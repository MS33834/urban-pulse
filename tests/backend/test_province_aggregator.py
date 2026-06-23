"""Tests for backend.core.province_aggregator."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from backend.core import province_aggregator as pa


class TestIndicatorAggregation:
    def test_aggregate_indicator_known(self):
        assert pa.aggregate_indicator("gdp") == "sum"
        assert pa.aggregate_indicator("rd_intensity") == "weighted_avg"

    def test_aggregate_indicator_unknown(self):
        assert pa.aggregate_indicator("foo") == "avg"

    def test_cagr(self):
        assert pa._cagr(100, 121, 2) == pytest.approx(10.0)
        assert math.isnan(pa._cagr(0, 100, 1))
        assert math.isnan(pa._cagr(100, 100, 0))


class TestForecastHelpers:
    def test_linear_regression_forecast(self):
        result = pa._linear_regression_forecast([1.0, 2.0, 3.0, 4.0, 5.0], 3)
        assert len(result["predictions"]) == 3
        assert "lower_95" in result
        assert "metrics" in result
        assert result["method"].startswith("Linear Regression")

    def test_linear_regression_forecast_insufficient(self):
        result = pa._linear_regression_forecast([1.0, 2.0], 3)
        assert result["method"] == "Insufficient data (<3 points)"
        assert result["predictions"] == [2.0, 2.0, 2.0]

    def test_forecast_series_insufficient(self):
        result = pa.forecast_series([], 3, 2024)
        assert result["method"] == "Insufficient data"
        assert result["predictions"] == [0.0, 0.0, 0.0]

    def test_forecast_series_linear(self):
        result = pa.forecast_series([1.0, 2.0, 3.0, 4.0, 5.0], 2, 2024)
        assert len(result["predictions"]) == 2
        assert result["years"] == [2025, 2026]
        assert result["method"].startswith("Linear Regression")


class TestProvinceTimeseries:
    @pytest.fixture
    def sample_historical(self):
        return {
            "深圳": pd.DataFrame(
                {
                    "year": [2021, 2022, 2023],
                    "gdp": [100.0, 110.0, 120.0],
                    "population": [1000, 1010, 1020],
                    "rd_intensity": [3.0, 3.2, 3.5],
                }
            ),
            "广州": pd.DataFrame(
                {
                    "year": [2021, 2022, 2023],
                    "gdp": [90.0, 95.0, 100.0],
                    "population": [900, 905, 910],
                    "rd_intensity": [2.5, 2.6, 2.7],
                }
            ),
        }

    def test_get_province_timeseries_sum(self, monkeypatch, sample_historical):
        monkeypatch.setattr(pa, "get_province_index", lambda: {"广东": ["深圳", "广州"]})
        monkeypatch.setattr(pa, "get_historical_data", lambda city: sample_historical.get(city, pd.DataFrame()))
        df = pa.get_province_timeseries("广东", "gdp")
        assert len(df) == 3
        assert df["value"].iloc[-1] == pytest.approx(220.0)

    def test_get_province_timeseries_weighted(self, monkeypatch, sample_historical):
        monkeypatch.setattr(pa, "get_province_index", lambda: {"广东": ["深圳", "广州"]})
        monkeypatch.setattr(pa, "get_historical_data", lambda city: sample_historical.get(city, pd.DataFrame()))
        df = pa.get_province_timeseries("广东", "rd_intensity")
        assert len(df) == 3
        assert df["value"].iloc[-1] > 2.7

    def test_get_province_timeseries_empty(self, monkeypatch):
        monkeypatch.setattr(pa, "get_province_index", lambda: {"广东": []})
        df = pa.get_province_timeseries("广东", "gdp")
        assert df.empty


class TestForecastCityIndicator:
    def test_forecast_city_indicator_success(self, monkeypatch):
        hist = pd.DataFrame(
            {
                "year": [2020, 2021, 2022, 2023, 2024],
                "gdp": [80.0, 90.0, 100.0, 110.0, 120.0],
            }
        )
        monkeypatch.setattr(pa, "get_all_forecast_cities", lambda: ["深圳"])
        monkeypatch.setattr(pa, "get_historical_data", lambda city: hist)
        result = pa.forecast_city_indicator("深圳", "gdp", years=3)
        assert result["scope"] == "city"
        assert len(result["forecast_values"]) == 3

    def test_forecast_city_indicator_not_found(self, monkeypatch):
        monkeypatch.setattr(pa, "get_all_forecast_cities", lambda: ["深圳"])
        result = pa.forecast_city_indicator("上海", "gdp")
        assert "error" in result

    def test_forecast_city_indicator_no_data(self, monkeypatch):
        monkeypatch.setattr(pa, "get_all_forecast_cities", lambda: ["深圳"])
        monkeypatch.setattr(pa, "get_historical_data", lambda city: pd.DataFrame())
        result = pa.forecast_city_indicator("深圳", "gdp")
        assert "error" in result


class TestForecastProvinceIndicator:
    def test_forecast_province_indicator_success(self, monkeypatch):
        hist = pd.DataFrame(
            {
                "year": [2020, 2021, 2022, 2023, 2024],
                "value": [100.0, 110.0, 120.0, 130.0, 140.0],
                "cities": [["深圳"]] * 5,
            }
        )
        monkeypatch.setattr(pa, "get_province_index", lambda: {"广东": ["深圳"]})
        monkeypatch.setattr(pa, "get_province_timeseries", lambda p, i: hist)
        result = pa.forecast_province_indicator("广东", "gdp", years=2)
        assert result["scope"] == "province"
        assert len(result["forecast_values"]) == 2

    def test_forecast_province_indicator_not_found(self, monkeypatch):
        monkeypatch.setattr(pa, "get_province_index", lambda: {"广东": ["深圳"]})
        result = pa.forecast_province_indicator("浙江", "gdp")
        assert "error" in result

    def test_forecast_all_provinces(self, monkeypatch):
        hist = pd.DataFrame(
            {
                "year": [2020, 2021, 2022, 2023, 2024],
                "value": [100.0, 110.0, 120.0, 130.0, 140.0],
                "cities": [["深圳"]] * 5,
            }
        )
        monkeypatch.setattr(pa, "get_province_index", lambda: {"广东": ["深圳"]})
        monkeypatch.setattr(pa, "get_province_timeseries", lambda p, i: hist)
        result = pa.forecast_all_provinces("gdp", years=2)
        assert "广东" in result["provinces"]
        assert len(result["comparison"]) == 1


class TestProvinceIndex:
    def test_build_province_index_fallback(self, monkeypatch):
        monkeypatch.setattr("backend.regions.get_registry", lambda: (_ for _ in ()).throw(RuntimeError("no registry")))
        monkeypatch.setattr("backend.data.city_data.HISTORICAL_DATA", {"深圳": [], "广州": []})
        index = pa._build_province_index()
        assert "深圳" in index
        assert "广州" in index
