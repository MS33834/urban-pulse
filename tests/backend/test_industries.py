"""产业预测模块测试"""

from __future__ import annotations

import pytest

from backend.industries import (
    FactorImpact,
    Industry,
    IndustryLevel,
    IndustryRegistry,
    compute_factor_adjustment,
    forecast_industry,
    get_industry_registry,
)


class TestIndustryModel:
    def test_industry_creation(self):
        i = Industry(
            code="semiconductor",
            name="半导体",
            region_code="CN-GD-SZ",
            level=IndustryLevel.SECONDARY,
        )
        assert i.code == "semiconductor"
        assert i.name == "半导体"
        assert i.has_time_series is False
        assert i.latest_year is None

    def test_factor_impact_clamping(self):
        f = FactorImpact(name="政策支持", score=2.0, weight=1.5)
        assert f.score == 1.0
        assert f.weight == 1.0

    def test_time_series(self):
        i = Industry(
            code="semiconductor",
            name="半导体",
            region_code="CN-GD-SZ",
            historical_data=[
                {"year": 2020, "output_value": 100.0},
                {"year": 2021, "output_value": 120.0},
                {"year": 2022, "output_value": 140.0},
            ],
        )
        assert i.has_time_series is True
        assert i.get_time_series("output_value") == [100.0, 120.0, 140.0]
        assert i.latest_year == 2022


class TestFactorAdjustment:
    def test_no_factors(self):
        assert compute_factor_adjustment([]) == 0.0

    def test_weighted_adjustment(self):
        factors = [
            FactorImpact("政策支持", score=0.6, weight=0.5),
            FactorImpact("供应链风险", score=-0.2, weight=0.5),
        ]
        # (0.6*0.5 - 0.2*0.5) / 1.0 = 0.2 -> clamped to 0.15
        # 改用较小数值，确保不被裁剪
        factors = [
            FactorImpact("政策支持", score=0.4, weight=0.5),
            FactorImpact("供应链风险", score=-0.2, weight=0.5),
        ]
        # (0.4*0.5 - 0.2*0.5) / 1.0 = 0.1
        assert compute_factor_adjustment(factors) == pytest.approx(0.1)

    def test_clamping(self):
        factors = [FactorImpact("强刺激", score=1.0, weight=1.0)]
        assert compute_factor_adjustment(factors) == pytest.approx(0.15)


class TestIndustryForecaster:
    def test_forecast_with_factors(self):
        industry = Industry(
            code="semiconductor",
            name="半导体",
            region_code="CN-GD-SZ",
            historical_data=[
                {"year": 2020, "output_value": 100.0},
                {"year": 2021, "output_value": 120.0},
                {"year": 2022, "output_value": 140.0},
                {"year": 2023, "output_value": 170.0},
            ],
            factors=[
                FactorImpact("政策支持", score=0.6, weight=0.3),
                FactorImpact("市场需求", score=0.4, weight=0.3),
            ],
        )
        result = forecast_industry(industry, indicator="output_value", forecast_years=3)
        assert "error" not in result
        assert len(result["forecast_values"]) == 3
        assert result["factor_adjustment_pct"] > 0
        assert result["adjusted_cagr_pct"] > result["baseline_cagr_pct"]

    def test_forecast_without_factors(self):
        industry = Industry(
            code="semiconductor",
            name="半导体",
            region_code="CN-GD-SZ",
            historical_data=[
                {"year": 2020, "output_value": 100.0},
                {"year": 2021, "output_value": 110.0},
                {"year": 2022, "output_value": 120.0},
                {"year": 2023, "output_value": 130.0},
            ],
        )
        result = forecast_industry(industry, indicator="output_value", forecast_years=2, use_factors=False)
        assert "error" not in result
        assert result["factor_adjustment_pct"] == 0.0
        assert result["baseline_cagr_pct"] == pytest.approx(result["adjusted_cagr_pct"])

    def test_insufficient_data(self):
        industry = Industry(
            code="semiconductor",
            name="半导体",
            region_code="CN-GD-SZ",
            historical_data=[
                {"year": 2022, "output_value": 100.0},
                {"year": 2023, "output_value": 110.0},
            ],
        )
        result = forecast_industry(industry, indicator="output_value", forecast_years=3)
        assert "error" in result


class TestIndustryRegistry:
    def test_register_and_get(self):
        registry = IndustryRegistry()
        i = Industry(code="semiconductor", name="半导体", region_code="CN-GD-SZ")
        assert registry.register(i) is True
        assert registry.get("CN-GD-SZ", "semiconductor") == i
        assert registry.register(i) is False

    def test_singleton(self):
        r1 = get_industry_registry()
        r2 = get_industry_registry()
        assert r1 is r2


class TestIndustryAPI:
    def test_create_and_forecast(self, api_client):
        # 依赖 CN-GD-SZ 区域已存在
        payload = {
            "code": "new_energy",
            "name": "新能源",
            "region_code": "CN-GD-SZ",
            "level": "secondary",
            "category": "制造业",
            "historical_data": [
                {"year": 2020, "output_value": 200.0},
                {"year": 2021, "output_value": 260.0},
                {"year": 2022, "output_value": 330.0},
                {"year": 2023, "output_value": 420.0},
            ],
            "factors": [
                {"name": "政策支持", "score": 0.7, "weight": 0.3},
                {"name": "市场需求", "score": 0.5, "weight": 0.3},
                {"name": "供应链风险", "score": -0.2, "weight": 0.2},
            ],
        }
        response = api_client.post("/api/v1/industries", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["industry"]["name"] == "新能源"

        response = api_client.get("/api/v1/industries/CN-GD-SZ/new_energy")
        assert response.status_code == 200

        response = api_client.post(
            "/api/v1/industries/CN-GD-SZ/new_energy/forecast",
            json={"indicator": "output_value", "forecast_years": 3, "use_factors": True},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert len(result["forecast_values"]) == 3
        assert result["factor_adjustment_pct"] > 0
