"""
投资决策级风险分析 API

将 backend.core.risk_engine 的能力暴露为 REST 接口，支持：
- 滚动年化波动率 / GARCH 条件波动率
- 历史模拟 VaR / CVaR
- 基线 / 乐观 / 悲观 / 衰退 四档情景分析
- 残差 bootstrap 蒙特卡洛模拟

调用流程：
1. 取城市指定指标的历史时序
2. 用 forecast_engine 生成 baseline 预测
3. 用 risk_engine 计算风险指标
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.core.forecast_engine import forecast_full_pipeline
from backend.core.province_aggregator import SUPPORTED_INDICATORS
from backend.core.risk_engine import risk_full_pipeline
from backend.data.city_data import get_all_forecast_cities, get_historical_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk", tags=["风险分析"])


class RiskAnalyzeRequest(BaseModel):
    """风险分析请求"""

    city_name: str = Field(..., min_length=1, description="城市名称")
    indicator: str = Field("gdp", description=f"指标代码,支持: {', '.join(SUPPORTED_INDICATORS)}")
    forecast_years: int = Field(5, ge=1, le=20, description="预测年数")
    n_sims: int = Field(1000, ge=100, le=10000, description="蒙特卡洛模拟次数")

    @field_validator("indicator")
    @classmethod
    def _validate_indicator(cls, v: str) -> str:
        if v not in SUPPORTED_INDICATORS:
            raise ValueError(f"不支持的指标 '{v}'")
        return v


class RiskAnalyzeResponse(BaseModel):
    """风险分析响应"""

    city: str
    indicator: str
    forecast_years: int
    historical_years: list[int]
    historical_values: list[float]
    volatility: dict[str, Any]
    garch: dict[str, Any]
    var_95: dict[str, Any]
    var_99: dict[str, Any]
    scenarios: dict[str, Any]
    monte_carlo: dict[str, Any]
    engine_stack: dict[str, Any]


def _get_city_indicator_series(city_name: str, indicator: str) -> tuple[list[int], list[float]]:
    """获取城市指定指标的历史年份与数值序列。"""
    df = get_historical_data(city_name)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"城市 {city_name} 无历史数据")

    if "year" not in df.columns:
        raise HTTPException(status_code=503, detail=f"城市 {city_name} 历史数据缺少年份字段")

    if indicator not in df.columns:
        available = [c for c in df.columns if c != "year"]
        raise HTTPException(
            status_code=400,
            detail=f"城市 {city_name} 不存在指标 '{indicator}'，可用指标: {available}",
        )

    df = df.sort_values("year").reset_index(drop=True)
    years = df["year"].astype(int).tolist()
    values = df[indicator].astype(float).tolist()
    return years, values


@router.post("/analyze", response_model=RiskAnalyzeResponse, summary="城市经济指标风险分析")
async def analyze_risk(request: RiskAnalyzeRequest) -> RiskAnalyzeResponse:
    """
    对指定城市 × 指定指标进行综合风险分析。

    返回：滚动波动率、GARCH 条件波动率（若安装 arch 库）、VaR 95/99、
          四档情景预测、蒙特卡洛 P5/P50/P95 分位及尾部风险概率。
    """
    if request.city_name not in get_all_forecast_cities():
        raise HTTPException(status_code=404, detail=f"城市 {request.city_name} 不在预测城市列表中")

    try:
        years, values = _get_city_indicator_series(request.city_name, request.indicator)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("读取城市指标序列失败: %s", e, exc_info=True)
        raise HTTPException(status_code=503, detail="读取城市指标序列失败") from None

    if len(values) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"指标 '{request.indicator}' 的历史样本不足（需要至少 5 年，实际 {len(values)} 年）",
        )

    try:
        # 用 forecast_engine 生成 baseline 预测
        forecast_result = forecast_full_pipeline(
            values,
            start_year=years[0],
            years=request.forecast_years,
        )
        baseline = forecast_result["ensemble"]["predictions"]
    except Exception as e:
        logger.error("生成 baseline 预测失败: %s", e, exc_info=True)
        raise HTTPException(status_code=503, detail="生成 baseline 预测失败") from None

    try:
        risk_result = risk_full_pipeline(
            values,
            baseline_predictions=baseline,
            starting_value=values[-1],
            n_sims=request.n_sims,
        )
    except Exception as e:
        logger.error("风险分析失败: %s", e, exc_info=True)
        raise HTTPException(status_code=503, detail="风险分析计算失败") from None

    return RiskAnalyzeResponse(
        city=request.city_name,
        indicator=request.indicator,
        forecast_years=request.forecast_years,
        historical_years=years,
        historical_values=[round(v, 4) for v in values],
        volatility=risk_result["volatility"],
        garch=risk_result["garch"],
        var_95=risk_result["var_95"],
        var_99=risk_result["var_99"],
        scenarios=risk_result["scenarios"],
        monte_carlo=risk_result["monte_carlo"],
        engine_stack=risk_result["engine_stack"],
    )


@router.get("/indicators", summary="列出风险分析支持的指标")
async def list_risk_indicators() -> dict[str, Any]:
    """返回风险分析支持的指标列表（与预测指标一致）。"""
    return {
        "supported_indicators": SUPPORTED_INDICATORS,
        "total": len(SUPPORTED_INDICATORS),
        "note": "建议使用 GDP、财政收入、人口等长周期绝对量指标，样本越长风险指标越稳定",
    }
