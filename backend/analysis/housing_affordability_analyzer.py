"""
住房可负担性分析器（插件示例）

作为 AnalysisPlugin 的示例实现，计算城市住房可负担性指标，
包括房价收入比、可负担性指数与压力等级。
"""

import logging
from typing import Any

from backend.analysis.base_analyzer import AnalysisPlugin

logger = logging.getLogger(__name__)


class HousingAffordabilityAnalyzer(AnalysisPlugin):
    """
    住房可负担性分析器。

    输入数据要求（city_data 字典）：
        - median_house_price: 房屋中位数价格
        - median_household_income: 家庭中位数年收入
        - mortgage_rate: （可选）房贷利率，默认 4.5%
        - loan_term_years: （可选）贷款年限，默认 30

    输出：
        - price_to_income_ratio: 房价收入比
        - affordability_index: 可负担性指数（0-100，越高越可负担）
        - monthly_mortgage_pct_income: 月供占收入比例
        - stress_level: 压力等级（low / moderate / high / severe）
    """

    def metadata(self) -> dict[str, Any]:
        return {
            "description": "计算城市住房可负担性指标，包括房价收入比、可负担性指数与压力等级。",
            "version": "0.1.0",
            "author": "Urban Pulse Team",
            "tags": ["housing", "affordability", "social"],
            "parameters": [
                {
                    "name": "mortgage_rate",
                    "type": "float",
                    "required": False,
                    "default": 4.5,
                    "description": "房贷利率（%）",
                },
                {
                    "name": "loan_term_years",
                    "type": "int",
                    "required": False,
                    "default": 30,
                    "description": "贷款年限",
                },
            ],
            "example": {
                "median_house_price": 600000,
                "median_household_income": 80000,
                "mortgage_rate": 4.5,
            },
        }

    def name(self) -> str:
        return "housing_affordability"

    def required_indicators(self) -> list[str]:
        return ["median_house_price", "median_household_income"]

    def analyze(self, city_data: dict, **params) -> dict[str, Any]:
        missing = [k for k in self.required_indicators() if k not in city_data]
        if missing:
            return {
                "status": "insufficient_data",
                "missing_indicators": missing,
                "message": f"缺少指标: {', '.join(missing)}",
            }

        price = float(city_data["median_house_price"])
        income = float(city_data["median_household_income"])
        rate = float(city_data.get("mortgage_rate", 4.5)) / 100
        term = int(city_data.get("loan_term_years", 30))

        if income <= 0 or price <= 0:
            return {
                "status": "invalid_data",
                "message": "房价与收入必须大于 0",
            }

        price_to_income = price / income

        # 月供 = P * (r/12) * (1 + r/12)^(12*n) / ((1 + r/12)^(12*n) - 1)
        monthly_rate = rate / 12
        n_months = term * 12
        if n_months <= 0:
            monthly_payment = 0.0
        elif monthly_rate == 0:
            monthly_payment = price / n_months
        else:
            factor = (1 + monthly_rate) ** n_months
            monthly_payment = (price * monthly_rate * factor) / (factor - 1)

        monthly_income = income / 12
        mortgage_pct_income = (monthly_payment / monthly_income) * 100

        # 可负担性指数：房价收入比越低越可负担
        # 国际通常认为 3-5 为合理区间
        if price_to_income <= 3:
            affordability_index = 100.0
            stress_level = "low"
        elif price_to_income <= 5:
            affordability_index = max(0.0, 100 - (price_to_income - 3) * 15)
            stress_level = "moderate"
        elif price_to_income <= 8:
            affordability_index = max(0.0, 70 - (price_to_income - 5) * 15)
            stress_level = "high"
        else:
            affordability_index = max(0.0, 25 - (price_to_income - 8) * 5)
            stress_level = "severe"

        return {
            "status": "success",
            "median_house_price": price,
            "median_household_income": income,
            "mortgage_rate_pct": rate * 100,
            "loan_term_years": term,
            "price_to_income_ratio": round(price_to_income, 2),
            "affordability_index": round(affordability_index, 2),
            "monthly_mortgage_pct_income": round(mortgage_pct_income, 2),
            "stress_level": stress_level,
            "interpretation": self._interpret(stress_level),
        }

    def _interpret(self, stress_level: str) -> str:
        interpretations = {
            "low": "住房可负担性良好，居民购房压力较小。",
            "moderate": "住房可负担性一般，购房需一定储蓄规划。",
            "high": "住房可负担性较差，居民购房压力较大。",
            "severe": "住房严重不可负担，需警惕金融风险与社会问题。",
        }
        return interpretations.get(stress_level, "")
