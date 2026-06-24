"""
产业预测引擎

采用“基准时序预测 + 多因素调整”的两段式模型：
1. 基准：用已有 forecast_engine 对产业历史指标做趋势外推；
2. 调整：根据政策、技术、市场需求、供应链、社会情绪等因素，
   对基准增速做加权修正，使预测更贴近产业真实未来。

设计原则：
- 透明可解释：每个因素的影响方向和幅度公开；
- 合理稳健：因素权重之和不必为 1，通过加权平均后做饱和度裁剪；
- 不黑箱：不用复杂 ML，只用经济学上可解释的调整。
"""

from __future__ import annotations

import logging
import math
from typing import Any

from backend.core.forecast_engine import (
    arima_forecast,
    ensemble_forecast,
    ets_forecast,
    linear_regression_forecast,
)
from backend.industries.models import FactorImpact, Industry

logger = logging.getLogger(__name__)

# 默认因素：与 config/industries/template.py 和调查数据指标对齐
DEFAULT_FACTOR_CATEGORIES = {
    "policy_support": {"name": "政策支持", "default_weight": 0.25},
    "technology_maturity": {"name": "技术成熟度", "default_weight": 0.20},
    "market_demand": {"name": "市场需求", "default_weight": 0.25},
    "supply_chain_risk": {"name": "供应链风险", "default_weight": 0.15},
    "social_sentiment": {"name": "社会情绪/人才供给", "default_weight": 0.15},
}


def compute_factor_adjustment(factors: list[FactorImpact]) -> float:
    """
    计算多因素对产业增速的综合调整量。

    公式：adj = Σ(score_i × weight_i) / Σ|weight_i|
    结果裁剪到 [-0.15, 0.15]，避免单一因素过度放大或压低预测。
    """
    if not factors:
        return 0.0

    total_weight = sum(f.weight for f in factors)
    if total_weight == 0:
        return 0.0

    weighted_score = sum(f.score * f.weight for f in factors) / total_weight
    # 裁剪：即便是强政策刺激，年化增速调整也不超过 ±15 个百分点
    return max(-0.15, min(0.15, weighted_score))


def forecast_industry(
    industry: Industry,
    indicator: str = "output_value",
    forecast_years: int = 5,
    use_factors: bool = True,
) -> dict[str, Any]:
    """
    预测产业未来指标。

    Args:
        industry: 产业实体
        indicator: 要预测的指标名
        forecast_years: 预测年数
        use_factors: 是否启用多因素调整

    Returns:
        {
            "industry_code", "industry_name", "region_code", "indicator",
            "historical_years", "historical_values",
            "forecast_years", "forecast_values", "lower_95", "upper_95",
            "factor_adjustment_pct", "baseline_cagr_pct", "adjusted_cagr_pct",
            "method", "factors"
        }
    """
    valid_rows = [
        (int(row["year"]), float(row[indicator]))
        for row in industry.historical_data
        if indicator in row and row[indicator] is not None and row.get("year") is not None
    ]
    if not valid_rows:
        raise ValueError(f"指标 {indicator} 无有效历史数据")
    valid_rows.sort(key=lambda x: x[0])
    years = [r[0] for r in valid_rows]
    series = [r[1] for r in valid_rows]

    if len(series) < 3:
        return {
            "error": f"产业 {industry.name} 的指标 {indicator} 历史数据不足（至少 3 年）",
            "industry_code": industry.code,
            "indicator": indicator,
            "available_years": len(series),
        }

    # 1. 基准预测：三模型集成
    arima = arima_forecast(series, forecast_years)
    ets = ets_forecast(series, forecast_years)
    lr = linear_regression_forecast(series, forecast_years)
    base = ensemble_forecast(arima, ets, lr)
    base_values = base["predictions"]
    lower = base["lower_ci"]
    upper = base["upper_ci"]

    # 计算基准末期 CAGR
    baseline_cagr = _cagr(series[-1], base_values[-1], forecast_years)

    # 2. 因素调整
    factor_adj = compute_factor_adjustment(industry.factors) if use_factors else 0.0
    adjusted_cagr = baseline_cagr + factor_adj * 100

    # 3. 用调整后的 CAGR 重新生成预测路径
    adjusted_values = _apply_cagr_path(series[-1], adjusted_cagr / 100, forecast_years)

    # 置信区间也随调整整体平移，保持区间宽度不变
    width = [u - lo for u, lo in zip(upper, lower)]
    adjusted_lower = [max(0.0, v - w / 2) for v, w in zip(adjusted_values, width)]
    adjusted_upper = [v + w / 2 for v, w in zip(adjusted_values, width)]

    forecast_years_list = [years[-1] + i + 1 for i in range(forecast_years)]

    return {
        "industry_code": industry.code,
        "industry_name": industry.name,
        "region_code": industry.region_code,
        "indicator": indicator,
        "historical_years": years,
        "historical_values": series,
        "forecast_years": forecast_years_list,
        "forecast_values": adjusted_values,
        "lower_95": adjusted_lower,
        "upper_95": adjusted_upper,
        "factor_adjustment_pct": round(factor_adj * 100, 2),
        "baseline_cagr_pct": round(baseline_cagr, 2),
        "adjusted_cagr_pct": round(adjusted_cagr, 2),
        "method": f"{base['method']} + 多因素调整" if use_factors else base["method"],
        "factors": [
            {"name": f.name, "score": f.score, "weight": f.weight, "source": f.source} for f in industry.factors
        ],
    }


def _cagr(start: float, end: float, years: int) -> float:
    """计算复合年化增长率（%）"""
    if start <= 0 or years <= 0 or end <= 0:
        return 0.0
    return (math.pow(end / start, 1.0 / years) - 1.0) * 100


def _apply_cagr_path(last_value: float, cagr: float, years: int) -> list[float]:
    """从 last_value 出发，按 CAGR 生成未来 years 年路径"""
    return [round(last_value * math.pow(1 + cagr, i + 1), 4) for i in range(years)]
