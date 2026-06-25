"""
经济韧性 DPSR 模型

基于 "驱动力-压力-状态-响应"（Driver-Pressure-State-Response）框架评估经济韧性。
参考：中国城市经济韧性时空演变特征研究；MDPI Land 韧性评估。
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


class DPSRResilienceModel:
    """
    DPSR 经济韧性评估模型。

    四个子系统：
    - 驱动力（Driver）：经济增长潜力，如 GDP 增速、投资增速
    - 压力（Pressure）：外部冲击强度，如失业率、债务率
    - 状态（State）：经济当前状态，如人均 GDP、产业结构
    - 响应（Response）：政策与市场调整能力，如财政支出、创新投入

    每个维度由用户指定指标，模型进行标准化、加权、综合评分。
    """

    def __init__(
        self,
        driver_indicators: list[str] | None = None,
        pressure_indicators: list[str] | None = None,
        state_indicators: list[str] | None = None,
        response_indicators: list[str] | None = None,
        weights: dict[str, float] | None = None,
    ):
        self.dimensions = {
            "driver": driver_indicators or [],
            "pressure": pressure_indicators or [],
            "state": state_indicators or [],
            "response": response_indicators or [],
        }
        self.weights = weights or {"driver": 0.25, "pressure": 0.25, "state": 0.25, "response": 0.25}

    def _normalize(self, df: pd.DataFrame, indicators: list[str], higher_is_better: bool = True) -> pd.DataFrame:
        """Min-Max 标准化"""
        result = pd.DataFrame(index=df.index)
        for col in indicators:
            if col not in df.columns:
                continue
            min_val = df[col].min()
            max_val = df[col].max()
            if max_val - min_val == 0:
                result[col] = 0.5
            else:
                normalized = (df[col] - min_val) / (max_val - min_val)
                result[col] = normalized if higher_is_better else 1 - normalized
        return result

    def run(self, df: pd.DataFrame, entity_col: str = "region") -> dict[str, Any]:
        results = []
        dimension_scores = {}

        # 压力指标是反向指标（值越大韧性越差）
        higher_is_better_map = {
            "driver": True,
            "pressure": False,
            "state": True,
            "response": True,
        }

        for dim, indicators in self.dimensions.items():
            if not indicators:
                continue
            normalized = self._normalize(df, indicators, higher_is_better_map[dim])
            dimension_scores[dim] = normalized.mean(axis=1)

        # 计算综合韧性得分
        resilience_score = pd.Series(0.0, index=df.index)
        total_weight = 0.0
        for dim, score in dimension_scores.items():
            weight = self.weights.get(dim, 0.25)
            resilience_score += score * weight
            total_weight += weight

        if total_weight > 0:
            resilience_score = resilience_score / total_weight

        # 转换到 0-100 分
        resilience_score = resilience_score * 100

        for idx, row in df.iterrows():
            item = {
                "entity": row.get(entity_col, str(idx)),
                "resilience_score": round(float(resilience_score.iloc[idx]), 2),
            }
            for dim, score in dimension_scores.items():
                item[f"{dim}_score"] = round(float(score.iloc[idx]) * 100, 2)
            results.append(item)

        results.sort(key=lambda x: x["resilience_score"], reverse=True)

        return {
            "model": "DPSR_Resilience",
            "dimensions": self.dimensions,
            "weights": self.weights,
            "results": results,
            "summary": {
                "mean_resilience": float(resilience_score.mean()),
                "top_entity": results[0]["entity"] if results else None,
                "bottom_entity": results[-1]["entity"] if results else None,
            },
        }
