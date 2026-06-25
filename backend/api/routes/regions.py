"""
区域 API 路由 — 多层级、可扩展的区域发现与数据访问

支持国家 / 省 / 市 / 区县四级，未来接入社会实践、调查数据时可直接挂载到
区域实体上。
"""

from __future__ import annotations

import io
import logging
from typing import Any

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field

from backend.core.province_aggregator import SUPPORTED_INDICATORS, forecast_city_indicator
from backend.data_collection.survey_collector import SurveyCollector
from backend.regions import RegionLevel, get_registry
from backend.regions.survey_integration import attach_survey_records, get_survey_indicators
from config.regions import get_region_config, list_all_regions

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/regions", tags=["区域"])

# 延迟导入 limiter 以避免与 backend.api.main 的循环依赖
from backend.api.main import limiter  # noqa: E402

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


class RegionForecastRequest(BaseModel):
    """区域预测请求"""

    indicator: str = Field("gdp", description=f"预测指标,支持: {', '.join(SUPPORTED_INDICATORS)}")
    forecast_years: int = Field(5, ge=1, le=20, description="预测年数")


class BatchForecastRequest(BaseModel):
    """批量区域预测请求"""

    codes: list[str] = Field(..., min_length=1, max_length=50, description="区域编码列表")
    indicator: str = Field("gdp", description=f"预测指标,支持: {', '.join(SUPPORTED_INDICATORS)}")
    forecast_years: int = Field(5, ge=1, le=20, description="预测年数")


# --------------------------------------------------------------------------- #
# 发现与查询
# --------------------------------------------------------------------------- #


@router.get("/summary", summary="区域覆盖总览")
async def region_summary() -> dict[str, Any]:
    """返回当前注册的区域总数、层级分布、可预测区域数、地理大区列表。"""
    registry = get_registry()
    return {
        "success": True,
        "summary": registry.region_summary(),
    }


@router.get("", summary="列出所有区域")
async def list_regions(
    level: RegionLevel | None = Query(None, description="按层级过滤: country/province/city/district"),
    region: str | None = Query(None, description="按地理大区过滤,如华东、华南"),
    parent_code: str | None = Query(None, description="按父区域编码过滤"),
    forecastable: bool = Query(False, description="仅返回可用于预测的区域"),
    limit: int = Query(1000, ge=1, le=5000, description="返回数量上限"),
) -> dict[str, Any]:
    """列出区域，支持层级、大区、父区域、可预测性过滤。"""
    registry = get_registry()

    if forecastable:
        regions = registry.list_forecastable("gdp")
    elif region:
        regions = registry.list_by_region(region)
    elif parent_code:
        regions = registry.list_by_parent(parent_code)
    elif level:
        regions = registry.list_all(level)
    else:
        regions = registry.list_all()

    return {
        "success": True,
        "count": len(regions),
        "regions": [r.to_summary() for r in regions[:limit]],
    }


@router.get("/{code}", summary="获取区域详情")
async def get_region(code: str) -> dict[str, Any]:
    """按区域编码获取完整信息，包括指标快照、历史时序、元数据。"""
    registry = get_registry()
    region = registry.get(code)
    if region is None:
        raise HTTPException(status_code=404, detail=f"区域不存在: {code}")
    return {"success": True, "region": region.to_dict()}


@router.get("/{code}/time-series/{indicator}", summary="获取区域某指标时序")
async def get_region_time_series(
    code: str,
    indicator: str,
    start_year: int | None = Query(None, description="起始年份"),
    end_year: int | None = Query(None, description="结束年份"),
) -> dict[str, Any]:
    """获取指定区域某指标的历史时间序列。"""
    registry = get_registry()
    region = registry.get(code)
    if region is None:
        raise HTTPException(status_code=404, detail=f"区域不存在: {code}")

    data = []
    for row in sorted(region.historical_data, key=lambda r: r.get("year", 0)):
        year = row.get("year")
        if year is None or indicator not in row:
            continue
        if start_year is not None and year < start_year:
            continue
        if end_year is not None and year > end_year:
            continue
        try:
            data.append({"year": year, "value": float(row[indicator])})
        except (TypeError, ValueError):
            continue

    return {
        "success": True,
        "code": code,
        "name": region.name,
        "indicator": indicator,
        "count": len(data),
        "data": data,
    }


# --------------------------------------------------------------------------- #
# 预测
# --------------------------------------------------------------------------- #


@router.get("/{code}/forecast/{indicator}", summary="预测区域指标")
async def forecast_region_indicator(
    code: str,
    indicator: str,
    forecast_years: int = Query(5, ge=1, le=20, description="预测年数"),
) -> dict[str, Any]:
    """对指定区域（目前仅 city 层级实现）的某指标做未来 N 年预测。"""
    registry = get_registry()
    region = registry.get(code)
    if region is None:
        raise HTTPException(status_code=404, detail=f"区域不存在: {code}")

    if region.level != RegionLevel.CITY:
        # 省级预测复用 province_aggregator
        from backend.core.province_aggregator import forecast_province_indicator

        result = forecast_province_indicator(region.name, indicator, forecast_years)
        if "error" in result:
            status = 404 if "not in registry" in result["error"] else 503
            raise HTTPException(status_code=status, detail=result["error"])
        return {"success": True, "region_code": code, **result}

    # 城市级预测复用现有函数（按名称匹配）
    result = forecast_city_indicator(region.name, indicator, forecast_years)
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return {"success": True, "region_code": code, **result}


@router.post("/batch/forecast", summary="批量区域预测")
@limiter.limit("10/minute")
async def batch_forecast_regions(request: Request, body: BatchForecastRequest) -> dict[str, Any]:
    """对多个城市/省份批量预测同一指标，并给出排名。"""
    registry = get_registry()
    results: dict[str, Any] = {}
    errors: dict[str, str] = {}
    comparison: list[dict[str, Any]] = []

    for code in body.codes:
        region = registry.get(code)
        if region is None:
            errors[code] = "区域不存在"
            continue

        if region.level == RegionLevel.CITY:
            result = forecast_city_indicator(region.name, body.indicator, body.forecast_years)
        else:
            from backend.core.province_aggregator import forecast_province_indicator

            result = forecast_province_indicator(region.name, body.indicator, body.forecast_years)

        if "error" in result:
            errors[code] = result["error"]
            continue

        results[code] = result
        if result.get("forecast_values"):
            comparison.append(
                {
                    "code": code,
                    "name": region.name,
                    "level": region.level.value,
                    "latest_value": result["historical_values"][-1] if result.get("historical_values") else None,
                    "forecast_value": result["forecast_values"][-1],
                    "forecast_cagr_pct": result["growth"]["forecast_cagr_pct"],
                }
            )

    comparison.sort(key=lambda r: r["forecast_value"] or 0, reverse=True)
    return {
        "success": True,
        "indicator": body.indicator,
        "forecast_years": body.forecast_years,
        "results": results,
        "errors": errors,
        "comparison": comparison,
    }


# --------------------------------------------------------------------------- #
# 社会实践 / 调查数据（开放社区贡献入口）
# --------------------------------------------------------------------------- #


@router.post("/survey/upload", summary="上传调查数据")
@limiter.limit("10/minute")
async def upload_survey_data(
    request: Request,
    file: UploadFile = File(..., description="CSV/Excel 调查数据文件"),
    overwrite: bool = Query(False, description="是否覆盖已有同名调查指标"),
) -> dict[str, Any]:
    """
    上传社会实践或调查数据文件，按标准格式（region_code, year, indicator, value）
    挂接到已有区域。这是开放数据社区的核心贡献入口之一。
    """
    registry = get_registry()
    collector = SurveyCollector(source_name=file.filename or "community-upload")

    try:
        content = await file.read()
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="文件过大，最大支持 50 MB")
        if file.filename and file.filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), dtype={"region_code": str})
        elif file.filename and file.filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content), dtype={"region_code": str})
        else:
            raise HTTPException(status_code=400, detail="仅支持 CSV 或 Excel 文件")

        records = collector.load_dataframe(df)
        stats = attach_survey_records(registry, records, overwrite=overwrite)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception:
        logger.exception("调查数据上传失败")
        raise HTTPException(status_code=500, detail="调查数据处理失败，请检查文件格式") from None

    return {
        "success": True,
        "filename": file.filename,
        "indicators": collector.list_indicators(),
        "stats": stats,
    }


@router.get("/{code}/survey", summary="获取区域调查指标")
async def get_region_survey_indicators(
    code: str,
    indicator: str | None = Query(None, description="指定调查指标名"),
) -> dict[str, Any]:
    """返回某区域已挂载的社会实践/调查指标列表或单个指标时序。"""
    registry = get_registry()
    region = registry.get(code)
    if region is None:
        raise HTTPException(status_code=404, detail=f"区域不存在: {code}")

    if indicator:
        data = []
        for row in sorted(region.historical_data, key=lambda r: r.get("year", 0)):
            if indicator in row:
                # 单行脏数据不应中断整个返回,跳过非法值
                try:
                    data.append({"year": row["year"], "value": float(row[indicator])})
                except (TypeError, ValueError):
                    logger.warning("区域 %s 指标 %s 跳过非法值: %r", code, indicator, row[indicator])
                    continue
        return {
            "success": True,
            "code": code,
            "name": region.name,
            "indicator": indicator,
            "data": data,
        }

    return {
        "success": True,
        "code": code,
        "name": region.name,
        "survey_indicators": get_survey_indicators(region),
    }


# --------------------------------------------------------------------------- #
# 区域配置详情（行政区划、指标权重、经济特征等）
# --------------------------------------------------------------------------- #


@router.get("/config/list", summary="列出所有已配置区域")
async def list_region_configs() -> dict[str, Any]:
    """返回所有有详细配置的城市名称列表。"""
    return {
        "success": True,
        "count": len(list_all_regions()),
        "regions": list_all_regions(),
    }


@router.get("/config/{name}", summary="获取区域配置详情")
async def get_region_config_detail(name: str) -> dict[str, Any]:
    """
    获取指定区域的详细配置，包括：
    - 行政区划（区县、开发区）
    - 指标权重
    - 经济特征标签
    - 基准数据
    - 数据来源
    """
    config_cls = get_region_config(name)
    if config_cls is None:
        raise HTTPException(status_code=404, detail=f"区域配置不存在: {name}")

    config = config_cls()
    return {
        "success": True,
        "name": config.name,
        "code": config.code,
        "province": config.province,
        "country": config.country,
        "statistical_caliber": config.statistical_caliber,
        "administrative_divisions": config.administrative_divisions,
        "indicator_weights": config.indicator_weights,
        "economic_characteristics": config.economic_characteristics,
        "benchmark_data": config.benchmark_data,
        "data_sources": config.data_sources,
    }


@router.get("/config/{name}/districts", summary="获取区域行政区划")
async def get_region_districts(name: str) -> dict[str, Any]:
    """获取指定区域的区县和开发区列表。"""
    config_cls = get_region_config(name)
    if config_cls is None:
        raise HTTPException(status_code=404, detail=f"区域配置不存在: {name}")

    config = config_cls()
    return {
        "success": True,
        "name": config.name,
        "districts": config.administrative_divisions.get("districts", []),
        "development_zones": config.administrative_divisions.get("development_zones", []),
    }


@router.get("/config/{name}/benchmarks", summary="获取区域基准数据")
async def get_region_benchmarks(name: str) -> dict[str, Any]:
    """获取指定区域的基准数据（人均GDP、平均工资、工业效率等）。"""
    config_cls = get_region_config(name)
    if config_cls is None:
        raise HTTPException(status_code=404, detail=f"区域配置不存在: {name}")

    config = config_cls()
    return {
        "success": True,
        "name": config.name,
        "benchmark_data": config.benchmark_data,
    }
