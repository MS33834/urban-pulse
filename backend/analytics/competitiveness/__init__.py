"""城市竞争力指数引擎 — 基于倪鹏飞弓弦箭模型

将 19 个指标映射到硬竞争力（8 分力）和软竞争力（5 分力），
通过 MinMax 标准化 + 熵权法 生成综合竞争力指数。
"""

from backend.analytics.competitiveness.framework import IndicatorFramework
from backend.analytics.competitiveness.normalizer import minmax_normalize
from backend.analytics.competitiveness.ranker import CompetitivenessRanker
from backend.analytics.competitiveness.weighting import entropy_weight, get_weights

__all__ = [
    "IndicatorFramework",
    "minmax_normalize",
    "entropy_weight",
    "get_weights",
    "CompetitivenessRanker",
]
