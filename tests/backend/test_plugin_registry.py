"""
插件注册表与自动发现测试
"""

import numpy as np
import pandas as pd

from backend.analysis.base_analyzer import AnalysisPlugin
from backend.core.forecast_base import ForecastingPlugin
from backend.core.plugin_registry import PluginRegistry
from backend.data_collection.base_collector import DataCollector
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
