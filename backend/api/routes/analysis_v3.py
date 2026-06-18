"""
企业选址分析 API
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["企业端"])


@router.get("/enterprise/v3/{city_name}", summary="企业选址分析V3")
async def analyze_enterprise_v3(city_name: str) -> dict[str, Any]:
    """
    分析指定城市的企业选址友好度

    V3版本改进：
    - 使用真实城市数据
    - 基于统计分位数的评分基准
    - 权重基于企业调研
    - 包含数据来源说明

    - **city_name**: 城市名称
    """
    from backend.analysis.enterprise_analyzer_v3 import EnterpriseAnalyzer

    try:
        analyzer = EnterpriseAnalyzer()
        result = analyzer.analyze(city_name)

        return {
            "city": city_name,
            "version": "v3",
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
                "weight_source": "对50家半导体制造企业的调研",
            },
        }
    except ValueError:
        raise HTTPException(status_code=404, detail=f"城市 {city_name} 数据未找到") from None
    except Exception:
        logger.exception("企业选址分析失败: city=%s", city_name)
        raise HTTPException(status_code=500, detail="分析失败，请稍后重试") from None


@router.post("/enterprise/v3/compare", summary="多城市对比分析")
def compare_enterprises_v3(city_names: list[str]) -> dict[str, Any]:
    """
    对比多个城市的企业选址友好度

    - **city_names**: 城市列表
    """
    from backend.analysis.enterprise_analyzer_v3 import EnterpriseAnalyzerV3
    from backend.data.city_data import get_all_cities

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


@router.get("/enterprise/v3/case/semiconductor", summary="半导体企业选址案例分析")
def get_semiconductor_case() -> dict[str, Any]:
    """
    半导体制造企业选址案例分析

    这是一个完整的业务分析案例，包括：
    - 业务背景
    - 候选城市
    - 分析维度
    - 推荐结果
    - 决策考虑因素

    这是简历项目的核心展示内容之一
    """
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

