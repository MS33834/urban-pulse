"""
Urban Pulse 可视化引擎

提供数据画像、图表推荐、通用图表配置协议与后端预渲染能力。
"""

from backend.viz.profiler import DataProfile, profile_dataset
from backend.viz.recommender import ChartRecommendation, recommend_charts
from backend.viz.schema import ChartConfig, ChartType, DataSource, Encoding, Interaction, Style

__all__ = [
    "ChartConfig",
    "ChartType",
    "DataSource",
    "Encoding",
    "Interaction",
    "Style",
    "DataProfile",
    "profile_dataset",
    "ChartRecommendation",
    "recommend_charts",
]
