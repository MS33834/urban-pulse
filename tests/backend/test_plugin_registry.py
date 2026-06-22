"""
插件注册表与自动发现测试
"""

import numpy as np
import pandas as pd

from backend.analysis.base_analyzer import AnalysisPlugin
from backend.analysis.housing_affordability_analyzer import HousingAffordabilityAnalyzer
from backend.core.forecast_base import ForecastingPlugin
from backend.core.linear_trend_forecaster import LinearTrendForecaster
from backend.core.plugin_registry import PluginRegistry
from backend.data_collection.base_collector import DataCollector
from backend.data_collection.world_bank_collector import WorldBankCollector
from backend.utils.html_table_visualizer import HtmlTableVisualizer
from backend.utils.visualizer_base import VisualizerPlugin


class DummyCollector(DataCollector):
    def name(self) -> str:
        return "dummy_collector"

    def supported_cities(self) -> list[str]:
        return ["CN-SZ"]

    def fetch_data(self, **kwargs) -> list[dict]:
        return [{"value": 1}]

    def fetch_all(self, indicators: list[str] | None = None) -> dict[str, list[dict]]:
        return {"dummy": [{"value": 1}]}


class DummyAnalyzer(AnalysisPlugin):
    def name(self) -> str:
        return "dummy_analyzer"

    def required_indicators(self) -> list[str]:
        return ["gdp"]

    def analyze(self, city_data: dict, **params) -> dict:
        return {"score": 100}


class DummyForecaster(ForecastingPlugin):
    def name(self) -> str:
        return "dummy_forecaster"

    def forecast(self, data: pd.Series, steps: int) -> tuple[np.ndarray, np.ndarray]:
        return np.ones(steps), np.zeros(steps)

    def min_data_points(self) -> int:
        return 3


class DummyVisualizer(VisualizerPlugin):
    def name(self) -> str:
        return "dummy_visualizer"

    def render(self, data: dict) -> str:
        return "<div>dummy</div>"


class TestPluginRegistry:
    def setup_method(self):
        PluginRegistry.clear()

    def teardown_method(self):
        PluginRegistry.clear()

    def test_register_and_get_collector(self):
        PluginRegistry.register_collector(DummyCollector())
        collector = PluginRegistry.get_collector("dummy_collector")
        assert collector is not None
        assert collector.name() == "dummy_collector"

    def test_register_analyzer(self):
        PluginRegistry.register_analyzer(DummyAnalyzer())
        assert "dummy_analyzer" in PluginRegistry.list_analyzers()

    def test_register_forecaster(self):
        PluginRegistry.register_forecaster(DummyForecaster())
        forecaster = PluginRegistry.get_forecaster("dummy_forecaster")
        assert forecaster.min_data_points() == 3

    def test_register_visualizer(self):
        PluginRegistry.register_visualizer(DummyVisualizer())
        assert "dummy_visualizer" in PluginRegistry.list_visualizers()

    def test_discover_collectors(self):
        PluginRegistry.discover("backend.data_collection", DataCollector, PluginRegistry._collectors)
        names = PluginRegistry.list_collectors()
        assert "nbs" in names
        assert "pbc" in names
        assert "industry" in names
        assert "survey" in names

    def test_discovered_collector_has_methods(self):
        PluginRegistry.discover("backend.data_collection", DataCollector, PluginRegistry._collectors)
        nbs = PluginRegistry.get_collector("nbs")
        assert nbs is not None
        assert nbs.supported_cities() == ["CN"]

    def test_discover_external_plugins_via_entry_points(self):
        PluginRegistry.discover_all()
        names = PluginRegistry.list_collectors()
        assert "demo_collector" in names
        demo = PluginRegistry.get_collector("demo_collector")
        assert demo is not None
        assert demo.supported_cities() == ["demo_city"]


class TestExamplePlugins:
    def test_world_bank_collector_fallback(self):
        collector = WorldBankCollector(use_api=False)
        data = collector.fetch_data(city="new_york")
        indicators = {record["indicator"] for record in data}
        assert "gdp_current_usd" in indicators
        assert "population" in indicators

    def test_world_bank_collector_supported_cities(self):
        collector = WorldBankCollector(use_api=False)
        assert "shanghai" in collector.supported_cities()
        assert "tokyo" in collector.supported_cities()

    def test_housing_affordability_analyzer(self):
        analyzer = HousingAffordabilityAnalyzer()
        result = analyzer.analyze({"median_house_price": 600_000, "median_household_income": 80_000})
        assert result["status"] == "success"
        assert result["price_to_income_ratio"] == 7.5
        assert result["stress_level"] == "high"

    def test_linear_trend_forecaster(self):
        forecaster = LinearTrendForecaster()
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        mean, ci = forecaster.forecast(series, steps=3)
        assert len(mean) == 3
        assert len(ci) == 3
        assert abs(mean[-1] - 8.0) < 1e-6

    def test_html_table_visualizer(self):
        visualizer = HtmlTableVisualizer()
        html = visualizer.render(
            {
                "title": "测试表",
                "records": [
                    {"city": "深圳", "gdp": 3000},
                    {"city": "上海", "gdp": 4500},
                ],
            }
        )
        assert "<table" in html
        assert "深圳" in html
        assert "测试表" in html
