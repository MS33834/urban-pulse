"""
城市经济发展健康水平指数（CEHI）API 路由

端点：
  GET  /api/v1/health/indicators - 完整指标体系
  POST /api/v1/health/calculate  - 单城市 CEHI 计算
  POST /api/v1/health/benchmark  - 城市对标分析
  GET  /api/v1/health/demo       - 示例城市 CEHI 结果
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Any, Literal, cast
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from backend.core.health_data_io import export_indicator_template, parse_indicator_data
from backend.core.health_index import CEHIConfig, CEHIEngine, CEHIResult, get_demo_values, health_index_demo
from backend.core.health_report import generate_cehi_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["健康指数"])


# --------------------------------------------------------------------------- #
# Pydantic 请求 / 响应模型
# --------------------------------------------------------------------------- #


class HealthLevelOut(BaseModel):
    """健康等级输出"""

    model_config = ConfigDict(populate_by_name=True)

    level: str
    name: str
    color: str
    emoji: str
    min_score: float
    description: str


class IndicatorOut(BaseModel):
    """指标定义输出"""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    dimension_id: str
    unit: str
    direction: Literal["positive", "negative"]
    description: str
    thresholds: dict[str, float]
    weight: float
    data_source: str


class DimensionOut(BaseModel):
    """维度定义输出"""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    weight: float
    description: str
    indicators: list[IndicatorOut]


class IndicatorScoreOut(BaseModel):
    """指标评分输出"""

    model_config = ConfigDict(populate_by_name=True)

    indicator: IndicatorOut
    raw_value: float | None
    score: float
    status: str
    status_name: str
    contribution: float


class DimensionScoreOut(BaseModel):
    """维度评分输出"""

    model_config = ConfigDict(populate_by_name=True)

    dimension: DimensionOut
    score: float
    status: str
    status_name: str
    indicator_scores: list[IndicatorScoreOut]
    weight: float


class CEHIResultOut(BaseModel):
    """CEHI 计算结果输出"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    city_name: str
    year: int
    total_score: float
    status: str
    status_name: str
    level: HealthLevelOut
    dimension_scores: list[DimensionScoreOut]
    top_strengths: list[IndicatorScoreOut]
    top_weaknesses: list[IndicatorScoreOut]
    recommendations: list[str]

    # 前端友好别名
    city: str | None = None
    score: float | None = None
    cehi_score: float | None = None
    dimensions: dict[str, float] | None = None
    weaknesses: list[dict[str, Any]] | None = None
    strengths: list[dict[str, Any]] | None = None
    suggestions: list[str] | None = None
    advice: list[str] | None = None


class IndicatorsResponse(BaseModel):
    """完整指标体系输出"""

    index_name: str
    index_short_name: str
    index_description: str
    schema_version: str
    dimensions: list[DimensionOut]
    indicators: list[IndicatorOut]
    health_levels: list[HealthLevelOut]


class CalculateRequest(BaseModel):
    """CEHI 计算请求"""

    city_name: str = Field(
        ...,
        min_length=1,
        description="城市名称",
        validation_alias=AliasChoices("city_name", "city"),
    )
    year: int = Field(..., ge=1900, le=2200, description="数据年份")
    indicator_values: dict[str, float] | None = Field(
        None, description="指标原始值 {indicator_id: value}，为空时使用演示数据"
    )

    model_config = ConfigDict(extra="allow")


class BenchmarkRequest(BaseModel):
    """城市对标请求"""

    target_city: str = Field(
        ...,
        min_length=1,
        description="目标城市名称",
        validation_alias=AliasChoices("target_city", "target", "city"),
    )
    year: int = Field(2024, ge=1900, le=2200, description="数据年份")
    target_values: dict[str, float] | None = Field(None, description="目标城市指标原始值，为空时使用演示数据")
    peers: dict[str, dict[str, float]] = Field(..., description="对标城市集 {city_name: {indicator_id: value}}")


class BenchmarkResponse(BaseModel):
    """城市对标结果输出"""

    target_city: str
    target_score: float
    target_status: str
    rankings: list[dict[str, Any]]
    similar_cities: list[dict[str, Any]]
    best_practice: dict[str, Any]


class ImportResponse(BaseModel):
    """指标数据导入结果输出"""

    indicator_values: dict[str, float]
    missing: list[str]
    invalid: list[dict[str, Any]]


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #


def _serialize(obj: Any) -> Any:
    """递归将 CEHI 数据类（或数据类列表/字典）转换为可 JSON 序列化的结构。"""
    if dataclasses.is_dataclass(obj):
        return _serialize(dataclasses.asdict(cast(Any, obj)))
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def _indicator_to_frontend(item: dict[str, Any]) -> dict[str, Any]:
    """将指标评分转换为前端友好的对象。"""
    indicator = item.get("indicator", {})
    return {
        "name": indicator.get("name", ""),
        "score": item.get("score", 0.0),
        "value": item.get("raw_value"),
        "dimension": indicator.get("dimension_id", ""),
        "unit": indicator.get("unit", ""),
    }


def _cehi_result_to_dict(result: CEHIResult) -> dict[str, Any]:
    """将 CEHI 计算结果转换为字典，并附带前端友好的别名字段。"""
    base = cast(dict[str, Any], _serialize(result))
    dimensions_map = {ds["dimension"]["name"]: ds["score"] for ds in base.get("dimension_scores", [])}
    base["city"] = base.get("city_name", "")
    base["score"] = base.get("total_score", 0.0)
    base["cehi_score"] = base.get("total_score", 0.0)
    base["dimensions"] = dimensions_map
    base["weaknesses"] = [_indicator_to_frontend(item) for item in base.get("top_weaknesses", [])]
    base["strengths"] = [_indicator_to_frontend(item) for item in base.get("top_strengths", [])]
    base["suggestions"] = base.get("recommendations", [])
    base["advice"] = base.get("recommendations", [])
    return base


# --------------------------------------------------------------------------- #
# 端点
# --------------------------------------------------------------------------- #


@router.get("/indicators", response_model=IndicatorsResponse, summary="获取 CEHI 指标体系")
async def get_indicators() -> IndicatorsResponse:
    """
    返回完整的 CEHI 指标体系，包括维度、指标、阈值、权重与健康等级。
    """
    try:
        config = CEHIConfig.default()
        return IndicatorsResponse(
            index_name=config.index_name,
            index_short_name=config.index_short_name,
            index_description=str(config._raw.get("index_description", "")),
            schema_version=str(config._raw.get("schema_version", "")),
            dimensions=_serialize(config.dimensions),
            indicators=_serialize(config.indicators),
            health_levels=_serialize(config.health_levels),
        )
    except Exception as e:
        logger.error("获取 CEHI 指标体系失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="获取指标体系失败") from None


@router.post("/calculate", response_model=CEHIResultOut, summary="计算 CEHI")
async def calculate_cehi(request: CalculateRequest) -> CEHIResultOut:
    """
    根据传入的城市指标原始值，计算该城市的 CEHI 综合得分、维度得分、健康等级与短板建议。
    """
    try:
        engine = CEHIEngine()
        values = request.indicator_values if request.indicator_values else get_demo_values()
        result = engine.calculate(
            city_name=request.city_name,
            year=request.year,
            indicator_values=values,
        )
        return CEHIResultOut.model_validate(_cehi_result_to_dict(result))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("CEHI 计算失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="CEHI 计算失败") from None


@router.post("/benchmark", response_model=BenchmarkResponse, summary="城市 CEHI 对标")
async def benchmark_cehi(request: BenchmarkRequest) -> BenchmarkResponse:
    """
    将目标城市与一组对标城市进行 CEHI 综合得分排名、相似城市与最佳实践差距分析。
    """
    try:
        engine = CEHIEngine()
        target_values = request.target_values if request.target_values else get_demo_values()
        result = engine.benchmark(
            target_city=request.target_city,
            target_values=target_values,
            peers=request.peers,
            year=request.year,
        )
        return BenchmarkResponse.model_validate(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("CEHI 对标分析失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="CEHI 对标分析失败") from None


@router.get("/demo", response_model=CEHIResultOut, summary="示例城市 CEHI 结果")
async def get_demo() -> CEHIResultOut:
    """
    返回使用内置示例数据计算的 CEHI 结果，便于快速体验接口返回结构。
    """
    try:
        result = health_index_demo()
        return CEHIResultOut.model_validate(_cehi_result_to_dict(result))
    except Exception as e:
        logger.error("生成 CEHI 示例结果失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="生成示例结果失败") from None


@router.get("/template", summary="下载 CEHI 指标录入模板")
async def download_template(
    format: Literal["xlsx", "csv"] = Query("xlsx", description="模板格式：xlsx 或 csv"),
) -> Response:
    """
    下载 CEHI 指标录入模板（Excel 或 CSV），包含全部指标定义与空 value 列。
    """
    try:
        content = export_indicator_template(format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except Exception as e:
        logger.error("生成 CEHI 指标模板失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="生成指标模板失败") from None

    media_types = {
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv; charset=utf-8",
    }
    extensions = {"xlsx": "xlsx", "csv": "csv"}
    filename = f"cehi_indicator_template.{extensions[format]}"

    return Response(
        content=content,
        media_type=media_types[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=ImportResponse, summary="导入 CEHI 指标数据")
async def import_indicators(
    file: UploadFile = File(..., description="要上传的 Excel 或 CSV 文件"),
) -> ImportResponse:
    """
    上传 CEHI 指标数据文件，解析后返回有效指标值、缺失指标与无效值信息。
    """
    filename = file.filename or ""
    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="上传文件为空")
        if len(file_bytes) > 50 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="文件过大，最大支持 50 MB")

        indicator_values = parse_indicator_data(file_bytes, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except HTTPException:
        raise
    except Exception as e:
        logger.error("解析 CEHI 指标数据失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="解析指标数据失败") from None

    config = CEHIConfig.default()
    configured_ids = {indicator.id for indicator in config.indicators}
    missing = sorted(configured_ids - set(indicator_values.keys()))

    return ImportResponse(indicator_values=indicator_values, missing=missing, invalid=[])


def _pdf_filename(city_name: str, year: int) -> str:
    """生成符合 RFC 5987 的 Content-Disposition 文件名。"""
    base = f"{city_name}_{year}_CEHI报告"
    ascii_name = "".join(c if c.isascii() else "_" for c in base)
    if not ascii_name.endswith(".pdf"):
        ascii_name += ".pdf"
    utf8_name = quote(f"{base}.pdf", safe="")
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'{utf8_name}'


@router.post("/report/pdf", summary="导出 CEHI PDF 诊断报告")
async def export_cehi_pdf(request: CalculateRequest) -> Response:
    """
    接收与 /calculate 相同的请求体，生成并返回 CEHI PDF 诊断报告。
    """
    try:
        engine = CEHIEngine()
        values = request.indicator_values if request.indicator_values else get_demo_values()
        result = engine.calculate(
            city_name=request.city_name,
            year=request.year,
            indicator_values=values,
        )
        pdf_bytes = generate_cehi_pdf(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("生成 CEHI PDF 报告失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="生成 PDF 报告失败") from None

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": _pdf_filename(request.city_name, request.year)},
    )
