"""补充 backend.utils.visualizer 与相关可视化工具的覆盖测试。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.utils.visualizer import Visualizer
from backend.utils.visualizer_base import VisualizerPlugin


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "year": list(range(2010, 2026)),
            "gdp": np.linspace(1000, 5000, 16),
            "population": np.linspace(500, 900, 16),
        }
    )


@pytest.fixture
def visualizer():
    return Visualizer(theme="plotly_white", color_palette=["#1f77b4", "#ff7f0e", "#2ca02c"])


class TestVisualizerTimeSeries:
    def test_time_series_basic(self, visualizer, sample_df):
        fig = visualizer.time_series_plot(sample_df, x="year", y="gdp", title="GDP")
        assert fig is not None
        assert len(fig.data) >= 1
        assert fig.layout.title.text == "GDP"

    def test_time_series_with_trend_and_ma(self, visualizer, sample_df):
        fig = visualizer.time_series_plot(sample_df, x="year", y="gdp", show_trend=True, show_ma=True, ma_window=3)
        # 原始数据 + 移动平均 + 趋势线
        assert len(fig.data) == 3

    def test_time_series_too_short_for_ma(self, visualizer):
        df = pd.DataFrame({"year": [1, 2], "gdp": [10, 20]})
        fig = visualizer.time_series_plot(df, x="year", y="gdp", show_trend=False, show_ma=True, ma_window=5)
        assert len(fig.data) == 1  # 只有原始数据

    def test_time_series_insufficient_valid_points_for_trend(self, visualizer):
        df = pd.DataFrame({"year": [1], "gdp": [10]})
        fig = visualizer.time_series_plot(df, x="year", y="gdp", show_trend=True)
        assert len(fig.data) == 1


class TestVisualizerCorrelationHeatmap:
    def test_correlation_heatmap_default(self, visualizer, sample_df):
        fig = visualizer.correlation_heatmap(sample_df, title="Corr")
        assert fig is not None
        assert fig.layout.title.text == "Corr"

    def test_correlation_heatmap_with_columns(self, visualizer, sample_df):
        fig = visualizer.correlation_heatmap(sample_df, columns=["gdp", "population"], method="spearman")
        assert fig is not None


class TestVisualizerDistributionPlot:
    def test_distribution_plot(self, visualizer):
        df = pd.DataFrame({"value": np.random.randn(100)})
        fig = visualizer.distribution_plot(df, column="value", bins=20)
        assert fig is not None
        assert len(fig.data) == 2  # 直方图 + KDE

    def test_distribution_plot_no_kde(self, visualizer):
        df = pd.DataFrame({"value": np.random.randn(100)})
        fig = visualizer.distribution_plot(df, column="value", show_kde=False)
        assert len(fig.data) == 1


class TestVisualizerComparisonBar:
    def test_comparison_bar(self, visualizer):
        df = pd.DataFrame({"city": ["A", "B"], "gdp": [100, 200]})
        fig = visualizer.comparison_bar(df, x="city", y="gdp", title="GDP Compare")
        assert fig is not None

    def test_comparison_bar_with_color(self, visualizer):
        df = pd.DataFrame({"city": ["A", "B"], "gdp": [100, 200], "group": ["x", "y"]})
        fig = visualizer.comparison_bar(df, x="city", y="gdp", color="group")
        assert fig is not None


class TestVisualizerRadarChart:
    def test_radar_chart_no_group(self, visualizer):
        df = pd.DataFrame({"category": ["A", "B", "C"], "value": [1, 2, 3]})
        fig = visualizer.radar_chart(df, categories="category", values="value")
        assert fig is not None
        assert len(fig.data) == 1

    def test_radar_chart_with_group(self, visualizer):
        df = pd.DataFrame(
            {
                "category": ["A", "B", "A", "B"],
                "value": [1, 2, 3, 4],
                "group": ["X", "X", "Y", "Y"],
            }
        )
        fig = visualizer.radar_chart(df, categories="category", values="value", group="group")
        assert len(fig.data) == 2


class TestVisualizerDashboard:
    def test_dashboard(self, visualizer, sample_df):
        fig = visualizer.dashboard(sample_df, metrics={"GDP": "gdp", "Population": "population"}, time_col="year")
        assert fig is not None
        assert len(fig.data) == 2


class TestVisualizerBase:
    def test_visualizer_plugin_default_supported_types(self):
        class DummyPlugin(VisualizerPlugin):
            def name(self):
                return "dummy"

            def render(self, data):
                return "dummy"

        plugin = DummyPlugin()
        assert plugin.supported_data_types() == ["generic"]
