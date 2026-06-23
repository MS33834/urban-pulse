"""Tests for backend.analytics.competitiveness modules."""

from __future__ import annotations

import pandas as pd
import pytest

from backend.analytics.competitiveness import (
    CompetitivenessRanker,
    IndicatorFramework,
    entropy_weight,
    get_weights,
    minmax_normalize,
)


class TestIndicatorFramework:
    def test_get_all_indicators(self):
        indicators = IndicatorFramework.get_all_indicators()
        assert "gdp" in indicators
        assert "rd_intensity" in indicators
        assert indicators["gdp"]["direction"] == "positive"

    def test_get_covered_indicators(self):
        covered = IndicatorFramework.get_covered_indicators()
        assert "gdp" in covered
        assert set(covered.keys()).issubset(set(IndicatorFramework.COVERED_INDICATOR_KEYS))

    def test_get_dimension_mapping(self):
        dims = IndicatorFramework.get_dimension_mapping()
        names = {d["name"] for d in dims}
        assert "资本力" in names
        assert "制度力" in names

    def test_get_direction(self):
        assert IndicatorFramework.get_direction("gdp") == "positive"
        assert IndicatorFramework.get_direction("energy_cost") == "negative"
        assert IndicatorFramework.get_direction("land_price") == "bidirectional"
        assert IndicatorFramework.get_direction("unknown") == "positive"

    def test_missing_and_data_dimensions(self):
        missing = {d["name"] for d in IndicatorFramework.get_missing_dimensions()}
        data = {d["name"] for d in IndicatorFramework.get_data_dimensions()}
        assert "结构力" in missing
        assert "资本力" in data
        assert missing & data == set()


class TestNormalizer:
    def test_empty_data_raises(self):
        with pytest.raises(ValueError):
            minmax_normalize({})

    def test_all_empty_indicators_raises(self):
        with pytest.raises(ValueError):
            minmax_normalize({"A": {"x": None}, "B": {"x": None}})

    def test_positive_negative_bidirectional(self):
        data = {
            "A": {"gdp": 100, "energy_cost": 10, "land_price": 50},
            "B": {"gdp": 200, "energy_cost": 5, "land_price": 100},
            "C": {"gdp": 150, "energy_cost": 8, "land_price": 75},
        }
        out = minmax_normalize(data)
        # positive: higher is better
        assert out["B"]["gdp"] == pytest.approx(100.0)
        assert out["A"]["gdp"] == pytest.approx(0.0)
        # negative: lower is better
        assert out["B"]["energy_cost"] == pytest.approx(100.0)
        assert out["A"]["energy_cost"] == pytest.approx(0.0)
        # bidirectional: closer to median is better
        assert out["C"]["land_price"] == pytest.approx(100.0)

    def test_missing_value_gets_middle_score(self):
        data = {
            "A": {"gdp": 100},
            "B": {"gdp": 200},
            "C": {"gdp": None},
        }
        out = minmax_normalize(data)
        assert out["C"]["gdp"] == pytest.approx(50.0)

    def test_zero_range_gets_middle_score(self):
        data = {
            "A": {"gdp": 100},
            "B": {"gdp": 100},
        }
        out = minmax_normalize(data)
        assert out["A"]["gdp"] == pytest.approx(50.0)
        assert out["B"]["gdp"] == pytest.approx(50.0)

    def test_non_finite_ignored(self):
        data = {
            "A": {"gdp": 100},
            "B": {"gdp": float("inf")},
        }
        out = minmax_normalize(data)
        assert "gdp" in out["A"]
        assert out["A"]["gdp"] == pytest.approx(50.0)


class TestWeighting:
    def test_entropy_weight_empty_raises(self):
        with pytest.raises(ValueError):
            entropy_weight(pd.DataFrame())

    def test_entropy_weight_single_sample(self):
        df = pd.DataFrame({"x": [1.0], "y": [2.0]})
        w = entropy_weight(df)
        assert len(w) == 2
        assert w.sum() == pytest.approx(1.0)
        assert w["x"] == pytest.approx(0.5)

    def test_entropy_weight_uniform_returns_equal(self):
        df = pd.DataFrame({"x": [1.0, 1.0, 1.0], "y": [2.0, 2.0, 2.0]})
        w = entropy_weight(df)
        assert w["x"] == pytest.approx(0.5)
        assert w["y"] == pytest.approx(0.5)

    def test_entropy_weight_with_variation(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [1.0, 1.01, 1.02, 1.03]})
        w = entropy_weight(df)
        assert w["x"] > w["y"]
        assert w.sum() == pytest.approx(1.0)

    def test_get_weights_default(self):
        w = get_weights(method="default", framework=IndicatorFramework)
        assert "gdp" in w
        covered = IndicatorFramework.get_covered_indicators()
        # 默认等权 = 1/19, 但只有 covered 指标被返回
        assert sum(w.values()) == pytest.approx(len(covered) / 19, abs=1e-6)

    def test_get_weights_entropy(self):
        df = pd.DataFrame({"gdp": [0.5, 0.6, 0.7], "rd_intensity": [0.2, 0.3, 0.25]})
        w = get_weights(method="entropy", data_matrix=df, framework=IndicatorFramework)
        assert set(w.keys()).issubset(set(IndicatorFramework.get_covered_indicators().keys()))
        assert sum(w.values()) == pytest.approx(1.0)

    def test_get_weights_unknown_fallback(self):
        w = get_weights(method="nonsense", framework=IndicatorFramework)
        assert "gdp" in w


class TestCompetitivenessRanker:
    @staticmethod
    def _sample_provider() -> dict[str, dict[str, float]]:
        return {
            "深圳": {
                "gdp": 35000,
                "fiscal_revenue": 5000,
                "gdp_growth": 6.0,
                "rd_intensity": 5.0,
                "industry_high_tech_ratio": 60.0,
                "rd_subsidy": 15.0,
                "population": 1800,
                "supplier_count": 5000,
                "land_price": 5500,
                "salary_level": 12000,
                "energy_cost": 0.8,
                "local_support_rate": 85.0,
                "policy_coverage": 90.0,
                "tax_coverage": 80.0,
                "avg_approval_time": 5.0,
                "tax_reduction": 30.0,
            },
            "上海": {
                "gdp": 48000,
                "fiscal_revenue": 7000,
                "gdp_growth": 5.0,
                "rd_intensity": 4.5,
                "industry_high_tech_ratio": 55.0,
                "rd_subsidy": 12.0,
                "population": 2500,
                "supplier_count": 6000,
                "land_price": 6500,
                "salary_level": 13000,
                "energy_cost": 0.9,
                "local_support_rate": 82.0,
                "policy_coverage": 88.0,
                "tax_coverage": 78.0,
                "avg_approval_time": 6.0,
                "tax_reduction": 25.0,
            },
            "北京": {
                "gdp": 45000,
                "fiscal_revenue": 6000,
                "gdp_growth": 5.2,
                "rd_intensity": 6.0,
                "industry_high_tech_ratio": 62.0,
                "rd_subsidy": 18.0,
                "population": 2200,
                "supplier_count": 4500,
                "land_price": 7000,
                "salary_level": 13500,
                "energy_cost": 0.85,
                "local_support_rate": 80.0,
                "policy_coverage": 87.0,
                "tax_coverage": 75.0,
                "avg_approval_time": 5.5,
                "tax_reduction": 22.0,
            },
        }

    def test_compute_index_default(self):
        ranker = CompetitivenessRanker(data_provider=self._sample_provider)
        result = ranker.compute_index()
        assert "overall" in result
        assert "rankings" in result
        assert "dimensions" in result
        assert "missing_dimensions" in result
        assert len(result["overall"]) == 3

    def test_compute_index_subset_cities(self):
        ranker = CompetitivenessRanker(data_provider=self._sample_provider)
        result = ranker.compute_index(city_names=["深圳", "上海"])
        assert set(result["overall"].keys()) == {"深圳", "上海"}

    def test_compute_index_empty_provider(self):
        ranker = CompetitivenessRanker(data_provider=lambda: {})
        result = ranker.compute_index()
        assert "error" in result
        assert result["overall"] == {}

    def test_compute_index_default_weights_method(self):
        ranker = CompetitivenessRanker(data_provider=self._sample_provider)
        result = ranker.compute_index(method="default")
        assert result["methodology"].startswith("默认权重")

    def test_generate_report_existing_city(self):
        ranker = CompetitivenessRanker(data_provider=self._sample_provider)
        report = ranker.generate_report("深圳")
        assert report["city_name"] == "深圳"
        assert report["overall_rank"] > 0
        assert "dimensions" in report
        assert "advantages" in report
        assert "disadvantages" in report

    def test_generate_report_missing_city(self):
        ranker = CompetitivenessRanker(data_provider=self._sample_provider)
        report = ranker.generate_report("不存在")
        assert "error" in report
