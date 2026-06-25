"""
数学模型 API

提供 VAR、XGBoost、TFP、区位商、DPSR 等模型的调用接口。
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.analytics.models.forecast.var_model import VARModel
from backend.analytics.models.forecast.xgboost_model import XGBoostForecastModel
from backend.analytics.models.industry.location_quotient import LocationQuotientModel
from backend.analytics.models.quality.tfp_model import TFPModel
from backend.analytics.models.resilience.dpsr_model import DPSRResilienceModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/models", tags=["数学模型"])


class DataFrameInput(BaseModel):
    """通用数据输入"""

    data: list[dict[str, Any]] = Field(..., min_length=1, description="数据行列表")
    entity_col: str | None = Field(None, description="实体列名")


class VARInput(DataFrameInput):
    """VAR 模型输入"""

    variables: list[str] | None = Field(None, description="参与建模的变量，为空则使用所有数值列")
    lags: int = Field(2, ge=1, le=5)
    steps: int = Field(3, ge=1, le=10)


class XGBoostInput(DataFrameInput):
    """XGBoost 模型输入"""

    target: str = Field(..., description="目标变量")
    features: list[str] = Field(default_factory=list, description="特征变量")
    lags: int = Field(2, ge=1, le=5)
    steps: int = Field(3, ge=1, le=10)


class TFPInput(DataFrameInput):
    """TFP 模型输入"""

    output_col: str = "gdp"
    capital_col: str = "capital"
    labor_col: str = "labor"


class LQInput(DataFrameInput):
    """区位商模型输入"""

    region_col: str = "region"
    industry_col: str = "industry"
    value_col: str = "value"


class DPSRInput(DataFrameInput):
    """DPSR 韧性模型输入"""

    driver_indicators: list[str] = Field(default_factory=list)
    pressure_indicators: list[str] = Field(default_factory=list)
    state_indicators: list[str] = Field(default_factory=list)
    response_indicators: list[str] = Field(default_factory=list)
    weights: dict[str, float] | None = None


def _to_dataframe(body: DataFrameInput) -> pd.DataFrame:
    return pd.DataFrame(body.data)


@router.post("/var", summary="VAR 多变量预测")
async def run_var(body: VARInput) -> dict[str, Any]:
    """向量自回归模型：分析多变量联动关系并预测未来走势。"""
    try:
        df = _to_dataframe(body)
        variables = body.variables or [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        df = df[variables].dropna()
        model = VARModel(lags=body.lags)
        result = model.run(df, steps=body.steps)
        return {"success": True, **result}
    except Exception as e:
        logger.error("VAR 模型失败: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"VAR 模型失败: {e}") from None


@router.post("/xgboost", summary="XGBoost 非线性预测")
async def run_xgboost(body: XGBoostInput) -> dict[str, Any]:
    """基于梯度提升的多因素非线性预测。"""
    try:
        df = _to_dataframe(body)
        features = body.features or [c for c in df.columns if c != body.target and pd.api.types.is_numeric_dtype(df[c])]
        model = XGBoostForecastModel(target=body.target, features=features, lags=body.lags)
        result = model.run(df, steps=body.steps)
        return {"success": True, **result}
    except Exception as e:
        logger.error("XGBoost 模型失败: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"XGBoost 模型失败: {e}") from None


@router.post("/tfp", summary="全要素生产率 TFP 测算")
async def run_tfp(body: TFPInput) -> dict[str, Any]:
    """基于 Cobb-Douglas 生产函数测算全要素生产率。"""
    try:
        df = _to_dataframe(body)
        model = TFPModel(
            output_col=body.output_col,
            capital_col=body.capital_col,
            labor_col=body.labor_col,
        )
        result = model.run(df)
        return {"success": True, **result}
    except Exception as e:
        logger.error("TFP 模型失败: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"TFP 模型失败: {e}") from None


@router.post("/location-quotient", summary="区位商产业分析")
async def run_location_quotient(body: LQInput) -> dict[str, Any]:
    """区位商模型：识别地区专业化产业与比较优势。"""
    try:
        df = _to_dataframe(body)
        model = LocationQuotientModel(
            region_col=body.region_col,
            industry_col=body.industry_col,
            value_col=body.value_col,
        )
        result = model.run(df)
        return {"success": True, **result}
    except Exception as e:
        logger.error("区位商模型失败: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"区位商模型失败: {e}") from None


@router.post("/dpsr", summary="DPSR 经济韧性评估")
async def run_dpsr(body: DPSRInput) -> dict[str, Any]:
    """DPSR 经济韧性评估：驱动力-压力-状态-响应四维框架。"""
    try:
        df = _to_dataframe(body)
        model = DPSRResilienceModel(
            driver_indicators=body.driver_indicators,
            pressure_indicators=body.pressure_indicators,
            state_indicators=body.state_indicators,
            response_indicators=body.response_indicators,
            weights=body.weights,
        )
        result = model.run(df, entity_col=body.entity_col or "region")
        return {"success": True, **result}
    except Exception as e:
        logger.error("DPSR 模型失败: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"DPSR 模型失败: {e}") from None


@router.get("/list", summary="列出可用模型")
async def list_models() -> dict[str, Any]:
    """返回当前可用的数学模型列表。"""
    return {
        "success": True,
        "models": [
            {"id": "var", "name": "VAR 向量自回归", "type": "forecast", "description": "多变量时间序列联动分析与预测"},
            {"id": "xgboost", "name": "XGBoost 梯度提升", "type": "forecast", "description": "多因素非线性经济预测"},
            {"id": "tfp", "name": "全要素生产率 TFP", "type": "quality", "description": "Cobb-Douglas 生产函数测算技术进步"},
            {"id": "location-quotient", "name": "区位商 LQ", "type": "industry", "description": "地区专业化产业识别"},
            {"id": "dpsr", "name": "DPSR 经济韧性", "type": "resilience", "description": "驱动力-压力-状态-响应韧性评估"},
        ],
    }
