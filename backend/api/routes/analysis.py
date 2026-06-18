"""
产业分析 API
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.analysis.enterprise_analyzer_v3 import enterprise_analyzer
from backend.analysis.government_analyzer import GovernmentAnalyzer
from backend.analysis.real_data_analysis import real_data_analyzer
from config.analysis_config import AnalysisConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["产业端"])


class AnalysisRequest(BaseModel):
    """分析请求"""

    region: str = AnalysisConfig.DEFAULT_REGION
    industry: str = AnalysisConfig.DEFAULT_INDUSTRY
    year: int = AnalysisConfig.DEFAULT_YEAR
    data: dict[str, Any] | None = None


@router.post("/enterprise", summary="企业端综合分析")
def enterprise_analysis(request: AnalysisRequest):
    """基于真实城市数据，对企业选址进行成本、供应链、政策环境评分。"""
    try:
        logger.info("企业端分析请求: %s - %s - %s", request.region, request.industry, request.year)

        data = request.data or {}
        data.update(
            {
                "region": request.region,
                "industry": request.industry,
                "year": request.year,
                "land_price": data.get("land_price", 800.0),
                "salary_level": data.get("salary_level", 15000.0),
                "energy_cost": data.get("energy_cost", 1.2),
                "financing_cost": data.get("financing_cost", 4.5),
                "local_support_rate": data.get("local_support_rate", 75.0),
                "avg_delivery_time": data.get("avg_delivery_time", 3.0),
                "location_quotient": data.get("location_quotient", 2.5),
                "tax_reduction": data.get("tax_reduction", 500.0),
                "tax_coverage": data.get("tax_coverage", 85.0),
                "rd_subsidy": data.get("rd_subsidy", 200.0),
                "avg_approval_time": data.get("avg_approval_time", 5.0),
            }
        )

        report = enterprise_analyzer.generate_comprehensive_report(data)
        return {"status": "success", "data": report}

    except Exception as e:
        logger.exception("企业端分析失败: %s", e)
        raise HTTPException(status_code=500, detail="企业端分析失败，请稍后重试") from None


@router.get("/enterprise/sample", summary="获取企业端示例数据")
def get_enterprise_sample_data(
    region: str = Query(AnalysisConfig.DEFAULT_REGION),
    industry: str = Query(AnalysisConfig.DEFAULT_INDUSTRY),
    year: int = Query(AnalysisConfig.DEFAULT_YEAR),
):
    """返回企业端分析所需的指标模板，可在此基础上修改后提交分析。"""
    sample_data = {
        "region": region,
        "industry": industry,
        "year": year,
        "land_price": 800.0,
        "salary_level": 15000.0,
        "energy_cost": 1.2,
        "financing_cost": 4.5,
        "local_support_rate": 75.0,
        "avg_delivery_time": 3.0,
        "location_quotient": 2.5,
        "tax_reduction": 500.0,
        "tax_coverage": 85.0,
        "rd_subsidy": 200.0,
        "avg_approval_time": 5.0,
    }

    try:
        macro_df = real_data_analyzer.fetch_macro_data()
        sample_data["macro_reference"] = {
            "available_years": len(macro_df),
            "latest_gdp": float(macro_df.iloc[-1]["gdp"]) if len(macro_df) > 0 else None,
            "data_source": "akshare",
        }
    except Exception as e:
        logger.warning("获取宏观参考数据失败: %s", e)

    return sample_data


@router.get("/config", summary="获取分析配置")
def get_analysis_config():
    """获取分析平台的默认配置"""
    return AnalysisConfig.get_config()


@router.post("/government", summary="政府端产业分析")
def government_analysis(request: AnalysisRequest):
    """基于真实城市数据，评估财政杠杆、产业带动效应与产业链完整性。"""
    try:
        logger.info("政府端分析请求: %s - %s - %s", request.region, request.industry, request.year)

        analyzer = GovernmentAnalyzer()
        data = dict(request.data or {})
        data["region"] = request.region
        data["industry"] = request.industry
        data["year"] = request.year

        report = analyzer.generate_comprehensive_report(data)

        # 映射为前端兼容格式
        fiscal = report.get("fiscal_leverage", {})
        driving = report.get("industry_driving", {})

        return {
            "status": "success",
            "data": {
                "fiscal_leverage": {
                    "score": fiscal.get("fiscal_leverage_score", 0.0),
                    "revenue_efficiency": fiscal.get("fiscal_self_sufficiency", 0.0),
                    "expenditure_efficiency": fiscal.get("funding_efficiency", 0.0),
                },
                "industry_drive": {
                    "score": driving.get("driving_score", 0.0),
                    "employment_contribution": driving.get("direct_effects", {}).get("employment_driven", 0.0),
                    "tax_contribution": driving.get("direct_effects", {}).get("tax_contribution", 0.0),
                },
                "industry_chain": report.get("industry_chain", {}),
                "overall_score": report.get("overall_score", 0.0),
                "policy_recommendations": report.get("policy_recommendations", []),
            },
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("政府端分析失败: %s", e)
        raise HTTPException(status_code=500, detail="政府端分析失败，请稍后重试") from None
