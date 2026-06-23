"""
城市数据模块 - 兼容层

底层数据已迁移到 backend/regions/ 注册表（支持国家/省/市/区县四级），
本模块保留原有函数签名，作为向后兼容的 facade。
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import pandas as pd

from backend.regions import RegionLevel, get_registry

logger = logging.getLogger(__name__)


def _refresh_cache() -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """从区域注册表同步城市级数据到兼容字典"""
    registry = get_registry()
    city_data: dict[str, dict[str, Any]] = {}
    historical_data: dict[str, list[dict[str, Any]]] = {}

    for city in registry.list_all(RegionLevel.CITY):
        snapshot = dict(city.indicators)
        snapshot.update(
            {
                "name": city.name,
                "region": city.region,
                "code": city.code,
                "parent_code": city.parent_code,
                "data_source": city.metadata.get("data_source", ""),
                "data_quality": city.metadata.get("data_quality", 80.0),
            }
        )
        city_data[city.name] = snapshot
        if city.historical_data:
            historical_data[city.name] = list(city.historical_data)

    return city_data, historical_data


# 启动时同步一次；后续新增城市可调用 refresh()
CITY_DATA, HISTORICAL_DATA = _refresh_cache()


def refresh() -> None:
    """刷新缓存（当动态加载新城市后调用）"""
    global CITY_DATA, HISTORICAL_DATA
    CITY_DATA, HISTORICAL_DATA = _refresh_cache()
    get_score_benchmarks.cache_clear()
    get_score_weights.cache_clear()
    logger.info(f"城市数据缓存已刷新: {len(CITY_DATA)} 个城市")


def get_city_data(city_name: str) -> dict[str, Any] | None:
    """获取单个城市的完整数据"""
    return CITY_DATA.get(city_name)


def get_all_cities() -> list[str]:
    """获取所有有完整指标数据的城市"""
    return list(CITY_DATA.keys())


def get_all_forecast_cities() -> list[str]:
    """获取所有有历史时序数据的城市"""
    registry = get_registry()
    return [r.name for r in registry.list_forecastable("gdp")]


def get_historical_data(city_name: str) -> pd.DataFrame:
    """获取城市历史数据（DataFrame 形式）"""
    rows = HISTORICAL_DATA.get(city_name, [])
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def compare_cities(city_names: list[str] | None = None) -> pd.DataFrame:
    """对比多个城市的数据（DataFrame 形式）"""
    if city_names is None:
        city_names = list(CITY_DATA.keys())
    rows = []
    for c in city_names:
        if c in CITY_DATA:
            row = {"name": c, **CITY_DATA[c]}
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


@lru_cache(maxsize=1)
def get_score_benchmarks() -> dict[str, dict[str, float]]:
    """获取评分基准（基于当前城市数据分位数）"""

    def _values(key: str) -> list[float]:
        return [d[key] for d in CITY_DATA.values() if key in d and isinstance(d[key], (int, float))]

    def _q(arr: list[float], pct: float) -> float:
        if not arr:
            return 0.0
        s = sorted(arr)
        idx = int(len(s) * pct)
        return float(s[min(idx, len(s) - 1)])

    keys = [
        "land_price",
        "salary_level",
        "energy_cost",
        "financing_cost",
        "local_support_rate",
        "tax_reduction",
        "supplier_count",
        "rd_intensity",
        "rd_subsidy",
        "policy_coverage",
        "avg_approval_time",
    ]
    result: dict[str, dict[str, float]] = {}
    for key in keys:
        vals = _values(key)
        result[key] = {"low": _q(vals, 0.25), "medium": _q(vals, 0.5), "high": _q(vals, 0.75)}
    return result


@lru_cache(maxsize=1)
def get_score_weights() -> dict[str, float]:
    """获取评分权重（基于专家调研，已归一化到 1.0）"""
    _raw = {
        "business_cost": 0.38,
        "supply_chain": 0.32,
        "policy_benefit": 0.30,
        "land_price": 0.12,
        "salary_level": 0.10,
        "energy_cost": 0.08,
        "financing_cost": 0.08,
        "local_support_rate": 0.12,
        "supplier_count": 0.10,
        "avg_delivery_time": 0.05,
        "location_quotient": 0.05,
        "tax_reduction": 0.10,
        "policy_coverage": 0.07,
        "tax_coverage": 0.07,
        "rd_subsidy": 0.08,
        "avg_approval_time": 0.05,
    }
    total = sum(_raw.values())
    return {k: v / total for k, v in _raw.items()}


def get_data_source_info() -> dict[str, dict[str, Any]]:
    """获取数据来源信息"""
    return {
        city: {
            "source": data.get("data_source", ""),
            "data_quality_score": data.get("data_quality", 80.0),
            "year": data.get("year"),
            "region": data.get("region"),
        }
        for city, data in CITY_DATA.items()
    }


def generate_data_quality_report() -> dict[str, Any]:
    """生成数据质量报告"""
    qualities = [d.get("data_quality", 80.0) for d in CITY_DATA.values()]
    return {
        "total_cities": len(CITY_DATA),
        "avg_quality": sum(qualities) / len(qualities) if qualities else 0,
        "min_quality": min(qualities) if qualities else 0,
        "max_quality": max(qualities) if qualities else 0,
        "data_sources": {city: data.get("data_source", "") for city, data in CITY_DATA.items()},
        "quality_by_city": {city: data.get("data_quality", 80.0) for city, data in CITY_DATA.items()},
        "report_date": "2025年Q2",
    }
