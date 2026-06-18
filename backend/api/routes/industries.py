"""
产业 API 路由

产业预测是平台从“城市经济观测”升级为“产业未来预测”的关键能力。
端点支持发现产业、查看详情、以及基于多因素模型的未来预测。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.industries import (
    FactorImpact,
    Industry,
    IndustryLevel,
    forecast_industry,
    get_industry_registry,
)
from backend.regions import get_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/industries", tags=["产业"])


class IndustryCreateRequest(BaseModel):
    """创建产业请求"""

    code: str = Field(..., description="产业编码，如 semiconductor")
    name: str = Field(..., description="产业名称")
    region_code: str = Field(..., description="所属区域编码，如 CN-GD-SZ")
    level: IndustryLevel = Field(IndustryLevel.SECONDARY, description="产业层级")
    category: str = Field("", description="产业分类")
    key_indicators: dict[str, Any] = Field(default_factory=dict, description="关键指标定义")
    historical_data: list[dict[str, Any]] = Field(default_factory=list, description="年度历史数据")
    factors: list[dict[str, Any]] = Field(default_factory=list, description="影响因素列表")


class IndustryForecastRequest(BaseModel):
    """产业预测请求"""

    indicator: str = Field("output_value", description="要预测的指标名")
    forecast_years: int = Field(5, ge=1, le=20, description="预测年数")
    use_factors: bool = Field(True, description="是否启用多因素调整")


@router.get("/summary", summary="产业覆盖总览")
async def industry_summary() -> dict[str, Any]:
    """返回当前注册的产业总数及按区域分布。"""
    registry = get_industry_registry()
    return {"success": True, "summary": registry.summary()}


@router.get("", summary="列出产业")
async def list_industries(
    region_code: str | None = Query(None, description="按区域编码过滤"),
) -> dict[str, Any]:
    """列出产业，支持按区域过滤。"""
    registry = get_industry_registry()
    industries = registry.list_by_region(region_code) if region_code else registry.list_all()
    return {
        "success": True,
        "count": len(industries),
        "industries": [i.to_dict() for i in industries],
    }


@router.post("", summary="注册产业")
async def create_industry(request: IndustryCreateRequest) -> dict[str, Any]:
    """注册一个新的产业实体。"""
    region_registry = get_registry()
    if region_registry.get(request.region_code) is None:
        raise HTTPException(status_code=404, detail=f"区域不存在: {request.region_code}")

    factors = [FactorImpact(**f) for f in request.factors]
    industry = Industry(
        code=request.code,
        name=request.name,
        region_code=request.region_code,
        level=request.level,
        category=request.category,
        key_indicators=request.key_indicators,
        historical_data=request.historical_data,
        factors=factors,
    )

    registry = get_industry_registry()
    if not registry.register(industry):
        raise HTTPException(status_code=409, detail=f"产业已存在: {request.region_code}:{request.code}")

    return {"success": True, "industry": industry.to_dict()}


@router.get("/{region_code}/{industry_code}", summary="获取产业详情")
async def get_industry(region_code: str, industry_code: str) -> dict[str, Any]:
    """获取指定区域下某产业的完整信息。"""
    registry = get_industry_registry()
    industry = registry.get(region_code, industry_code)
    if industry is None:
        raise HTTPException(status_code=404, detail=f"产业不存在: {region_code}:{industry_code}")
    return {"success": True, "industry": industry.to_dict()}


@router.post("/{region_code}/{industry_code}/forecast", summary="产业未来预测")
async def forecast_industry_endpoint(
    region_code: str,
    industry_code: str,
    request: IndustryForecastRequest,
) -> dict[str, Any]:
    """
    对指定产业做未来 N 年预测。

    模型：基准时序预测（ARIMA + ETS + LR 集成）+ 多因素增速调整。
    因素包括政策支持、技术成熟度、市场需求、供应链风险、社会情绪等。
    """
    registry = get_industry_registry()
    industry = registry.get(region_code, industry_code)
    if industry is None:
        raise HTTPException(status_code=404, detail=f"产业不存在: {region_code}:{industry_code}")

    result = forecast_industry(
        industry,
        indicator=request.indicator,
        forecast_years=request.forecast_years,
        use_factors=request.use_factors,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"success": True, **result}
