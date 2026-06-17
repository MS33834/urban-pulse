"""综合排名引擎 — CompetitivenessRanker

管理从数据加载 → 标准化 → 赋权 → 算分的端到端流程。
支持单城市分析报告和多城市综合排名。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from backend.analytics.competitiveness.framework import IndicatorFramework
from backend.analytics.competitiveness.normalizer import minmax_normalize
from backend.analytics.competitiveness.weighting import get_weights

logger = logging.getLogger(__name__)


class CompetitivenessRanker:
    """城市竞争力排名引擎"""

    def __init__(
        self,
        data_provider: Callable[[], dict[str, dict[str, float]]],
        framework: type[IndicatorFramework] = IndicatorFramework,
    ):
        """初始化排名引擎

        Args:
            data_provider: 可调用对象，返回 {城市名: {指标键: 原始值}}
            framework: 指标体系类
        """
        self._data_provider = data_provider
        self._framework = framework

    def _load_data(
        self, city_names: list[str] | None = None
    ) -> dict[str, dict[str, float]]:
        """加载城市数据，只取框架中定义的指标

        Args:
            city_names: 可选的城市名列表，None 表示加载所有城市

        Returns:
            过滤后的数据
        """
        raw_data = self._data_provider()

        if not raw_data:
            logger.warning("data_provider 返回空数据")
            return {}

        # 只取框架中定义的指标
        covered_keys = set(self._framework.get_covered_indicators().keys())

        result: dict[str, dict[str, float]] = {}
        for city_name, city_indicators in raw_data.items():
            if city_names is not None and city_name not in city_names:
                continue
            filtered: dict[str, float] = {}
            for key in covered_keys:
                val = city_indicators.get(key)
                if val is not None and isinstance(val, (int, float)):
                    filtered[key] = float(val)
            if filtered:
                result[city_name] = filtered

        return result

    def compute_index(
        self, city_names: list[str] | None = None, method: str = "entropy"
    ) -> dict[str, Any]:
        """计算城市竞争力指数

        Args:
            city_names: 可选的城市名列表，None 表示所有城市
            method: 权重方法，"entropy" 或 "default"

        Returns:
            dict 包含:
              - overall: {城市名: 综合得分}
              - dimensions: {维度名: {城市名: 维度分}}
              - rankings: {维度名/overall: [(城市名, 得分)]}
              - missing_dimensions: 无数据覆盖的维度列表
              - methodology: 方法论描述
        """
        # 1. 加载数据
        filtered_data = self._load_data(city_names)
        if not filtered_data:
            return {
                "overall": {},
                "dimensions": {},
                "rankings": {},
                "missing_dimensions": [d["name"] for d in self._framework.get_missing_dimensions()],
                "methodology": "熵权法 + MinMax标准化",
                "error": "数据为空",
            }

        # 2. 标准化
        normalized = minmax_normalize(filtered_data, self._framework)

        # 3. 获取维度映射
        dim_mapping = self._framework.get_dimension_mapping()
        data_dims = [d for d in dim_mapping if not d.get("data_missing", False)]
        missing_dims = [d["name"] for d in dim_mapping if d.get("data_missing", False)]

        # 4. 计算权重
        # 构建数据矩阵用于熵权法（向量化构建，缺失值用 NaN 填充，由熵权法内部处理）
        all_cities = sorted(normalized.keys())
        all_indicators = sorted(
            set(k for c in normalized.values() for k in c.keys())
        )
        data_matrix = pd.DataFrame.from_dict(normalized, orient="index").reindex(
            columns=all_indicators
        )
        # data_matrix 已经是 [0,100] 分，需要转为 [0,1] 用于熵权法
        data_matrix_01 = data_matrix / 100.0

        weights = get_weights(
            method=method,
            data_matrix=data_matrix_01 if method == "entropy" else None,
            framework=self._framework,
        )

        # 5. 计算维度得分
        # 每个维度的指标取标准分的加权平均
        dim_scores: dict[str, dict[str, float]] = {}
        dim_rankings: dict[str, list[tuple[str, float]]] = {}

        for dim in data_dims:
            dim_name: str = dim["name"]
            dim_indicators: list[str] = dim["indicators"]
            # 过滤掉没有权重的指标
            valid_inds = [k for k in dim_indicators if k in weights]
            if not valid_inds:
                continue

            dim_data: dict[str, float] = {}
            for city in all_cities:
                scores: list[float] = []
                w_sum: float = 0.0
                for ind in valid_inds:
                    s = normalized.get(city, {}).get(ind)
                    w = weights.get(ind, 0.0)
                    if s is not None and w > 0:
                        scores.append(s * w)
                        w_sum += w

                if w_sum > 0:
                    dim_data[city] = round(sum(scores) / w_sum, 1)
                else:
                    dim_data[city] = 0.0

            dim_scores[dim_name] = dim_data
            dim_rankings[dim_name] = sorted(
                dim_data.items(), key=lambda x: x[1], reverse=True
            )

        # 6. 计算综合得分
        overall_scores: dict[str, float] = {}
        for city in all_cities:
            total_weight: float = 0.0
            weighted_sum: float = 0.0

            for dim in data_dims:
                dim_name = dim["name"]
                dim_score = dim_scores.get(dim_name, {}).get(city)
                if dim_score is not None and dim_score > 0:
                    # 维度权重 = 该维度下所有指标权重之和
                    dim_weight = sum(
                        weights.get(k, 0.0) for k in dim["indicators"]
                        if k in weights
                    )
                    weighted_sum += dim_score * dim_weight
                    total_weight += dim_weight

            if total_weight > 0:
                overall_scores[city] = round(weighted_sum / total_weight, 1)
            else:
                overall_scores[city] = 0.0

        overall_rankings = sorted(
            overall_scores.items(), key=lambda x: x[1], reverse=True
        )

        # 7. 组装结果
        return {
            "overall": overall_scores,
            "dimensions": dim_scores,
            "rankings": {
                "overall": overall_rankings,
                **dim_rankings,
            },
            "missing_dimensions": missing_dims,
            "methodology": f"{'熵权法' if method == 'entropy' else '默认权重'} + MinMax标准化",
            "weights": weights,
            "normalized": normalized,
        }

    def generate_report(self, city_name: str) -> dict[str, Any]:
        """单城市深度分析报告

        Args:
            city_name: 城市名称

        Returns:
            深度分析报告
        """
        # 先算全部城市的指数
        index_result = self.compute_index()
        if city_name not in index_result["overall"]:
            return {
                "error": f"城市 {city_name} 不在数据中",
                "city_name": city_name,
            }

        # 该城市的综合得分与排名
        overall_ranking = index_result["rankings"]["overall"]
        city_rank = -1
        for i, (name, score) in enumerate(overall_ranking):
            if name == city_name:
                city_rank = i + 1
                break

        city_overall = index_result["overall"][city_name]
        total_cities = len(overall_ranking)

        # 各维度得分与排名
        dim_details: dict[str, dict[str, Any]] = {}
        for dim_name, dim_scores in index_result["dimensions"].items():
            dim_rank = -1
            sorted_dim = sorted(
                dim_scores.items(), key=lambda x: x[1], reverse=True
            )
            for i, (name, score) in enumerate(sorted_dim):
                if name == city_name:
                    dim_rank = i + 1
                    break

            dim_details[dim_name] = {
                "score": dim_scores.get(city_name, 0),
                "rank": dim_rank,
                "total": len(sorted_dim),
                "is_advantage": dim_rank > 0 and dim_rank <= 3,
                "is_disadvantage": dim_rank > 0 and dim_rank >= total_cities - 2,
            }

        # 优势/劣势指标
        advantages: list[dict[str, Any]] = []
        disadvantages: list[dict[str, Any]] = []

        # 优势/劣势指标 — 复用 compute_index 已计算的标准化数据，避免重复加载
        all_normalized = index_result.get("normalized", {})
        weights = index_result.get("weights", {})

        city_data = all_normalized.get(city_name, {})
        for ind_key, ind_value in city_data.items():
            # 该指标在所有城市的平均分
            all_scores = [
                all_normalized[c].get(ind_key, 0) for c in all_normalized
            ]
            avg_score = np.mean(all_scores) if all_scores else 0

            indicator_info = self._framework.get_all_indicators().get(ind_key, {})
            entry = {
                "key": ind_key,
                "name": indicator_info.get("name", ind_key),
                "score": ind_value,
                "average": round(float(avg_score), 1),
                "weight": weights.get(ind_key, 0),
            }

            score_diff = ind_value - avg_score
            if score_diff > 10:
                # 超过平均分 10 分以上 = 优势指标
                entry["advantage_gap"] = round(score_diff, 1)
                advantages.append(entry)
            elif score_diff < -10:
                # 低于平均分 10 分以上 = 劣势指标
                entry["disadvantage_gap"] = round(abs(score_diff), 1)
                disadvantages.append(entry)

        advantages.sort(key=lambda x: x["advantage_gap"], reverse=True)
        disadvantages.sort(key=lambda x: x["disadvantage_gap"], reverse=True)

        report = {
            "city_name": city_name,
            "overall_score": city_overall,
            "overall_rank": city_rank,
            "total_cities": total_cities,
            "dimensions": dim_details,
            "advantages": advantages[:5],
            "disadvantages": disadvantages[:5],
            "missing_dimensions": index_result["missing_dimensions"],
            "methodology": index_result["methodology"],
        }

        return report
