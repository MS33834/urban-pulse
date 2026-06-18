"""区域数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RegionLevel(StrEnum):
    """区域层级"""

    COUNTRY = "country"
    PROVINCE = "province"
    CITY = "city"
    DISTRICT = "district"


@dataclass
class Region:
    """
    区域实体

    支持国家、省、市、区县四个层级，可挂载任意指标与历史时序数据。
    """

    code: str  # 区域唯一编码，如 'CN-GD-SZ' 或 '440300'
    name: str  # 区域名称
    level: RegionLevel  # 区域层级
    parent_code: str | None = None  # 父区域编码
    region: str | None = None  # 地理大区，如华东、华南
    country: str = "中国"
    indicators: dict[str, Any] = field(default_factory=dict)  # 最新指标快照
    historical_data: list[dict[str, Any]] = field(default_factory=list)  # 年度时序数据
    metadata: dict[str, Any] = field(default_factory=dict)  # 来源、质量、更新时间等

    @property
    def province_code(self) -> str | None:
        """所属省份编码（仅对 city/district 有效）"""
        if self.level == RegionLevel.PROVINCE:
            return self.code
        if self.parent_code is None:
            return None
        if self.level == RegionLevel.CITY:
            return self.parent_code
        # district: 父级是 city，需要再向上找 province
        return self.metadata.get("province_code")

    @property
    def has_time_series(self) -> bool:
        """是否有可用于预测的历史时序数据"""
        return len(self.historical_data) >= 3

    def get_indicator(self, key: str, default: Any = None) -> Any:
        """获取单个指标"""
        return self.indicators.get(key, default)

    def get_time_series(self, indicator: str) -> list[float]:
        """获取某个指标的历史序列（按年份排序）"""
        return [
            float(row[indicator])
            for row in sorted(self.historical_data, key=lambda r: r.get("year", 0))
            if indicator in row and row[indicator] is not None
        ]

    @property
    def latest_year(self) -> int | None:
        """最新数据年份"""
        if not self.historical_data:
            return self.indicators.get("year")
        return max(row.get("year", 0) for row in self.historical_data)

    def to_summary(self) -> dict[str, Any]:
        """导出摘要信息，用于 API 列表"""
        return {
            "code": self.code,
            "name": self.name,
            "level": self.level.value,
            "parent_code": self.parent_code,
            "region": self.region,
            "country": self.country,
            "latest_year": self.latest_year,
            "has_time_series": self.has_time_series,
            "data_quality": self.metadata.get("data_quality"),
            "data_source": self.metadata.get("data_source"),
        }

    def to_dict(self) -> dict[str, Any]:
        """完整导出"""
        return {
            "code": self.code,
            "name": self.name,
            "level": self.level.value,
            "parent_code": self.parent_code,
            "region": self.region,
            "country": self.country,
            "indicators": self.indicators,
            "historical_data": self.historical_data,
            "metadata": self.metadata,
        }
