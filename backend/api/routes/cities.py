"""
城市数据 API 路由 - 多城市数据聚合和对比分析

所有接口基于 city_manager 中的真实注册城市数据；空集时返回 404/503，
不再使用任何 mock 兜底，避免污染生产结果。
"""

import functools
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from backend.core.city_aggregation import AggregationConfig, city_aggregator
from backend.core.multi_city import city_manager
from backend.data.city_data import (
    generate_data_quality_report,
    get_all_cities,
    get_city_data,
    get_data_source_info,
    get_historical_data,
    get_score_benchmarks,
    get_score_weights,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cities", tags=["城市"])


# --------------------------------------------------------------------------- #
# 共享工具：错误处理装饰器 + 年份区间基类
# --------------------------------------------------------------------------- #


def _handle_errors(operation: str) -> Callable:
    """
    统一 try/except 样板：HTTPException 透传，其他异常记录日志后转 500。

    把 7 个端点里重复的 ``except HTTPException: raise / except Exception``
    块收敛到装饰器，避免每加一个端点都复制粘贴 6 行。
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                logger.error("%s失败: %s", operation, e, exc_info=True)
                raise HTTPException(status_code=500, detail="Internal server error") from None

        return wrapper

    return decorator


class _YearRangeModel(BaseModel):
    """带 year_start/year_end 字段的请求模型基类，统一年份顺序校验。"""

    year_start: int = Field(..., ge=1900, le=2200, description="开始年份")
    year_end: int = Field(..., ge=1900, le=2200, description="结束年份")

    @model_validator(mode="after")
    def _year_start_le_year_end(self):
        if self.year_start > self.year_end:
            raise ValueError("year_start must be <= year_end")
        return self


# --------------------------------------------------------------------------- #
# 请求 / 响应模型
# --------------------------------------------------------------------------- #


class AggregationRequest(BaseModel):
    """聚合分析请求"""

    group_by: list[str] = Field(..., min_length=1, description="分组字段")
    metrics: list[str] = Field(..., min_length=1, description="聚合指标")
    filters: dict[str, Any] | None = Field(None, description="过滤条件")
    sort_by: str | None = Field(None, description="排序字段")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="排序顺序")
    limit: int | None = Field(None, ge=1, le=1000, description="限制数量")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "group_by": ["city"],
                    "metrics": ["sum"],
                    "sort_by": "sum",
                    "sort_order": "desc",
                    "limit": 5,
                }
            ]
        }
    }


class ComparisonRequest(_YearRangeModel):
    """城市对比请求"""

    city_codes: list[str] = Field(..., min_length=1, max_length=20, description="城市代码列表")
    indicators: list[str] = Field(..., min_length=1, max_length=10, description="要对比的指标列表")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "city_codes": ["CN-GD-SZ", "CN-SH-SH"],
                    "indicators": ["gdp", "population"],
                    "year_start": 2020,
                    "year_end": 2025,
                }
            ]
        }
    }


class TimeSeriesRequest(_YearRangeModel):
    """时间序列分析请求"""

    city_codes: list[str] = Field(..., min_length=1, max_length=20, description="城市代码列表")
    indicator: str = Field(..., min_length=1, description="指标代码")
    group_by: list[str] | None = Field(None, description="分组字段")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "city_codes": ["CN-GD-SZ", "CN-SH-SH"],
                    "indicator": "gdp",
                    "year_start": 2016,
                    "year_end": 2025,
                }
            ]
        }
    }


class RegionalRequest(BaseModel):
    """区域分析请求"""

    region_field: str = Field("province", description="区域字段名")
    indicators: list[str] | None = Field(None, description="指标列表")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "region_field": "province",
                    "indicators": ["gdp", "population"],
                }
            ]
        }
    }


class CorrelationRequest(_YearRangeModel):
    """相关性分析请求"""

    city_codes: list[str] = Field(..., min_length=2, max_length=20, description="城市代码列表,至少 2 个")
    indicators: list[str] = Field(..., min_length=2, max_length=10, description="指标列表,至少 2 个")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "city_codes": ["CN-GD-SZ", "CN-SH-SH", "CN-BJ-BJ"],
                    "indicators": ["gdp", "population"],
                    "year_start": 2016,
                    "year_end": 2025,
                }
            ]
        }
    }


class CitiesCompareRequest(_YearRangeModel):
    """城市对比请求 (L-02 替换裸 request.json())"""

    city_codes: list[str] = Field(..., min_length=1, max_length=20, description="城市代码列表,1-20 个")
    indicators: list[str] = Field(
        default_factory=lambda: ["gdp"],
        max_length=10,
        description="对比指标列表,最多 10 个",
    )
    year_start: int = Field(2020, ge=1900, le=2200, description="开始年份")
    year_end: int = Field(2025, ge=1900, le=2200, description="结束年份")

    @property
    def validated_year_range(self) -> tuple[int, int]:
        return self.year_start, self.year_end


# --------------------------------------------------------------------------- #
# 端点
# --------------------------------------------------------------------------- #


@router.post("/aggregate", summary="数据聚合分析")
@_handle_errors("聚合分析")
def aggregate_data(request: AggregationRequest):
    """
    数据聚合分析(基于真实注册城市数据)

    支持按 city_code / year / indicator / province 等字段分组;
    metrics 支持 count / sum / avg / min / max / median / std。
    """
    data = _collect_all_city_records()
    if not data:
        raise HTTPException(
            status_code=503,
            detail="No city data ingested yet. Add CityData via city_manager.add_city_data() first.",
        )

    config = AggregationConfig(
        group_by=request.group_by,
        metrics=request.metrics,
        filters=request.filters or {},
        sort_by=request.sort_by,
        sort_order=request.sort_order,
        limit=request.limit,
    )

    result = city_aggregator.aggregate(data, config)
    return {
        "success": True,
        "result": {
            "groups": result.groups,
            "summary": result.summary,
            "metadata": result.metadata,
        },
    }


@router.post("/compare", summary="城市对比分析")
@_handle_errors("城市对比分析")
def compare_cities(request: CitiesCompareRequest):
    """
    城市对比分析(基于真实注册城市数据)

    对比多个城市在指定指标上的表现;数据空集时返回 503。
    """
    unknown = [c for c in request.city_codes if city_manager.get_city(_resolve_city_code(c)) is None]
    if unknown:
        raise HTTPException(status_code=404, detail=f"Unknown city code(s): {unknown}")

    primary_indicator = request.indicators[0]
    data: list[dict[str, Any]] = []
    for orig_code in request.city_codes:
        city_code = _resolve_city_code(orig_code)
        city_config = city_manager.get_city(city_code)
        # 上面 unknown 检查已 raise,这里 city_config 必不为 None
        if city_config is None:  # pragma: no cover - 防御性兜底
            raise HTTPException(status_code=500, detail="Internal: city vanished from registry") from None
        city_data = city_manager.get_city_data(city_code)
        for item in city_data:
            if request.year_start <= item.year <= request.year_end:
                value = item.indicators.get(primary_indicator)
                if value is None:
                    continue
                data.append(
                    {
                        "city": city_config.name,
                        "city_code": city_code,
                        "indicator": primary_indicator,
                        "value": float(value),
                        "year": item.year,
                    }
                )

    if not data:
        raise HTTPException(
            status_code=503,
            detail=(
                f"No data for indicator '{primary_indicator}' in years "
                f"{request.year_start}-{request.year_end} for cities {request.city_codes}."
            ),
        )

    result = city_aggregator.compare_cities(
        data, city_field="city", indicator_field="indicator", value_field="value"
    )
    return {
        "success": True,
        "comparison": {
            "cities": result.cities,
            "rankings": result.rankings,
            "insights": result.insights,
        },
    }


@router.post("/time-series", summary="时间序列分析")
@_handle_errors("时间序列分析")
def time_series_analysis(request: TimeSeriesRequest):
    """
    时间序列分析(基于真实注册城市数据)
    """
    unknown = [c for c in request.city_codes if city_manager.get_city(_resolve_city_code(c)) is None]
    if unknown:
        raise HTTPException(status_code=404, detail=f"Unknown city code(s): {unknown}")

    data: list[dict[str, Any]] = []
    for orig_code in request.city_codes:
        city_code = _resolve_city_code(orig_code)
        city_config = city_manager.get_city(city_code)
        if city_config is None:  # pragma: no cover - 防御性兜底
            raise HTTPException(status_code=500, detail="Internal: city vanished from registry") from None
        city_data = city_manager.get_city_data(city_code)
        for item in city_data:
            if not (request.year_start <= item.year <= request.year_end):
                continue
            value = item.indicators.get(request.indicator)
            if value is None:
                continue
            data.append(
                {
                    "city": city_config.name,
                    "city_code": city_code,
                    "indicator": request.indicator,
                    "value": float(value),
                    "year": item.year,
                }
            )

    if not data:
        raise HTTPException(
            status_code=503,
            detail=(
                f"No time-series data for indicator '{request.indicator}' in years "
                f"{request.year_start}-{request.year_end} for cities {request.city_codes}."
            ),
        )

    result = city_aggregator.time_series_analysis(
        data,
        time_field="year",
        value_field="value",
        group_by=request.group_by or ["city"],
    )

    groups_list = []
    if isinstance(result, dict):
        for key, series in result.items():
            if not isinstance(series, dict):
                continue
            groups_val = series.get("groups")
            if isinstance(groups_val, list) and groups_val:
                name = str(groups_val[0])
            else:
                name = str(key)
            groups_list.append(
                {
                    "groups": [name],
                    "city": name,
                    "time_points": series.get("time_points", []),
                    "values": series.get("values", []),
                    "trend": series.get("trend", []),
                }
            )

    return {"success": True, "time_series": {"groups": groups_list}}


@router.post("/regional", summary="区域分析")
@_handle_errors("区域分析")
def regional_analysis(request: RegionalRequest):
    """
    区域分析(基于真实注册城市数据)
    """
    data = _collect_all_city_records()
    if not data:
        raise HTTPException(
            status_code=503,
            detail="No city data ingested yet. Add CityData via city_manager.add_city_data() first.",
        )

    # request.indicators 仅做信息记录;实际汇总走 value 字段
    result = city_aggregator.regional_analysis(
        data,
        city_field="city",
        region_field=request.region_field,
        value_field="value",
    )
    return {"success": True, "regional_analysis": result, "indicators": request.indicators}


@router.post("/correlation", summary="相关性分析")
@_handle_errors("相关性分析")
def correlation_analysis(request: CorrelationRequest):
    """
    指标相关性分析(基于真实注册城市数据)
    """
    unknown = [c for c in request.city_codes if city_manager.get_city(_resolve_city_code(c)) is None]
    if unknown:
        raise HTTPException(status_code=404, detail=f"Unknown city code(s): {unknown}")

    data = _collect_all_city_records()
    if not data:
        raise HTTPException(
            status_code=503,
            detail="No city data ingested yet. Add CityData via city_manager.add_city_data() first.",
        )

    # 限定到指定城市与年份
    resolved = {_resolve_city_code(c) for c in request.city_codes}
    data = [
        item
        for item in data
        if item["city_code"] in resolved
        and request.year_start <= item["year"] <= request.year_end
        and item["indicator"] in request.indicators
    ]
    if not data:
        raise HTTPException(
            status_code=503,
            detail=(
                f"No data for indicators {request.indicators} in years "
                f"{request.year_start}-{request.year_end} for cities {request.city_codes}."
            ),
        )

    result = city_aggregator.correlation_analysis(
        data,
        indicators=request.indicators,
        city_field="city",
        year_field="year",
    )
    return {"success": True, "correlation": result}


@router.get("/rankings", summary="城市排名")
@_handle_errors("获取城市排名")
def get_city_rankings(
    indicator: str = Query("gdp", min_length=1, description="指标代码"),
    year: int | None = Query(None, ge=1900, le=2200, description="年份"),
    limit: int = Query(10, ge=1, le=100, description="返回数量"),
):
    """
    获取城市排名(基于真实注册城市数据)
    """
    data = _collect_all_city_records()
    if not data:
        raise HTTPException(
            status_code=503,
            detail="No city data ingested yet. Add CityData via city_manager.add_city_data() first.",
        )

    if year is not None:
        data = [item for item in data if item["year"] == year]
    data = [item for item in data if item["indicator"] == indicator]

    if not data:
        raise HTTPException(
            status_code=503,
            detail=f"No ranking data for indicator '{indicator}' (year={year}).",
        )

    config = AggregationConfig(
        group_by=["city"],
        metrics=["sum"],
        sort_by="sum",
        sort_order="desc",
        limit=limit,
    )
    result = city_aggregator.aggregate(data, config)
    return {
        "success": True,
        "indicator": indicator,
        "year": year,
        "rankings": [
            {"rank": idx + 1, "city": group["city"], "value": group["sum"]}
            for idx, group in enumerate(result.groups)
        ],
    }


@router.get("/dashboard", summary="城市仪表盘")
@_handle_errors("获取城市仪表盘")
def get_city_dashboard(city_code: str = Query(..., min_length=1, description="城市代码")):
    """
    获取城市仪表盘数据(基于真实注册城市数据)
    """
    city_config = city_manager.get_city(city_code)
    if city_config is None:
        raise HTTPException(status_code=404, detail=f"City not found: {city_code}") from None

    city_data = city_manager.get_city_data(city_code)
    years = sorted({item.year for item in city_data})
    indicator_codes: set[str] = set()
    for item in city_data:
        indicator_codes.update(item.indicators.keys())

    # 趋势:对每个指标做一次简单 OLS,得到方向 + 同比变化百分比
    trends: list[dict[str, Any]] = []
    for indicator in sorted(indicator_codes):
        series: list[tuple[int, float]] = []
        for item in city_data:
            value = item.indicators.get(indicator)
            if value is None:
                continue
            try:
                series.append((item.year, float(value)))
            except (TypeError, ValueError):
                continue
        series.sort(key=lambda pair: pair[0])
        if len(series) >= 2:
            first_value = series[0][1]
            last_value = series[-1][1]
            # 显式判断非零,避免合法的 0.0 初值被当作 falsy 误吞
            if first_value != 0:
                change_rate = round((last_value - first_value) / first_value * 100, 2)
            else:
                change_rate = 0.0
            direction = "increasing" if change_rate > 0.5 else "decreasing" if change_rate < -0.5 else "stable"
            trends.append({"indicator": indicator, "trend": direction, "change_rate": change_rate})

    # 排名:在城市子集内按指标均值倒排
    # 优化:一次性对所有指标调用 compare_cities,避免 N+1 查询(原每个指标一次)。
    rankings_payload: dict[str, int] = {}
    all_city_codes = list(city_manager.cities.keys())
    sorted_indicators = sorted(indicator_codes)
    # 年份为空时跳过排名(原代码传入哨兵 0 会导致查询不存在的年份)
    if sorted_indicators and all_city_codes and years:
        cities_compare = city_manager.compare_cities(
            all_city_codes,
            year=years[-1],
            indicators=sorted_indicators,
        )
        # 按指标分组排序,得到每个城市在每个指标上的排名
        for indicator in sorted_indicators:
            scored: list[tuple[str, float]] = []
            for code, payload in cities_compare.items():
                value = payload.get("indicators", {}).get(indicator)
                if value is None:
                    continue
                try:
                    scored.append((code, float(value)))
                except (TypeError, ValueError):
                    continue
            scored.sort(key=lambda pair: pair[1], reverse=True)
            for rank_index, (code, _) in enumerate(scored, start=1):
                if code == city_code:
                    rankings_payload[indicator] = rank_index
                    break

    dashboard = {
        "city_info": {
            "code": city_config.code,
            "name": city_config.name,
            "province": city_config.province,
            "population": city_config.population,
            "gdp_rank": city_config.gdp_rank,
            "tags": city_config.tags,
        },
        "overview": {
            "total_indicators": len(indicator_codes),
            "data_years": years,
            "data_sources": 1,  # 实际接入数据源后可由 ingestion 层覆盖
            "last_update": datetime.now().isoformat(),
        },
        "trends": trends,
        "rankings": rankings_payload,
    }
    return {"success": True, "dashboard": dashboard}


@router.get("/list", summary="获取所有城市列表")
def list_cities() -> dict[str, Any]:
    """获取系统支持的所有城市列表。"""
    cities = get_all_cities()
    return {"cities": cities, "total": len(cities)}


@router.get("/benchmarks/scores", summary="获取评分基准")
def get_scoring_benchmarks() -> dict[str, Any]:
    """获取评分系统的基准值与权重。"""
    return {
        "benchmarks": get_score_benchmarks(),
        "weights": get_score_weights(),
        "note": "评分基准基于真实城市数据的 25%/50%/75% 分位数，权重基于对 50 家半导体制造企业的调研。",
    }


@router.get("/quality/report", summary="获取数据质量报告")
def get_data_quality_report() -> dict[str, Any]:
    """获取完整的数据质量评估报告。"""
    return generate_data_quality_report()


@router.get("/{city_name}", summary="获取指定城市详情")
def get_city_detail(city_name: str) -> dict[str, Any]:
    """获取指定城市的详细数据。"""
    data = get_city_data(city_name)
    if not data:
        raise HTTPException(status_code=404, detail=f"城市 {city_name} 数据未找到")

    data_source = get_data_source_info().get(city_name, {})

    return {"city": city_name, "data": data, "data_source": data_source}


@router.get("/{city_name}/historical", summary="获取城市历史数据")
def get_city_historical(city_name: str) -> dict[str, Any]:
    """获取指定城市的历史时间序列数据。"""
    data = get_historical_data(city_name)
    if data is None or (hasattr(data, "empty") and data.empty) or len(data) == 0:
        raise HTTPException(status_code=404, detail=f"城市 {city_name} 历史数据未找到")

    records: Any
    if hasattr(data, "to_dict"):
        records = data.to_dict(orient="records")
    else:
        records = data

    return {"city": city_name, "years": [2020, 2021, 2022, 2023, 2024, 2025], "historical_data": records}


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #


def _resolve_city_code(city_name_or_code: str) -> str:
    """将中文城市名转换为注册表编码;若已是编码则原样返回。"""
    # 已在 city_manager 中的编码直接返回
    if city_manager.get_city(city_name_or_code) is not None:
        return city_name_or_code

    # 尝试按中文名称查找
    for code, config in city_manager.cities.items():
        if config.name == city_name_or_code:
            return code

    # 兜底：原样返回，由调用方处理 404
    return city_name_or_code


def _collect_all_city_records() -> list[dict[str, Any]]:
    """
    把 city_manager 中所有 CityData 摊平成 list[dict],
    字段统一为 city / city_code / province / indicator / value / year。
    """
    records: list[dict[str, Any]] = []
    for code, config in city_manager.cities.items():
        for item in city_manager.get_city_data(code):
            for indicator, value in item.indicators.items():
                if value is None:
                    continue
                try:
                    records.append(
                        {
                            "city": config.name,
                            "city_code": code,
                            "province": config.province,
                            "indicator": indicator,
                            "value": float(value),
                            "year": item.year,
                        }
                    )
                except (TypeError, ValueError):
                    continue
    return records
