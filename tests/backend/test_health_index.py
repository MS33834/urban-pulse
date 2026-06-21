"""
城市经济发展健康水平指数（CEHI）计算引擎测试。

覆盖：
- CEHIConfig 能正确加载 YAML 配置
- 维度数量、指标数量、健康等级数量正确
- CEHIEngine.calculate 对示例数据返回合理结果
- 健康等级判定正确
- 数据缺失时计算不报错且缺失指标得分为 0
- CEHIEngine.benchmark 能正确返回对标结果
"""

from __future__ import annotations

import pytest

from backend.core.health_index import CEHIConfig, CEHIEngine, CEHIResult


@pytest.fixture
def config() -> CEHIConfig:
    """加载默认 CEHI 配置。"""
    return CEHIConfig()


@pytest.fixture
def engine(config: CEHIConfig) -> CEHIEngine:
    """使用默认配置的 CEHI 计算引擎。"""
    return CEHIEngine(config)


@pytest.fixture
def sample_indicator_values() -> dict[str, float]:
    """示例城市完整指标数据（来自 health_index_demo）。"""
    return {
        # 经济活力
        "gdp_growth": 5.8,
        "gdp_per_capita": 128000,
        "tertiary_industry_ratio": 58.0,
        "retail_sales_growth": 6.2,
        "fixed_asset_investment_growth": 3.5,
        # 产业结构
        "high_tech_industry_ratio": 42.0,
        "strategic_emerging_ratio": 16.0,
        "enterprise_density": 650,
        "listed_companies": 68,
        "industrial_concentration": 48.0,
        # 财政健康
        "fiscal_revenue_growth": 4.5,
        "fiscal_self_sufficiency": 55.0,
        "debt_ratio": 185.0,
        "tax_revenue_ratio": 72.0,
        "fund_revenue_growth": -2.0,
        # 民生福祉
        "disposable_income": 58000,
        "urbanization_rate": 72.0,
        "registered_unemployment_rate": 3.8,
        "education_expenditure_ratio": 11.0,
        "medical_expenditure_ratio": 8.0,
        # 创新驱动
        "rd_intensity": 2.8,
        "patents_per_10000": 22,
        "high_tech_enterprises": 1800,
        "university_count": 35,
        "talent_inflow_rate": 1.2,
        # 开放水平
        "import_export_growth": 4.0,
        "fdi_growth": 3.5,
        "foreign_trade_dependency": 28.0,
        "free_trade_zone": 2,
        "international_routes": 18,
    }


def _indicator_values_at_level(config: CEHIConfig, level_score: int) -> dict[str, float]:
    """构造使每个指标都落在指定分段边界的输入值。

    level_score 取 80/60/40/0，分别对应健康/亚健康/预警/风险边界。
    """
    values: dict[str, float] = {}
    for indicator in config.indicators:
        h = indicator.healthy_threshold
        s = indicator.subhealthy_threshold
        w = indicator.warning_threshold
        if indicator.direction == "positive":
            if level_score == 80:
                values[indicator.id] = h
            elif level_score == 60:
                values[indicator.id] = s
            elif level_score == 40:
                values[indicator.id] = w
            else:  # 0
                values[indicator.id] = w * 0.5
        else:
            if level_score == 80:
                values[indicator.id] = h
            elif level_score == 60:
                values[indicator.id] = s
            elif level_score == 40:
                values[indicator.id] = w
            else:  # 0
                values[indicator.id] = w * 1.5
    return values


class TestCEHIConfig:
    """CEHI 配置加载测试。"""

    def test_config_loads_yaml(self, config: CEHIConfig):
        """CEHIConfig 能正确加载 YAML 配置。"""
        assert config.config_path.exists()
        assert config.index_name == "城市经济发展健康水平指数"
        assert config.index_short_name == "CEHI"
        assert len(config.dimensions) > 0
        assert len(config.indicators) > 0
        assert len(config.health_levels) > 0

    def test_dimension_count(self, config: CEHIConfig):
        """维度数量正确。"""
        assert len(config.dimensions) == 6
        dimension_ids = {d.id for d in config.dimensions}
        expected = {
            "economic_vitality",
            "industrial_structure",
            "fiscal_health",
            "livelihood_welfare",
            "innovation_driver",
            "openness",
        }
        assert dimension_ids == expected

    def test_indicator_count(self, config: CEHIConfig):
        """指标数量正确。"""
        assert len(config.indicators) == 30
        for dimension in config.dimensions:
            assert len(dimension.indicators) == 5

    def test_health_level_count(self, config: CEHIConfig):
        """健康等级数量与定义正确。"""
        assert len(config.health_levels) == 4
        levels = {lvl.level: lvl for lvl in config.health_levels}
        assert "healthy" in levels
        assert "subhealthy" in levels
        assert "warning" in levels
        assert "risk" in levels
        assert levels["healthy"].min_score == 80
        assert levels["subhealthy"].min_score == 60
        assert levels["warning"].min_score == 40
        assert levels["risk"].min_score == 0

    def test_dimension_weights_sum_to_one(self, config: CEHIConfig):
        """维度权重之和为 1。"""
        total = sum(d.weight for d in config.dimensions)
        assert abs(total - 1.0) < 1e-9

    def test_indicators_normalized_within_dimension(self, config: CEHIConfig):
        """维度内指标权重已归一化。"""
        for dimension in config.dimensions:
            total = sum(i.weight for i in dimension.indicators)
            assert abs(total - 1.0) < 1e-9


class TestCEHIEngineCalculate:
    """CEHI 综合计算测试。"""

    def test_calculate_returns_result(self, engine: CEHIEngine, sample_indicator_values: dict[str, float]):
        """calculate 返回 CEHIResult。"""
        result = engine.calculate("测试市", 2024, sample_indicator_values)
        assert isinstance(result, CEHIResult)
        assert result.city_name == "测试市"
        assert result.year == 2024

    def test_total_score_in_range(self, engine: CEHIEngine, sample_indicator_values: dict[str, float]):
        """总分在 0-100 之间。"""
        result = engine.calculate("测试市", 2024, sample_indicator_values)
        assert 0 <= result.total_score <= 100

    def test_dimension_scores_in_range(self, engine: CEHIEngine, sample_indicator_values: dict[str, float]):
        """各维度得分在 0-100 之间。"""
        result = engine.calculate("测试市", 2024, sample_indicator_values)
        assert len(result.dimension_scores) == 6
        for ds in result.dimension_scores:
            assert 0 <= ds.score <= 100
            assert ds.dimension.id

    def test_health_level_healthy(self, engine: CEHIEngine, config: CEHIConfig):
        """>=80 判定为健康。"""
        values = _indicator_values_at_level(config, 80)
        result = engine.calculate("健康市", 2024, values)
        assert result.status == "healthy"
        assert result.status_name == "健康"
        assert result.total_score >= 80

    def test_health_level_subhealthy(self, engine: CEHIEngine, config: CEHIConfig):
        """>=60 判定为亚健康。"""
        values = _indicator_values_at_level(config, 60)
        result = engine.calculate("亚健康市", 2024, values)
        assert result.status == "subhealthy"
        assert result.status_name == "亚健康"
        assert 60 <= result.total_score < 80

    def test_health_level_warning(self, engine: CEHIEngine, config: CEHIConfig):
        """>=40 判定为预警。"""
        values = _indicator_values_at_level(config, 40)
        result = engine.calculate("预警市", 2024, values)
        assert result.status == "warning"
        assert result.status_name == "预警"
        assert 40 <= result.total_score < 60

    def test_health_level_risk(self, engine: CEHIEngine, config: CEHIConfig):
        """<40 判定为风险。"""
        values = _indicator_values_at_level(config, 0)
        result = engine.calculate("风险市", 2024, values)
        assert result.status == "risk"
        assert result.status_name == "风险"
        assert result.total_score < 40

    def test_calculate_with_missing_data(self, engine: CEHIEngine, sample_indicator_values: dict[str, float]):
        """部分数据缺失时计算不报错，缺失指标得分为 0。"""
        incomplete_values = dict(sample_indicator_values)
        missing_ids = ["gdp_growth", "debt_ratio", "rd_intensity"]
        for ind_id in missing_ids:
            incomplete_values[ind_id] = None

        result = engine.calculate("缺失数据市", 2024, incomplete_values)
        assert isinstance(result, CEHIResult)
        assert 0 <= result.total_score <= 100

        missing_scores = []
        for ds in result.dimension_scores:
            for ind_score in ds.indicator_scores:
                if ind_score.indicator.id in missing_ids:
                    missing_scores.append(ind_score)
                    assert ind_score.score == 0.0
                    assert ind_score.status == "missing"
                    assert ind_score.status_name == "数据缺失"
        assert len(missing_scores) == len(missing_ids)

    def test_calculate_with_empty_data(self, engine: CEHIEngine):
        """全部数据缺失时计算不报错，总分和各维度得分为 0。"""
        result = engine.calculate("空数据市", 2024, {})
        assert isinstance(result, CEHIResult)
        assert result.total_score == 0.0
        assert result.status == "risk"
        for ds in result.dimension_scores:
            assert ds.score == 0.0

    def test_top_strengths_and_weaknesses_sorted(self, engine: CEHIEngine, sample_indicator_values: dict[str, float]):
        """强项按贡献度降序，短板按拖累程度升序排列。"""
        result = engine.calculate("测试市", 2024, sample_indicator_values)
        strengths = result.top_strengths
        weaknesses = result.top_weaknesses

        if len(strengths) > 1:
            assert all(strengths[i].contribution >= strengths[i + 1].contribution for i in range(len(strengths) - 1))
        if len(weaknesses) > 1:
            assert all(weaknesses[i].contribution <= weaknesses[i + 1].contribution for i in range(len(weaknesses) - 1))

    def test_recommendations_generated(self, engine: CEHIEngine, sample_indicator_values: dict[str, float]):
        """诊断建议已生成。"""
        result = engine.calculate("测试市", 2024, sample_indicator_values)
        assert isinstance(result.recommendations, list)
        assert len(result.recommendations) > 0


class TestCEHIEngineBenchmark:
    """CEHI 城市对标测试。"""

    def test_benchmark_returns_expected_structure(self, engine: CEHIEngine, sample_indicator_values: dict[str, float]):
        """benchmark 返回正确的对标结果结构。"""
        peers = {
            "对标市A": dict(sample_indicator_values),
            "对标市B": {k: v * 0.8 if isinstance(v, (int, float)) else v for k, v in sample_indicator_values.items()},
        }
        result = engine.benchmark("目标市", sample_indicator_values, peers, year=2024)

        assert isinstance(result, dict)
        assert result["target_city"] == "目标市"
        assert isinstance(result["target_score"], float)
        assert isinstance(result["target_status"], str)
        assert "rankings" in result
        assert "similar_cities" in result
        assert "best_practice" in result

    def test_benchmark_rankings_sorted_by_score(self, engine: CEHIEngine, config: CEHIConfig):
        """排名按总分降序排列。"""
        target_values = _indicator_values_at_level(config, 60)
        peer_a_values = _indicator_values_at_level(config, 80)
        peer_b_values = _indicator_values_at_level(config, 40)
        peers = {"对标A": peer_a_values, "对标B": peer_b_values}

        result = engine.benchmark("目标市", target_values, peers, year=2024)
        rankings = result["rankings"]
        assert len(rankings) == 3
        scores = [r["score"] for r in rankings]
        assert scores == sorted(scores, reverse=True)
        assert rankings[0]["city"] == "对标A"

    def test_benchmark_similar_cities_sorted_by_distance(self, engine: CEHIEngine, config: CEHIConfig):
        """相似城市按欧氏距离升序排列。"""
        target_values = _indicator_values_at_level(config, 60)
        peer_close = _indicator_values_at_level(config, 60)
        peer_far = _indicator_values_at_level(config, 40)
        peers = {"较近市": peer_close, "较远市": peer_far}

        result = engine.benchmark("目标市", target_values, peers, year=2024)
        similar = result["similar_cities"]
        assert len(similar) == 2
        distances = [c["distance"] for c in similar]
        assert distances == sorted(distances)
        assert similar[0]["city"] == "较近市"

    def test_benchmark_best_practice_with_gap(self, engine: CEHIEngine, config: CEHIConfig):
        """标杆分析返回与最优城市的差距维度。"""
        target_values = _indicator_values_at_level(config, 60)
        peer_values = _indicator_values_at_level(config, 80)
        peers = {"标杆市": peer_values}

        result = engine.benchmark("目标市", target_values, peers, year=2024)
        best_practice = result["best_practice"]
        assert best_practice["peer"] == "标杆市"
        assert best_practice["peer_score"] >= best_practice.get("target_score", 0)
        assert isinstance(best_practice["gap_dimensions"], list)

    def test_benchmark_best_practice_no_peers(self, engine: CEHIEngine, config: CEHIConfig):
        """没有对标城市时 best_practice 返回空结构。"""
        values = _indicator_values_at_level(config, 60)
        result = engine.benchmark("目标市", values, {}, year=2024)
        best_practice = result["best_practice"]
        assert best_practice["peer"] is None
        assert best_practice["gap_dimensions"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
