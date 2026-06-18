"""
调查数据与区域注册表集成

把社会实践、民意调查、田野调查等数据按标准格式挂接到 Region 对象，
使其可以像 GDP、人口等硬指标一样被查询、汇总和预测。
"""

from __future__ import annotations

import logging
from typing import Any

from backend.regions.models import Region
from backend.regions.registry import RegionRegistry

logger = logging.getLogger(__name__)


def attach_survey_records(
    registry: RegionRegistry,
    records: list[dict[str, Any]],
    overwrite: bool = False,
) -> dict[str, int]:
    """
    将调查记录合并到区域注册表

    对于每个 (region_code, year)，会把 survey 指标写入对应 Region 的
    historical_data 中；如果该年份记录不存在，则新建一条。

    Args:
        registry: 区域注册表
        records: SurveyCollector 输出的标准记录列表
        overwrite: 是否覆盖已有的同名调查指标

    Returns:
        {"attached": 成功挂载记录数, "skipped": 跳过记录数, "unknown_regions": 未识别区域数}
    """
    stats = {"attached": 0, "skipped": 0, "unknown_regions": 0}

    for record in records:
        region_code = str(record.get("region_code", ""))
        region = registry.get(region_code)
        if region is None:
            stats["unknown_regions"] += 1
            continue

        year = int(record["year"])
        indicator = str(record["indicator"])
        value = float(record["value"])

        if _merge_into_region(region, year, indicator, value, record, overwrite):
            stats["attached"] += 1
        else:
            stats["skipped"] += 1

    return stats


def _merge_into_region(
    region: Region,
    year: int,
    indicator: str,
    value: float,
    record: dict[str, Any],
    overwrite: bool,
) -> bool:
    """把单个调查指标写入 Region 的 historical_data"""
    # 查找是否已有该年份记录
    year_row: dict[str, Any] | None = None
    for row in region.historical_data:
        if int(row.get("year", 0)) == year:
            year_row = row
            break

    if year_row is None:
        year_row = {"year": year}
        region.historical_data.append(year_row)

    if indicator in year_row and not overwrite:
        return False

    year_row[indicator] = value

    # 保留调查元信息到 metadata，便于追溯来源
    survey_meta = {
        "source": record.get("source"),
        "survey_type": record.get("survey_type"),
        "unit": record.get("unit"),
        "notes": record.get("notes"),
    }
    region.metadata.setdefault("survey_sources", {}).setdefault(indicator, []).append(
        {k: v for k, v in survey_meta.items() if v is not None}
    )

    return True


def get_survey_indicators(region: Region) -> list[str]:
    """返回区域 historical_data 中出现的所有调查类指标名"""
    indicators: set[str] = set()
    for row in region.historical_data:
        for key in row:
            if key == "year":
                continue
            if key not in ("gdp", "population", "fiscal_revenue", "rd_intensity", "hitech_output"):
                indicators.add(key)
    return sorted(indicators)
