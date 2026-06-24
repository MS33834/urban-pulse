"""Extended tests for backend.core forecast / risk / province modules."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from backend.core import forecast_engine as fe
from backend.core import province_aggregator as pa
from backend.core import risk_engine as re


@pytest.fixture
def clear_pmdarima_module():
    """Remove fake pmdarima module after test if injected."""
    yield
    sys.modules.pop("pmdarima", None)


@pytest.fixture
def clear_statsforecast_module():
    """Remove fake statsforecast module after test if injected."""
    yield
    sys.modules.pop("statsforecast", None)
    sys.modules.pop("statsforecast.models", None)


@pytest.fixture
def clear_arch_module():
    """Remove fake arch module after test if injected."""
    yield
    sys.modules.pop("arch", None)


class TestRiskEngineExtended:
    def test_rolling_volatility_n_small(self):
        out = re.rolling_volatility([1.0, 2.0], window=3)
        assert out["volatility"] == 0.0
        assert out["reason"] == "n<3"

    def test_rolling_volatility_window_adjustment(self):
        # Three returns but window=5 → window shrinks to 3, and returns differ → vol>0.
        out = re.rolling_volatility([1.0, 2.0, 3.0, 6.0], window=5)
        assert out["window"] == 3
        assert out["volatility"] > 0

    def test_rolling_volatility_no_annualize(self):
        out = re.rolling_volatility([1.0, 2.0, 3.0, 4.0, 5.0], window=2, annualize=False)
        assert out["volatility"] == out["annualized_volatility"]

    def test_garch_volatility_arch_unavailable(self, monkeypatch):
        monkeypatch.setattr(re, "arch_available", lambda: False)
        out = re.garch_volatility([1.0] * 10)
        assert "failed" in out["method"].lower()
        assert out["conditional_vol_pct"] == 0.0

    def test_garch_volatility_insufficient_data(self, monkeypatch):
        monkeypatch.setattr(re, "arch_available", lambda: True)
        out = re.garch_volatility([1.0, 2.0, 3.0])
        assert "insufficient data" in out["method"].lower()

    def test_garch_volatility_fit_failure(self, monkeypatch, clear_arch_module):
        monkeypatch.setattr(re, "arch_available", lambda: True)

        fake_arch = MagicMock()
        fake_arch.arch_model.side_effect = RuntimeError("boom")
        sys.modules["arch"] = fake_arch

        out = re.garch_volatility(list(range(1, 20)))
        assert "failed" in out["method"].lower()

    def test_var_cvar_n_small(self):
        out = re.var_cvar([1.0, 2.0], confidence=0.95)
        assert out["var"] == 0.0
        assert out["reason"] == "n<3"

    def test_var_cvar_confidence_variations(self):
        y = [100, 105, 110, 95, 100, 115, 120, 90, 105]
        out95 = re.var_cvar(y, confidence=0.95)
        out99 = re.var_cvar(y, confidence=0.99)
        assert out95["confidence"] == 0.95
        assert out99["confidence"] == 0.99
        assert out95["var_pct"] > 0

    def test_scenario_analysis_empty_predictions(self):
        out = re.scenario_analysis([], starting_value=100.0)
        for s in out["scenarios"].values():
            assert s["final_value"] == 0.0
            assert s["max_drawdown_pct"] == 0.0

    def test_monte_carlo_n_small(self):
        out = re.monte_carlo_simulation([1.0, 2.0, 3.0, 4.0], years=3)
        assert "error" in out

    def test_monte_carlo_perfect_linear(self):
        # Perfect linear → residuals zero; function should not divide by zero.
        y = list(range(1, 12))
        out = re.monte_carlo_simulation(y, years=3, n_sims=50)
        assert out["n_sims"] == 50
        assert "quantiles" in out

    def test_risk_full_pipeline(self):
        values = list(range(100, 132, 2))
        baseline = [130.0, 135.0, 140.0]
        out = re.risk_full_pipeline(values, baseline, starting_value=100.0, n_sims=50)
        assert "volatility" in out
        assert "var_95" in out
        assert "scenarios" in out
        assert "monte_carlo" in out


class TestForecastEngineExtended:
    def test_auto_arima_n_small(self):
        out = fe.auto_arima([1.0, 2.0, 3.0])
        assert out["model"] is None
        assert out["reason"] == "n<5"

    def test_auto_arima_all_orders_fail(self):
        # Force every ARIMA fit to fail.
        with patch("statsmodels.tsa.arima.model.ARIMA", side_effect=RuntimeError("fail")):
            out = fe.auto_arima(list(range(10)), max_p=1, max_d=1, max_q=1)
        assert out["model"] is None
        assert out["reason"] == "all orders failed"

    def test_auto_arima_native_fallback_to_statsmodels(self, monkeypatch):
        monkeypatch.setattr(fe, "statsforecast_available", lambda: False)
        monkeypatch.setattr(fe, "pmdarima_available", lambda: False)
        out = fe.auto_arima_native(list(range(10)))
        assert out["backend"] == "statsmodels"
        assert out["model"] is not None

    def test_auto_arima_native_pmdarima_path(self, monkeypatch, clear_pmdarima_module):
        monkeypatch.setattr(fe, "statsforecast_available", lambda: False)
        monkeypatch.setattr(fe, "pmdarima_available", lambda: True)

        fake_model = MagicMock()
        fake_model.order = (1, 1, 1)
        fake_model.aic = lambda: 123.0
        fake_model.bic = lambda: 130.0

        fake_pm = MagicMock()
        fake_pm.auto_arima.return_value = fake_model
        sys.modules["pmdarima"] = fake_pm

        out = fe.auto_arima_native(list(range(10)))

        assert out["backend"] == "pmdarima"
        assert out["order"] == (1, 1, 1)

    def test_auto_arima_native_statsforecast_path(self, monkeypatch, clear_statsforecast_module):
        monkeypatch.setattr(fe, "statsforecast_available", lambda: True)

        fake_model = MagicMock()
        fake_model.fit.side_effect = lambda _y: setattr(
            fake_model, "model_", {"arma": (1, 0, 0, 0, 1, 0, 0), "aic": 100.0, "bic": 110.0}
        )

        fake_sf = MagicMock()
        fake_sf.models = [fake_model]

        fake_autoarima = MagicMock(return_value=fake_model)
        fake_models = MagicMock()
        fake_models.AutoARIMA = fake_autoarima
        sys.modules["statsforecast.models"] = fake_models

        fake_statsforecast = MagicMock()
        fake_statsforecast.StatsForecast = MagicMock(return_value=fake_sf)
        sys.modules["statsforecast"] = fake_statsforecast

        out = fe.auto_arima_native(list(range(10)))

        assert out["backend"] == "statsforecast"
        assert out["order"] == (1, 0, 0)

    def test_arima_forecast_model_none(self):
        out = fe.arima_forecast([], years=3)
        assert out["method"] == "ARIMA failed"
        assert out["predictions"] == [0.0, 0.0, 0.0]

    def test_arima_forecast_statsforecast_failure(self, monkeypatch, clear_statsforecast_module):
        # Provide a fake fit that claims statsforecast backend; predict path should fail gracefully.
        fake_sf = MagicMock()
        fake_sf.predict.side_effect = RuntimeError("boom")
        fit = {
            "model": fake_sf,
            "order": (1, 0, 0),
            "aic": 10.0,
            "bic": 12.0,
            "backend": "statsforecast",
        }
        monkeypatch.setattr(fe, "auto_arima_native", lambda _values, **kwargs: fit)

        out = fe.arima_forecast([1.0, 2.0, 3.0, 4.0, 5.0], years=2)
        assert "failed" in out["method"].lower()

    def test_arima_forecast_pmdarima_failure(self, monkeypatch):
        model = MagicMock()
        model.predict.side_effect = RuntimeError("boom")
        fit = {
            "model": model,
            "order": (1, 0, 0),
            "aic": 10.0,
            "bic": 12.0,
            "backend": "pmdarima",
        }
        monkeypatch.setattr(fe, "auto_arima_native", lambda _values, **kwargs: fit)
        out = fe.arima_forecast([1.0, 2.0, 3.0, 4.0, 5.0], years=2)
        assert "failed" in out["method"].lower()

    def test_ets_forecast_insufficient_data(self):
        out = fe.ets_forecast([1.0, 2.0, 3.0], years=3)
        assert "insufficient" in out["method"].lower()

    def test_ets_forecast_failure_fallback(self):
        with (
            patch("statsmodels.tsa.holtwinters.ExponentialSmoothing", side_effect=RuntimeError("boom")),
            patch("statsmodels.tsa.holtwinters.SimpleExpSmoothing", side_effect=RuntimeError("boom")),
        ):
            out = fe.ets_forecast(list(range(10)), years=2)
        assert "failed" in out["method"].lower()

    def test_linear_regression_forecast_insufficient(self):
        out = fe.linear_regression_forecast([1.0, 2.0], years=3)
        assert "insufficient" in out["method"].lower()

    def test_linear_regression_perfect_fit(self):
        y = list(range(10, 30))
        out = fe.linear_regression_forecast(y, years=3)
        # Perfect line → residuals zero; AIC should not crash.
        assert np.isfinite(out["aic"])
        assert len(out["predictions"]) == 3

    def test_linear_regression_negative_values(self):
        y = [-5, -3, -1, 1, 3, 5]
        out = fe.linear_regression_forecast(y, years=2)
        assert len(out["predictions"]) == 2

    def test_ensemble_forecast_with_none_aic(self):
        ar = {"predictions": [1.0, 2.0], "lower_ci": [0.0, 1.0], "upper_ci": [2.0, 3.0], "aic": float("inf")}
        et = {"predictions": [1.1, 2.1], "lower_ci": [0.1, 1.1], "upper_ci": [2.1, 3.1], "aic": None}
        lr = {"predictions": [1.2, 2.2], "lower_ci": [0.2, 1.2], "upper_ci": [2.2, 3.2], "aic": 10.0}
        out = fe.ensemble_forecast(ar, et, lr)
        assert abs(sum(out["weights"].values()) - 1.0) < 1e-6
        assert out["weights"]["lr"] == 1.0

    def test_run_diagnostics_insufficient(self):
        out = fe.run_diagnostics([1.0, 2.0, 3.0])
        assert out["verdict"] == "INSUFFICIENT_DATA"

    def test_run_diagnostics_arima_fit_failure(self):
        with patch("statsmodels.tsa.arima.model.ARIMA", side_effect=RuntimeError("boom")):
            out = fe.run_diagnostics(list(range(10)), order=(1, 1, 0))
        assert out["verdict"] == "DIAGNOSTIC_FAILED"

    def test_chow_test_invalid_breakpoints(self):
        y = list(range(10))
        assert "invalid breakpoint" in fe.chow_test(y, 0)["reason"]
        assert "invalid breakpoint" in fe.chow_test(y, len(y) - 1)["reason"]

    def test_chow_test_no_variance(self):
        # Perfect split with zero residuals → special-case return.
        y = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        out = fe.chow_test(y, 3)
        # No residual variance only if split parts are perfectly linear with zero RSS.
        assert out["pvalue"] is None or out["pvalue"] == 1.0

    def test_find_structural_breaks_none(self):
        y = list(range(20))
        breaks = fe.find_structural_breaks(y, min_segment=3)
        assert breaks == []

    def test_backtest_forecast_too_small(self):
        out = fe.backtest_forecast([1.0, 2.0, 3.0], n_test=3)
        assert "error" in out

    def test_backtest_forecast_no_successful_steps(self):
        def failing_model(_v, _h):
            raise RuntimeError("always fails")

        out = fe.backtest_forecast(list(range(10)), n_test=2, model_func=failing_model)
        assert "error" in out

    def test_backtest_forecast_custom_model(self):
        def flat_model(_v, h):
            return {"predictions": [5.0] * h, "lower_ci": [4.0] * h, "upper_ci": [6.0] * h}

        y = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        out = fe.backtest_forecast(y, n_test=2, model_func=flat_model)
        assert "error" not in out
        assert len(out["metrics"]) == 5

    def test_forecast_full_pipeline_insufficient(self):
        out = fe.forecast_full_pipeline([1.0, 2.0, 3.0], start_year=2020, years=3)
        assert "error" in out

    def test_forecast_full_pipeline_zero_cagr(self):
        out = fe.forecast_full_pipeline([0.0, 1.0, 2.0, 3.0, 4.0], start_year=2020, years=2)
        assert "ensemble" in out
        assert np.isnan(out["growth"]["historical_cagr_pct"])


class TestProvinceAggregatorExtended:
    def test_aggregate_indicator_explicit(self):
        assert pa.aggregate_indicator("sum") == "sum"
        assert pa.aggregate_indicator("weighted_avg") == "weighted_avg"
        assert pa.aggregate_indicator("avg") == "avg"

    def test_get_province_index_from_registry(self):
        index = pa.get_province_index()
        assert isinstance(index, dict)
        # Cities are present under their provinces.
        assert any("深圳" in cities for cities in index.values())

    def test_get_province_timeseries_missing_indicator(self, monkeypatch):
        monkeypatch.setattr(pa, "get_province_index", lambda: {"广东": ["深圳"]})
        hist = pd.DataFrame({"year": [2021, 2022], "gdp": [100.0, 110.0], "population": [1000, 1010]})
        monkeypatch.setattr(pa, "get_historical_data", lambda city: hist)
        df = pa.get_province_timeseries("广东", "rd_intensity")
        assert df.empty

    def test_get_province_timeseries_with_nan(self, monkeypatch):
        monkeypatch.setattr(pa, "get_province_index", lambda: {"广东": ["深圳"]})
        hist = pd.DataFrame(
            {
                "year": [2021, 2022, 2023],
                "gdp": [100.0, np.nan, 120.0],
                "population": [1000, 1010, 1020],
            }
        )
        monkeypatch.setattr(pa, "get_historical_data", lambda city: hist)
        df = pa.get_province_timeseries("广东", "gdp")
        assert len(df) == 2

    def test_get_province_timeseries_avg_aggregation(self, monkeypatch):
        monkeypatch.setattr(pa, "get_province_index", lambda: {"广东": ["深圳", "广州"]})
        hist_sz = pd.DataFrame({"year": [2023], "foo": [10.0]})
        hist_gz = pd.DataFrame({"year": [2023], "foo": [20.0]})
        data = {"深圳": hist_sz, "广州": hist_gz}
        monkeypatch.setattr(pa, "get_historical_data", lambda city: data.get(city, pd.DataFrame()))
        df = pa.get_province_timeseries("广东", "foo")
        assert len(df) == 1
        assert df["value"].iloc[0] == pytest.approx(15.0)

    def test_forecast_series_linear(self):
        out = pa.forecast_series([1.0, 2.0, 3.0, 4.0, 5.0], years=2, start_year=2024)
        assert out["method"].startswith("Linear Regression")
        assert out["years"] == [2025, 2026]
        assert len(out["predictions"]) == 2

    def test_forecast_city_indicator_success_real_city(self):
        result = pa.forecast_city_indicator("深圳", "gdp", years=3)
        if "error" in result:
            pytest.skip("Real city data not available in this environment")
        assert result["scope"] == "city"
        assert len(result["forecast_values"]) == 3
        assert "growth" in result

    def test_forecast_province_indicator_not_found(self):
        result = pa.forecast_province_indicator("不存在的省", "gdp")
        assert "error" in result

    def test_forecast_province_indicator_empty_data(self, monkeypatch):
        monkeypatch.setattr(pa, "get_province_index", lambda: {"广东": ["深圳"]})
        monkeypatch.setattr(pa, "get_province_timeseries", lambda _p, _i: pd.DataFrame())
        result = pa.forecast_province_indicator("广东", "gdp")
        assert "error" in result

    def test_forecast_all_provinces_skips_errors(self, monkeypatch):
        monkeypatch.setattr(pa, "get_province_index", lambda: {"广东": ["深圳"], "浙江": ["杭州"]})

        def fake_timeseries(province: str, indicator: str) -> pd.DataFrame:
            if province == "广东":
                return pd.DataFrame({"year": [2021, 2022], "value": [100.0, 110.0], "cities": [["深圳"], ["深圳"]]})
            return pd.DataFrame()

        monkeypatch.setattr(pa, "get_province_timeseries", fake_timeseries)
        result = pa.forecast_all_provinces("gdp", years=2)
        assert "广东" in result["provinces"]
        assert "浙江" not in result["provinces"]
        assert len(result["comparison"]) == 1
        assert result["comparison"][0]["province"] == "广东"

    def test_cagr_edge_cases(self):
        assert np.isnan(pa._cagr(None, 100, 2))
        assert np.isnan(pa._cagr(100, -100, 2))
