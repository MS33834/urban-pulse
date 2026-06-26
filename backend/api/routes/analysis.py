"""
产业分析 API
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.analysis.enterprise_analyzer_v3 import EnterpriseAnalyzer, EnterpriseAnalyzerV3, enterprise_analyzer
from backend.analysis.government_analyzer import GovernmentAnalyzer
from backend.analysis.real_data_analysis import real_data_analyzer
from backend.data.city_data import get_all_cities
from config.analysis_config import AnalysisConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["企业端"])


class AnalysisRequest(BaseModel):
    """分析请求"""

    region: str = AnalysisConfig.DEFAULT_REGION
    industry: str = AnalysisConfig.DEFAULT_INDUSTRY
    year: int = Field(AnalysisConfig.DEFAULT_YEAR, ge=1900, le=2200, description="分析年份")
    data: dict[str, Any] | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "region": "深圳",
                    "industry": "半导体",
                    "year": 2025,
                    "data": {
                        "land_price": 800.0,
                        "salary_level": 15000.0,
                        "energy_cost": 1.2,
                        "financing_cost": 4.5,
                    },
                }
            ]
        }
    }


@router.post("/enterprise", summary="企业端综合分析")
def enterprise_analysis(request: AnalysisRequest):
    """基于真实城市数据，对企业选址进行成本、供应链、政策环境评分。"""
    try:
        logger.info("企业端分析请求: %s - %s - %s", request.region, request.industry, request.year)

        # 复制入参字典,避免直接修改 request.data 造成副作用
        data = dict(request.data or {})
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


@router.get("/enterprise/location/{city_name}", summary="企业选址分析")
async def analyze_enterprise_location(city_name: str) -> dict[str, Any]:
    """分析指定城市的企业选址友好度。"""
    try:
        analyzer = EnterpriseAnalyzer()
        result = analyzer.analyze(city_name)

        return {
            "city": city_name,
            "business_cost_score": result.business_cost_score,
            "supply_chain_score": result.supply_chain_score,
            "policy_benefit_score": result.policy_benefit_score,
            "total_score": result.total_score,
            "details": {
                "cost_details": result.cost_details,
                "supply_details": result.supply_details,
                "policy_details": result.policy_details,
            },
            "suggestions": result.suggestions,
            "data_source": result.data_source,
            "methodology": {
                "scoring_basis": "基于真实城市数据的统计分位数（25%/50%/75%）",
                "weight_source": "对 50 家半导体制造企业的调研",
            },
        }
    except ValueError:
        raise HTTPException(status_code=404, detail=f"城市 {city_name} 数据未找到") from None
    except Exception:
        logger.exception("企业选址分析失败: city=%s", city_name)
        raise HTTPException(status_code=500, detail="分析失败，请稍后重试") from None


@router.post("/enterprise/compare", summary="多城市企业选址对比")
def compare_enterprises(city_names: list[str]) -> dict[str, Any]:
    """对比多个城市的企业选址友好度。"""
    if len(city_names) > 20:
        raise HTTPException(status_code=422, detail="城市数量不能超过 20 个") from None
    valid_cities = [city for city in city_names if city in get_all_cities()]
    if not valid_cities:
        raise HTTPException(status_code=400, detail="未提供有效的城市名称") from None

    analyzer = EnterpriseAnalyzerV3()
    comparison_df = analyzer.compare_multiple_cities(valid_cities)

    return {
        "cities": valid_cities,
        "comparison": comparison_df.to_dict(orient="records") if hasattr(comparison_df, "to_dict") else comparison_df,
        "ranked_by": "total_score",
    }


@router.get("/enterprise/case/semiconductor", summary="半导体企业选址案例")
def get_semiconductor_case() -> dict[str, Any]:
    """半导体制造企业选址案例分析。"""
    from backend.analysis.enterprise_analyzer_v3 import run_semiconductor_fab_location_analysis

    try:
        result = run_semiconductor_fab_location_analysis()

        return {
            "case_title": "半导体制造企业选址分析",
            "business_background": result.get("business_background", ""),
            "candidate_cities": result.get("candidate_cities", []),
            "analysis": result,
            "recommendation": result.get("recommendation", {}),
            "data_quality_report": result.get("data_quality_report", {}),
            "methodology": result.get("benchmark_info", {}),
        }
    except Exception:
        logger.exception("半导体选址案例分析失败")
        raise HTTPException(status_code=500, detail="案例分析失败，请稍后重试") from None


@router.get("/config", summary="获取分析配置")
def get_analysis_config():
    """获取分析平台的默认配置。"""
    return AnalysisConfig.get_config()


@router.post("/government", summary="政府端产业分析", tags=["政府端"])
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
        raise HTTPException(status_code=404, detail="指定的城市或区域不存在") from e
    except Exception as e:
        logger.exception("政府端分析失败: %s", e)
        raise HTTPException(status_code=500, detail="政府端分析失败，请稍后重试") from None
