"""城市经济发展健康水平指数（CEHI）计算引擎。

CEHI = City Economic Health Index

该模块提供：
1. 从 YAML 加载指标体系与权重配置
2. 单指标评分（基于阈值区间的线性插值）
3. 维度得分与 CEHI 综合得分计算
4. 健康等级判定
5. 短板归因分析
6. 城市对标与标杆推荐
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import yaml


@dataclass(frozen=True)
class Indicator:
    """单个指标定义。"""

    id: str
    name: str
    dimension_id: str
    unit: str
    direction: Literal["positive", "negative"]
    description: str
    thresholds: dict[str, float]
    weight: float
    data_source: str

    @property
    def healthy_threshold(self) -> float:
        return self.thresholds["healthy"]

    @property
    def subhealthy_threshold(self) -> float:
        return self.thresholds["subhealthy"]

    @property
    def warning_threshold(self) -> float:
        return self.thresholds["warning"]


@dataclass(frozen=True)
class Dimension:
    """维度定义。"""

    id: str
    name: str
    weight: float
    description: str
    indicators: list[Indicator]


@dataclass(frozen=True)
class HealthLevel:
    """健康等级定义。"""

    level: str
    name: str
    color: str
    emoji: str
    min_score: float
    description: str


@dataclass(frozen=True)
class IndicatorScore:
    """单个指标评分结果。"""

    indicator: Indicator
    raw_value: float | None
    score: float
    status: str
    status_name: str
    contribution: float


@dataclass(frozen=True)
class DimensionScore:
    """单个维度评分结果。"""

    dimension: Dimension
    score: float
    status: str
    status_name: str
    indicator_scores: list[IndicatorScore]
    weight: float


@dataclass(frozen=True)
class CEHIResult:
    """CEHI 完整诊断结果。"""

    city_name: str
    year: int
    total_score: float
    status: str
    status_name: str
    level: HealthLevel
    dimension_scores: list[DimensionScore]
    top_strengths: list[IndicatorScore]
    top_weaknesses: list[IndicatorScore]
    recommendations: list[str]


class CEHIConfig:
    """CEHI 指标体系配置管理。"""

    _instance: CEHIConfig | None = None

    def __init__(self, config_path: Path | str | None = None) -> None:
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "cehi_indicators.yaml"
        self.config_path = Path(config_path)
        self._raw: dict[str, Any] = self._load()
        self._dimensions: dict[str, Dimension] = {}
        self._indicators: dict[str, Indicator] = {}
        self._levels: list[HealthLevel] = []
        self._build()

    @classmethod
    def default(cls) -> CEHIConfig:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self) -> dict[str, Any]:
        with self.config_path.open("r", encoding="utf-8") as f:
            return cast(dict[str, Any], yaml.safe_load(f))

    def _build(self) -> None:
        dims_raw = {d["id"]: d for d in self._raw["dimensions"]}
        indicators_by_dim: dict[str, list[Indicator]] = {d: [] for d in dims_raw}

        for ind in self._raw["indicators"]:
            indicator = Indicator(
                id=ind["id"],
                name=ind["name"],
                dimension_id=ind["dimension"],
                unit=ind["unit"],
                direction=ind["direction"],
                description=ind["description"],
                thresholds={
                    "healthy": float(ind["thresholds"]["healthy"]),
                    "subhealthy": float(ind["thresholds"]["subhealthy"]),
                    "warning": float(ind["thresholds"]["warning"]),
                },
                weight=float(ind["weight"]),
                data_source=ind["data_source"],
            )
            self._indicators[indicator.id] = indicator
            indicators_by_dim[indicator.dimension_id].append(indicator)

        for dim_id, dim_raw in dims_raw.items():
            dim_indicators = indicators_by_dim[dim_id]
            # 维度内权重归一化
            total_weight = sum(i.weight for i in dim_indicators)
            normalized = [
                Indicator(
                    id=i.id,
                    name=i.name,
                    dimension_id=i.dimension_id,
                    unit=i.unit,
                    direction=i.direction,
                    description=i.description,
                    thresholds=i.thresholds,
                    weight=i.weight / total_weight if total_weight > 0 else 0.0,
                    data_source=i.data_source,
                )
                for i in dim_indicators
            ]
            self._dimensions[dim_id] = Dimension(
                id=dim_id,
                name=dim_raw["name"],
                weight=float(dim_raw["weight"]),
                description=dim_raw["description"],
                indicators=normalized,
            )

        for lvl in self._raw["health_levels"]:
            self._levels.append(
                HealthLevel(
                    level=lvl["level"],
                    name=lvl["name"],
                    color=lvl["color"],
                    emoji=lvl["emoji"],
                    min_score=float(lvl["min_score"]),
                    description=lvl["description"],
                )
            )
        # 按 min_score 降序，方便判定
        self._levels.sort(key=lambda x: x.min_score, reverse=True)

    @property
    def index_name(self) -> str:
        return str(self._raw.get("index_name", "城市经济发展健康水平指数"))

    @property
    def index_short_name(self) -> str:
        return str(self._raw.get("index_short_name", "CEHI"))

    @property
    def dimensions(self) -> list[Dimension]:
        return list(self._dimensions.values())

    @property
    def indicators(self) -> list[Indicator]:
        return list(self._indicators.values())

    @property
    def health_levels(self) -> list[HealthLevel]:
        return self._levels

    def get_dimension(self, dim_id: str) -> Dimension | None:
        return self._dimensions.get(dim_id)

    def get_indicator(self, ind_id: str) -> Indicator | None:
        return self._indicators.get(ind_id)


class CEHIEngine:
    """CEHI 计算引擎。"""

    def __init__(self, config: CEHIConfig | None = None) -> None:
        self.config = config or CEHIConfig.default()

    def _indicator_score(self, indicator: Indicator, value: float | None) -> IndicatorScore:
        """计算单个指标得分。"""
        if value is None or math.isnan(value):
            return IndicatorScore(
                indicator=indicator,
                raw_value=None,
                score=0.0,
                status="missing",
                status_name="数据缺失",
                contribution=0.0,
            )

        h = indicator.healthy_threshold
        s = indicator.subhealthy_threshold
        w = indicator.warning_threshold

        if indicator.direction == "positive":
            if value >= h:
                base_score = self._linear_map(value, h, h * 1.5, 80.0, 100.0)
            elif value >= s:
                base_score = self._linear_map(value, s, h, 60.0, 80.0)
            elif value >= w:
                base_score = self._linear_map(value, w, s, 40.0, 60.0)
            else:
                base_score = self._linear_map(value, w * 0.5, w, 0.0, 40.0)
        else:
            if value <= h:
                base_score = self._linear_map(value, h * 0.5, h, 100.0, 80.0)
            elif value <= s:
                base_score = self._linear_map(value, h, s, 80.0, 60.0)
            elif value <= w:
                base_score = self._linear_map(value, s, w, 60.0, 40.0)
            else:
                base_score = self._linear_map(value, w, w * 1.5, 40.0, 0.0)

        base_score = max(0.0, min(100.0, base_score))
        status, status_name = self._score_status(base_score)

        return IndicatorScore(
            indicator=indicator,
            raw_value=value,
            score=base_score,
            status=status,
            status_name=status_name,
            contribution=0.0,  # 稍后计算
        )

    @staticmethod
    def _linear_map(value: float, x0: float, x1: float, y0: float, y1: float) -> float:
        """线性插值。"""
        if abs(x1 - x0) < 1e-9:
            return (y0 + y1) / 2
        return y0 + (value - x0) * (y1 - y0) / (x1 - x0)

    def _score_status(self, score: float) -> tuple[str, str]:
        """根据分数判定健康状态。"""
        for level in self.config.health_levels:
            if score >= level.min_score:
                return level.level, level.name
        return "risk", "风险"

    def _total_status(self, score: float) -> HealthLevel:
        """根据总分判定健康等级。"""
        for level in self.config.health_levels:
            if score >= level.min_score:
                return level
        return self.config.health_levels[-1]

    def calculate(
        self,
        city_name: str,
        year: int,
        indicator_values: Mapping[str, float | None],
    ) -> CEHIResult:
        """计算指定城市的 CEHI 诊断结果。"""
        dimension_scores: list[DimensionScore] = []

        for dimension in self.config.dimensions:
            indicator_scores: list[IndicatorScore] = []
            weighted_sum = 0.0
            total_weight = 0.0

            for indicator in dimension.indicators:
                value = indicator_values.get(indicator.id)
                score_result = self._indicator_score(indicator, value)
                indicator_scores.append(score_result)
                if score_result.status != "missing":
                    weighted_sum += score_result.score * indicator.weight
                    total_weight += indicator.weight

            dim_score = weighted_sum / total_weight if total_weight > 0 else 0.0
            status, status_name = self._score_status(dim_score)

            dimension_scores.append(
                DimensionScore(
                    dimension=dimension,
                    score=dim_score,
                    status=status,
                    status_name=status_name,
                    indicator_scores=indicator_scores,
                    weight=dimension.weight,
                )
            )

        # 计算总分
        total_weighted = sum(ds.score * ds.weight for ds in dimension_scores)
        total_weight = sum(ds.weight for ds in dimension_scores)
        total_score = total_weighted / total_weight if total_weight > 0 else 0.0

        level = self._total_status(total_score)

        # 计算指标贡献度（对总分的拖累/提升）
        all_indicator_scores: list[IndicatorScore] = []
        for ds in dimension_scores:
            for ind_score in ds.indicator_scores:
                if ind_score.status == "missing":
                    continue
                # 贡献度 = 该指标实际加权贡献 - 若按维度平均分计算的贡献
                dim_avg = ds.score
                gap = ind_score.score - dim_avg
                ind_weight_in_total = ind_score.indicator.weight * ds.weight
                contribution = gap * ind_weight_in_total
                all_indicator_scores.append(
                    IndicatorScore(
                        indicator=ind_score.indicator,
                        raw_value=ind_score.raw_value,
                        score=ind_score.score,
                        status=ind_score.status,
                        status_name=ind_score.status_name,
                        contribution=contribution,
                    )
                )

        # 强项与短板（强项按贡献度降序，短板按拖累程度升序）
        sorted_by_contribution = sorted(all_indicator_scores, key=lambda x: x.contribution, reverse=True)
        strengths = [s for s in sorted_by_contribution if s.contribution > 0]
        weaknesses = [s for s in sorted_by_contribution if s.contribution < 0]
        top_strengths = strengths[:5]
        # 短板取拖累最大的 5 个，并按从差到较好排序
        top_weaknesses = weaknesses[-5:][::-1]

        recommendations = self._generate_recommendations(dimension_scores, top_weaknesses)

        return CEHIResult(
            city_name=city_name,
            year=year,
            total_score=total_score,
            status=level.level,
            status_name=level.name,
            level=level,
            dimension_scores=dimension_scores,
            top_strengths=top_strengths,
            top_weaknesses=top_weaknesses,
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self,
        dimension_scores: list[DimensionScore],
        top_weaknesses: list[IndicatorScore],
    ) -> list[str]:
        """基于短板生成建议。"""
        recommendations: list[str] = []

        # 按维度得分排序，找出最弱的维度
        weak_dimensions = sorted(dimension_scores, key=lambda x: x.score)[:2]
        for ds in weak_dimensions:
            recommendations.append(
                f"优先提升「{ds.dimension.name}」维度（当前得分 {ds.score:.1f}），重点改善该维度下的短板指标。"
            )

        for weakness in top_weaknesses:
            ind = weakness.indicator
            if ind.direction == "positive":
                recommendations.append(
                    f"「{ind.name}」当前为 {weakness.raw_value}{ind.unit}（得分 {weakness.score:.1f}），"
                    f"建议通过政策引导或资源配置提升该指标。"
                )
            else:
                recommendations.append(
                    f"「{ind.name}」当前为 {weakness.raw_value}{ind.unit}（得分 {weakness.score:.1f}），"
                    f"建议采取措施降低该指标数值。"
                )

        return recommendations

    def benchmark(
        self,
        target_city: str,
        target_values: Mapping[str, float | None],
        peers: Mapping[str, Mapping[str, float | None]],
        year: int = 2024,
    ) -> dict[str, Any]:
        """城市对标分析。"""
        target_result = self.calculate(target_city, year, target_values)
        peer_results = [self.calculate(name, year, values) for name, values in peers.items()]
        all_results = [target_result] + peer_results
        all_results.sort(key=lambda x: x.total_score, reverse=True)

        # 找相似城市（基于维度得分向量的欧氏距离）
        target_vec = [ds.score for ds in target_result.dimension_scores]
        similarities: list[tuple[str, float]] = []
        for pr in peer_results:
            peer_vec = [ds.score for ds in pr.dimension_scores]
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(target_vec, peer_vec)))
            similarities.append((pr.city_name, dist))
        similarities.sort(key=lambda x: x[1])

        return {
            "target_city": target_city,
            "target_score": target_result.total_score,
            "target_status": target_result.status_name,
            "rankings": [{"city": r.city_name, "score": r.total_score, "status": r.status_name} for r in all_results],
            "similar_cities": [{"city": name, "distance": round(dist, 2)} for name, dist in similarities[:3]],
            "best_practice": self._best_practice(target_result, peer_results[0] if peer_results else None),
        }

    def _best_practice(
        self,
        target: CEHIResult,
        best_peer: CEHIResult | None,
    ) -> dict[str, Any]:
        """生成与标杆城市的差距分析。"""
        if best_peer is None:
            return {"peer": None, "gap_dimensions": []}

        gaps = []
        for t_ds, p_ds in zip(target.dimension_scores, best_peer.dimension_scores):
            gap = p_ds.score - t_ds.score
            if gap > 5:
                gaps.append(
                    {
                        "dimension": t_ds.dimension.name,
                        "target_score": t_ds.score,
                        "peer_score": p_ds.score,
                        "gap": gap,
                        "suggestion": f"学习 {best_peer.city_name} 在「{t_ds.dimension.name}」维度的经验，"
                        f"缩小 {gap:.1f} 分的差距。",
                    }
                )

        return {
            "peer": best_peer.city_name,
            "peer_score": best_peer.total_score,
            "gap_dimensions": sorted(gaps, key=lambda x: x["gap"], reverse=True),
        }


def get_demo_values() -> dict[str, float | None]:
    """返回演示用的指标原始值。"""
    return {
        # 经济活力
        "gdp_growth": 5.8,
        "gdp_per_capita": 128000,
        "tertiary_industry_ratio": 58.0,
        "retail_sales_growth": 6.2,
        "fixed_asset_investment_growth": 3.5,
        # 产业结构
        "high_tech_industry_ratio": 42.0,
        "strategic_emerging_ratio": 16.0,
        "enterprise_density": 650,
        "listed_companies": 68,
        "industrial_concentration": 48.0,
        # 财政健康
        "fiscal_revenue_growth": 4.5,
        "fiscal_self_sufficiency": 55.0,
        "debt_ratio": 185.0,
        "tax_revenue_ratio": 72.0,
        "fund_revenue_growth": -2.0,
        # 民生福祉
        "disposable_income": 58000,
        "urbanization_rate": 72.0,
        "registered_unemployment_rate": 3.8,
        "education_expenditure_ratio": 11.0,
        "medical_expenditure_ratio": 8.0,
        # 创新驱动
        "rd_intensity": 2.8,
        "patents_per_10000": 22,
        "high_tech_enterprises": 1800,
        "university_count": 35,
        "talent_inflow_rate": 1.2,
        # 开放水平
        "import_export_growth": 4.0,
        "fdi_growth": 3.5,
        "foreign_trade_dependency": 28.0,
        "free_trade_zone": 2,
        "international_routes": 18,
    }


def health_index_demo() -> CEHIResult:
    """生成一个演示用的 CEHI 计算结果。"""
    engine = CEHIEngine()
    return engine.calculate("示例市", 2024, get_demo_values())


if __name__ == "__main__":
    result = health_index_demo()
    print(f"城市: {result.city_name}")
    print(f"年份: {result.year}")
    print(f"CEHI总分: {result.total_score:.2f}")
    print(f"健康等级: {result.status_name} {result.level.emoji}")
    print("\n各维度得分:")
    for ds in result.dimension_scores:
        print(f"  {ds.dimension.name}: {ds.score:.2f} ({ds.status_name})")
    print("\n主要短板:")
    for w in result.top_weaknesses:
        print(f"  {w.indicator.name}: {w.raw_value}{w.indicator.unit} -> {w.score:.1f}分")
