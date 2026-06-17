"""
企业分析器 - 基于真实城市数据的统一版本

历史上有 V1/V2/V3 三个版本，现已合并为单一实现：
- 保留 V3 的真实数据驱动评分（基于统计分位数基准）
- 兼容 V1 的 dict 接口（generate_comprehensive_report / analyze_city / compare_cities）
- 提供 V3 的 dataclass 接口（analyze / compare_multiple_cities）
- 废弃 V2 的硬编码基准方式

所有调用方应统一使用本模块的 EnterpriseAnalyzer 或模块级单例 enterprise_analyzer。
"""

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd

from backend.analysis.base_analyzer import BaseAnalyzer
from backend.data.city_data import (
    generate_data_quality_report,
    get_all_cities,
    get_city_data,
    get_data_source_info,
    get_score_benchmarks,
    get_score_weights,
)

logger = logging.getLogger(__name__)


@dataclass
class EnterpriseAnalysis:
    """企业分析结果（结构化返回）"""

    region: str
    year: int
    business_cost_score: float
    supply_chain_score: float
    policy_benefit_score: float
    total_score: float
    cost_details: dict[str, float]
    supply_details: dict[str, float]
    policy_details: dict[str, float]
    suggestions: list[str]
    data_source: dict[str, Any]


class EnterpriseAnalyzer(BaseAnalyzer):
    """
    企业分析器 - 统一实现

    基于真实城市数据和统计分位数基准计算评分。
    同时支持两种调用风格：
    1. 结构化：analyzer.analyze(city) -> EnterpriseAnalysis
    2. 字典报告：analyzer.generate_comprehensive_report(data) / analyze_city(city) -> dict
    """

    def __init__(self):
        super().__init__()
        self.name = "EnterpriseAnalyzer"
        self.benchmarks = get_score_benchmarks()  # 基于真实数据的基准
        self.weights = get_score_weights()  # 基于调研的权重
        self.data_source_info = get_data_source_info()
        logger.info("EnterpriseAnalyzer initialized with real city data")

    # ------------------------------------------------------------------
    # 评分核心
    # ------------------------------------------------------------------
    def _calculate_score(
        self,
        value: float,
        metric: str,
        higher_is_better: bool = False,
    ) -> float:
        """基于真实基准值计算单个指标得分。

        基准值：low (25%), medium (50%), high (75%) 分位数。
        """
        bench = self.benchmarks.get(metric)
        if not bench or pd.isna(value):
            return 60.0  # 默认分

        if higher_is_better:
            if value >= bench["high"]:
                return 95.0
            elif value >= bench["medium"]:
                return 75.0 + (value - bench["medium"]) / (bench["high"] - bench["medium"]) * 20
            elif value >= bench["low"]:
                return 50.0 + (value - bench["low"]) / (bench["medium"] - bench["low"]) * 25
            else:
                return 30.0 + (value / bench["low"]) * 20
        else:
            if value <= bench["low"]:
                return 95.0
            elif value <= bench["medium"]:
                return 75.0 - (value - bench["low"]) / (bench["medium"] - bench["low"]) * 20
            elif value <= bench["high"]:
                return 50.0 - (value - bench["medium"]) / (bench["high"] - bench["medium"]) * 25
            else:
                return max(10.0, 30.0 - ((value - bench["high"]) / bench["high"]) * 30)

    # ------------------------------------------------------------------
    # 结构化接口（原 V3）
    # ------------------------------------------------------------------
    def analyze(self, region: str) -> EnterpriseAnalysis:
        """分析指定城市，返回结构化结果。"""
        city_data = get_city_data(region)
        if not city_data:
            raise ValueError(f"No data available for region: {region}")

        cost_score, cost_details = self._calculate_business_cost(city_data)
        supply_score, supply_details = self._calculate_supply_chain(city_data)
        policy_score, policy_details = self._calculate_policy_benefit(city_data)

        total_score = (
            cost_score * self.weights["business_cost"]
            + supply_score * self.weights["supply_chain"]
            + policy_score * self.weights["policy_benefit"]
        )

        suggestions = self._generate_suggestions(cost_score, supply_score, policy_score, city_data)
        data_source = self.data_source_info.get(region, {})

        logger.info(f"Analysis complete for {region}: total_score={total_score:.1f}")

        return EnterpriseAnalysis(
            region=region,
            year=city_data.get("year", 2025),
            business_cost_score=cost_score,
            supply_chain_score=supply_score,
            policy_benefit_score=policy_score,
            total_score=total_score,
            cost_details=cost_details,
            supply_details=supply_details,
            policy_details=policy_details,
            suggestions=suggestions,
            data_source=data_source,
        )

    def compare_multiple_cities(self, cities: list[str]) -> pd.DataFrame:
        """对比多个城市，返回按综合得分排序的 DataFrame。"""
        results = []
        for city in cities:
            try:
                analysis = self.analyze(city)
                results.append(
                    {
                        "城市": analysis.region,
                        "年份": analysis.year,
                        "营商成本": analysis.business_cost_score,
                        "供应链配套": analysis.supply_chain_score,
                        "政策红利": analysis.policy_benefit_score,
                        "综合得分": analysis.total_score,
                        "数据质量": self.data_source_info.get(city, {}).get("data_quality_score", 0),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to analyze {city}: {e}")

        df = pd.DataFrame(results)
        return df.sort_values("综合得分", ascending=False).reset_index(drop=True)

    def _calculate_business_cost(self, data: dict) -> tuple[float, dict[str, float]]:
        """计算营商成本维度得分（越低越好）。"""
        land_score = self._calculate_score(data["land_price"], "land_price", higher_is_better=False)
        salary_score = self._calculate_score(data["salary_level"], "salary_level", higher_is_better=False)
        energy_score = self._calculate_score(data["energy_cost"], "energy_cost", higher_is_better=False)
        financing_score = self._calculate_score(data["financing_cost"], "financing_cost", higher_is_better=False)

        total = land_score * 0.35 + salary_score * 0.40 + energy_score * 0.15 + financing_score * 0.10

        details = {
            "土地价格": data["land_price"],
            "平均工资": data["salary_level"],
            "能源成本": data["energy_cost"],
            "融资成本": data["financing_cost"],
            "土地价格得分": land_score,
            "平均工资得分": salary_score,
            "能源成本得分": energy_score,
            "融资成本得分": financing_score,
        }
        return total, details

    def _calculate_supply_chain(self, data: dict) -> tuple[float, dict[str, float]]:
        """计算供应链配套维度得分。"""
        support_score = self._calculate_score(data["local_support_rate"], "local_support_rate", higher_is_better=True)
        delivery_score = self._calculate_score(data["avg_delivery_time"], "avg_delivery_time", higher_is_better=False)
        location_score = self._calculate_score(data["location_quotient"], "location_quotient", higher_is_better=True)

        total = support_score * 0.45 + delivery_score * 0.25 + location_score * 0.30

        details = {
            "本地配套率": data["local_support_rate"],
            "平均交付周期": data["avg_delivery_time"],
            "区位熵": data["location_quotient"],
            "供应商数量": data.get("supplier_count", 0),
            "本地配套率得分": support_score,
            "交付周期得分": delivery_score,
            "产业集聚度得分": location_score,
        }
        return total, details

    def _calculate_policy_benefit(self, data: dict) -> tuple[float, dict[str, float]]:
        """计算政策红利维度得分。"""
        tax_red_score = self._calculate_score(data["tax_reduction"], "tax_reduction", higher_is_better=True)
        tax_cov_score = self._calculate_score(data["tax_coverage"], "tax_coverage", higher_is_better=True)
        rd_score = self._calculate_score(data["rd_subsidy"], "rd_subsidy", higher_is_better=True)
        approval_score = self._calculate_score(data["avg_approval_time"], "avg_approval_time", higher_is_better=False)

        total = tax_red_score * 0.30 + tax_cov_score * 0.20 + rd_score * 0.35 + approval_score * 0.15

        details = {
            "减税降费": data["tax_reduction"],
            "政策覆盖率": data["tax_coverage"],
            "研发补贴": data["rd_subsidy"],
            "平均审批时间": data["avg_approval_time"],
            "减税降费得分": tax_red_score,
            "政策覆盖率得分": tax_cov_score,
            "研发补贴得分": rd_score,
            "审批效率得分": approval_score,
        }
        return total, details

    def _generate_suggestions(
        self,
        cost_score: float,
        supply_score: float,
        policy_score: float,
        data: dict,
    ) -> list[str]:
        """生成针对性建议。"""
        suggestions = []

        if cost_score < 60:
            suggestions.append("[!] 营商成本偏高：建议考虑成本对冲策略，如与当地政府协商土地优惠政策")
        elif cost_score < 75:
            suggestions.append("[i] 营商成本中等：可探索供应链本地化降低综合成本")
        else:
            suggestions.append("[+] 营商成本具有竞争力")

        if supply_score < 60:
            suggestions.append("[!] 供应链配套不足：建议先建立区域供应商网络，评估分阶段投资策略")
        elif supply_score < 75:
            suggestions.append("[i] 供应链配套中等：可利用区位优势逐步完善产业生态")
        else:
            suggestions.append("[+] 供应链配套完善，产业集聚效应明显")

        if policy_score < 60:
            suggestions.append("[!] 政策支持力度一般：建议详细研究具体产业政策，主动申请专项补贴")
        elif policy_score < 75:
            suggestions.append("[i] 政策支持中等：可重点关注研发补贴和税收优惠政策")
        else:
            suggestions.append("[+] 政策红利显著，政府服务效率高")

        if data.get("industry_high_tech_ratio", 0) > 40:
            suggestions.append("[i] 该城市高新技术产业占比高，适合科技型企业布局")

        return suggestions

    # ------------------------------------------------------------------
    # 字典报告接口（兼容原 V1，供 API 路由 / Celery 任务 / 测试使用）
    # ------------------------------------------------------------------
    def analyze_business_costs(self, data: dict[str, Any]) -> dict[str, Any]:
        results: dict[str, Any] = {"total_cost_score": 0.0, "components": {}, "benchmarks": {}}

        if "land_price" in data:
            score = self._calculate_score(data["land_price"], "land_price", higher_is_better=False)
            results["components"]["land_cost"] = {
                "value": data["land_price"],
                "unit": "元/平方米·年",
                "weight": 0.30,
                "score": round(score, 2),
            }
            results["benchmarks"]["land_price"] = self.benchmarks.get("land_price", {})

        if "salary_level" in data:
            score = self._calculate_score(data["salary_level"], "salary_level", higher_is_better=False)
            results["components"]["labor_cost"] = {
                "value": data["salary_level"],
                "unit": "元/月",
                "weight": 0.40,
                "score": round(score, 2),
            }
            results["benchmarks"]["salary_level"] = self.benchmarks.get("salary_level", {})

        if "energy_cost" in data:
            score = self._calculate_score(data["energy_cost"], "energy_cost", higher_is_better=False)
            results["components"]["energy_cost"] = {
                "value": data["energy_cost"],
                "unit": "元/千瓦时",
                "weight": 0.20,
                "score": round(score, 2),
            }
            results["benchmarks"]["energy_cost"] = self.benchmarks.get("energy_cost", {})

        if "financing_cost" in data:
            score = self._calculate_score(data["financing_cost"], "financing_cost", higher_is_better=False)
            results["components"]["financing_cost"] = {
                "value": data["financing_cost"],
                "unit": "%",
                "weight": 0.10,
                "score": round(score, 2),
            }
            results["benchmarks"]["financing_cost"] = self.benchmarks.get("financing_cost", {})

        weighted_sum = 0.0
        weight_total = 0.0
        for comp in results["components"].values():
            w = comp["weight"]
            s = comp.get("score", 60.0)
            weighted_sum += s * w
            weight_total += w

        results["total_cost_score"] = round(weighted_sum / weight_total, 2) if weight_total > 0 else 0.0
        return results

    def analyze_supply_chain(self, data: dict[str, Any]) -> dict[str, Any]:
        results: dict[str, Any] = {
            "supply_chain_score": 0.0,
            "localization_rate": 0.0,
            "response_efficiency": {},
            "agglomeration_index": 0.0,
            "components": {},
            "benchmarks": {},
        }

        if "local_support_rate" in data:
            results["localization_rate"] = data["local_support_rate"]
            score = self._calculate_score(data["local_support_rate"], "local_support_rate", higher_is_better=True)
            results["components"]["localization"] = {
                "value": data["local_support_rate"],
                "unit": "%",
                "weight": 0.45,
                "score": round(score, 2),
            }
            results["benchmarks"]["local_support_rate"] = self.benchmarks.get("local_support_rate", {})

        if "avg_delivery_time" in data:
            results["response_efficiency"]["avg_delivery_time"] = data["avg_delivery_time"]
            score = self._calculate_score(data["avg_delivery_time"], "avg_delivery_time", higher_is_better=False)
            results["components"]["delivery"] = {
                "value": data["avg_delivery_time"],
                "unit": "天",
                "weight": 0.25,
                "score": round(score, 2),
            }
            results["benchmarks"]["avg_delivery_time"] = self.benchmarks.get("avg_delivery_time", {})

        if "location_quotient" in data:
            results["agglomeration_index"] = data["location_quotient"]
            score = self._calculate_score(data["location_quotient"], "location_quotient", higher_is_better=True)
            results["components"]["agglomeration"] = {
                "value": data["location_quotient"],
                "unit": "",
                "weight": 0.30,
                "score": round(score, 2),
            }
            results["benchmarks"]["location_quotient"] = self.benchmarks.get("location_quotient", {})

        weighted_sum = 0.0
        weight_total = 0.0
        for comp in results["components"].values():
            w = comp["weight"]
            s = comp.get("score", 60.0)
            weighted_sum += s * w
            weight_total += w

        results["supply_chain_score"] = round(weighted_sum / weight_total, 2) if weight_total > 0 else 0.0
        return results

    def analyze_policy_benefits(self, data: dict[str, Any]) -> dict[str, Any]:
        results: dict[str, Any] = {
            "policy_benefit_score": 0.0,
            "tax_incentives": {},
            "subsidies": {},
            "government_efficiency": {},
            "components": {},
            "benchmarks": {},
        }

        if "tax_reduction" in data:
            results["tax_incentives"]["actual_reduction"] = data["tax_reduction"]
            score = self._calculate_score(data["tax_reduction"], "tax_reduction", higher_is_better=True)
            results["components"]["tax_reduction"] = {
                "value": data["tax_reduction"],
                "unit": "亿元",
                "weight": 0.30,
                "score": round(score, 2),
            }
            results["benchmarks"]["tax_reduction"] = self.benchmarks.get("tax_reduction", {})

        if "tax_coverage" in data:
            results["tax_incentives"]["coverage_rate"] = data["tax_coverage"]
            score = self._calculate_score(data["tax_coverage"], "tax_coverage", higher_is_better=True)
            results["components"]["tax_coverage"] = {
                "value": data["tax_coverage"],
                "unit": "%",
                "weight": 0.20,
                "score": round(score, 2),
            }
            results["benchmarks"]["tax_coverage"] = self.benchmarks.get("tax_coverage", {})

        if "rd_subsidy" in data:
            results["subsidies"]["rd_subsidy"] = data["rd_subsidy"]
            score = self._calculate_score(data["rd_subsidy"], "rd_subsidy", higher_is_better=True)
            results["components"]["rd_subsidy"] = {
                "value": data["rd_subsidy"],
                "unit": "亿元",
                "weight": 0.35,
                "score": round(score, 2),
            }
            results["benchmarks"]["rd_subsidy"] = self.benchmarks.get("rd_subsidy", {})

        if "avg_approval_time" in data:
            results["government_efficiency"]["avg_approval_time"] = data["avg_approval_time"]
            score = self._calculate_score(data["avg_approval_time"], "avg_approval_time", higher_is_better=False)
            results["components"]["approval_efficiency"] = {
                "value": data["avg_approval_time"],
                "unit": "工作日",
                "weight": 0.15,
                "score": round(score, 2),
            }
            results["benchmarks"]["avg_approval_time"] = self.benchmarks.get("avg_approval_time", {})

        weighted_sum = 0.0
        weight_total = 0.0
        for comp in results["components"].values():
            w = comp["weight"]
            s = comp.get("score", 60.0)
            weighted_sum += s * w
            weight_total += w

        results["policy_benefit_score"] = round(weighted_sum / weight_total, 2) if weight_total > 0 else 0.0
        return results

    def analyze_city(self, city_name: str) -> dict[str, Any]:
        """按城市名分析，返回 dict 报告（兼容原 V1 接口）。"""
        city_data = get_city_data(city_name)
        if not city_data:
            raise ValueError(f"No data available for city: {city_name}")
        return self.generate_comprehensive_report(city_data)

    def compare_cities(self, city_names: list[str] | None = None) -> list[dict[str, Any]]:
        """对比多个城市，返回按综合得分排序的列表（兼容原 V1 接口）。"""
        if city_names is None:
            city_names = get_all_cities()

        results = []
        for city_name in city_names:
            try:
                report = self.analyze_city(city_name)
                results.append(
                    {
                        "city": city_name,
                        "business_cost_score": report["business_costs"]["total_cost_score"],
                        "supply_chain_score": report["supply_chain"]["supply_chain_score"],
                        "policy_benefit_score": report["policy_benefits"]["policy_benefit_score"],
                        "overall_score": report["overall_score"],
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to analyze {city_name}: {e}")

        return sorted(results, key=lambda x: x["overall_score"], reverse=True)

    def generate_comprehensive_report(self, data: dict[str, Any]) -> dict[str, Any]:
        """生成综合分析报告（dict 格式，兼容原 V1/V2 接口）。"""
        report: dict[str, Any] = {
            "region": data.get("region", data.get("name", "未知地区")),
            "industry": data.get("industry", "未知产业"),
            "year": data.get("year", 2025),
            "overall_score": 0.0,
            "business_costs": self.analyze_business_costs(data),
            "supply_chain": self.analyze_supply_chain(data),
            "policy_benefits": self.analyze_policy_benefits(data),
            "recommendations": [],
            "data_source": self.data_source_info.get(data.get("name", ""), {}),
        }

        cost_score = report["business_costs"]["total_cost_score"]
        supply_score = report["supply_chain"]["supply_chain_score"]
        policy_score = report["policy_benefits"]["policy_benefit_score"]

        w = self.weights
        report["overall_score"] = round(
            cost_score * w.get("business_cost", 0.35)
            + supply_score * w.get("supply_chain", 0.40)
            + policy_score * w.get("policy_benefit", 0.25),
            2,
        )

        if cost_score < 60:
            report["recommendations"].append("[!] 营商成本偏高：建议考虑成本对冲策略，如与当地政府协商土地优惠政策")
        elif cost_score < 75:
            report["recommendations"].append("[i] 营商成本中等：可探索供应链本地化降低综合成本")
        else:
            report["recommendations"].append("[+] 营商成本具有竞争力")

        if supply_score < 60:
            report["recommendations"].append("[!] 供应链配套不足：建议先建立区域供应商网络，评估分阶段投资策略")
        elif supply_score < 75:
            report["recommendations"].append("[i] 供应链配套中等：可利用区位优势逐步完善产业生态")
        else:
            report["recommendations"].append("[+] 供应链配套完善，产业集聚效应明显")

        if policy_score < 60:
            report["recommendations"].append("[!] 政策支持力度一般：建议详细研究具体产业政策，主动申请专项补贴")
        elif policy_score < 75:
            report["recommendations"].append("[i] 政策支持中等：可重点关注研发补贴和税收优惠政策")
        else:
            report["recommendations"].append("[+] 政策红利显著，政府服务效率高")

        return report

    def run_full_analysis(
        self, data, save_results: bool = True, output_dir: str = "data/enterprise_analysis", **kwargs
    ) -> dict[str, Any]:
        """兼容入口：接受城市名或数据字典。"""
        if isinstance(data, str):
            return self.analyze_city(data)
        elif isinstance(data, dict):
            return self.generate_comprehensive_report(data)
        else:
            raise ValueError("data must be city name (str) or city data (dict)")

    def predict(self, data) -> dict[str, Any]:
        """BaseAnalyzer.predict 兼容实现。"""
        return self.run_full_analysis(data)


# 模块级单例（替代原 V2 的 enterprise_analyzer_v2 单例）
enterprise_analyzer = EnterpriseAnalyzer()

# 向后兼容别名（供历史代码逐步迁移）
EnterpriseAnalyzerV3 = EnterpriseAnalyzer


def run_semiconductor_fab_location_analysis() -> dict[str, Any]:
    """
    企业选址案例分析：半导体制造企业选址
    业务背景：某大型半导体制造企业计划在中国新建12英寸晶圆厂
    候选城市：深圳、上海、成都
    分析维度：营商成本、供应链配套、政策红利
    """
    logger.info("Running semiconductor fab location analysis...")

    analyzer = EnterpriseAnalyzer()
    candidate_cities = ["深圳", "上海", "成都"]

    # 1. 逐个城市分析
    city_analyses = {}
    for city in candidate_cities:
        try:
            analysis = analyzer.analyze(city)
            city_analyses[city] = analysis
            logger.info(f"  {city}: total_score={analysis.total_score:.1f}")
        except Exception as e:
            logger.error(f"  {city} 分析失败: {e}")

    # 2. 多城市对比
    comparison_df = analyzer.compare_multiple_cities(candidate_cities)

    # 3. 生成选址建议
    recommendation = _generate_fab_location_recommendation(city_analyses, comparison_df)

    # 4. 数据质量报告
    quality_report = generate_data_quality_report()

    return {
        "case_title": "半导体制造企业选址分析",
        "candidate_cities": candidate_cities,
        "city_analyses": {city: _analysis_to_dict(a) for city, a in city_analyses.items()},
        "comparison_table": comparison_df.to_dict(orient="records"),
        "recommendation": recommendation,
        "data_quality": quality_report,
        "analysis_timestamp": pd.Timestamp.now().isoformat(),
    }


def _analysis_to_dict(a: EnterpriseAnalysis) -> dict[str, Any]:
    """将 EnterpriseAnalysis dataclass 转为可序列化 dict。"""
    return {
        "region": a.region,
        "year": a.year,
        "business_cost_score": round(a.business_cost_score, 2),
        "supply_chain_score": round(a.supply_chain_score, 2),
        "policy_benefit_score": round(a.policy_benefit_score, 2),
        "total_score": round(a.total_score, 2),
        "cost_details": a.cost_details,
        "supply_details": a.supply_details,
        "policy_details": a.policy_details,
        "suggestions": a.suggestions,
        "data_source": a.data_source,
    }


def _generate_fab_location_recommendation(
    city_analyses: dict[str, EnterpriseAnalysis],
    comparison_df: pd.DataFrame,
) -> dict[str, Any]:
    """基于分析结果生成选址建议。"""
    if comparison_df.empty:
        return {"recommended_city": None, "reason": "无可用分析数据"}

    best_city = comparison_df.iloc[0]["城市"]
    best_analysis = city_analyses.get(best_city)

    reasons = []
    if best_analysis:
        if best_analysis.business_cost_score >= 75:
            reasons.append(f"营商成本具有竞争力（{best_analysis.business_cost_score:.1f}分）")
        if best_analysis.supply_chain_score >= 75:
            reasons.append(f"供应链配套完善（{best_analysis.supply_chain_score:.1f}分）")
        if best_analysis.policy_benefit_score >= 75:
            reasons.append(f"政策红利显著（{best_analysis.policy_benefit_score:.1f}分）")
        reasons.extend(best_analysis.suggestions[:2])

    return {
        "recommended_city": best_city,
        "total_score": float(comparison_df.iloc[0]["综合得分"]),
        "reasons": reasons,
        "ranking": comparison_df[["城市", "综合得分"]].to_dict(orient="records"),
    }
