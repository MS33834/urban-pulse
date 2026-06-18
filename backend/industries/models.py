"""
产业数据模型

产业（Industry）是附着在区域（Region）上的经济实体，
用于预测产业未来规模、增速与风险。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class IndustryLevel(StrEnum):
    """产业层级"""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"


@dataclass
class FactorImpact:
    """
    影响产业未来发展的因素

    score: -1.0 ~ 1.0，负向抑制、正向促进
    weight: 0.0 ~ 1.0，该因素在综合调整中的权重
    """

    name: str
    score: float  # -1 ~ 1
    weight: float  # 0 ~ 1
    source: str | None = None  # 数据来源或依据
    note: str | None = None

    def __post_init__(self):
        self.score = max(-1.0, min(1.0, float(self.score)))
        self.weight = max(0.0, min(1.0, float(self.weight)))


@dataclass
class Industry:
    """
    产业实体

    - code: 产业编码，如 "C39" 或 "semiconductor"
    - name: 产业名称
    - region_code: 所属区域编码
    - level: 产业层级（一/二/三产）
    - historical_data: 年度历史指标（产值、就业、研发投入等）
    - factors: 影响未来发展的多因素列表
    """

    code: str
    name: str
    region_code: str
    level: IndustryLevel = IndustryLevel.SECONDARY
    category: str = ""
    key_indicators: dict[str, Any] = field(default_factory=dict)
    historical_data: list[dict[str, Any]] = field(default_factory=list)
    factors: list[FactorImpact] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_time_series(self) -> bool:
        """是否有可用于预测的历史时序数据"""
        return len(self.historical_data) >= 3

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
            return None
        return max(row.get("year", 0) for row in self.historical_data)

    def to_dict(self) -> dict[str, Any]:
        """完整导出"""
        return {
            "code": self.code,
            "name": self.name,
            "region_code": self.region_code,
            "level": self.level.value,
            "category": self.category,
            "key_indicators": self.key_indicators,
            "historical_data": self.historical_data,
            "factors": [
                {"name": f.name, "score": f.score, "weight": f.weight, "source": f.source, "note": f.note}
                for f in self.factors
            ],
            "metadata": self.metadata,
        }
