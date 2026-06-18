"""
产业管理模块

提供 Industry 实体、产业层级定义和产业预测能力，
作为 Urban Pulse 从“城市经济观测”扩展到“产业未来预测”的核心模块。
"""

from backend.industries.forecaster import compute_factor_adjustment, forecast_industry
from backend.industries.models import FactorImpact, Industry, IndustryLevel
from backend.industries.registry import IndustryRegistry, get_industry_registry

__all__ = [
    "Industry",
    "IndustryLevel",
    "FactorImpact",
    "IndustryRegistry",
    "get_industry_registry",
    "forecast_industry",
    "compute_factor_adjustment",
]
