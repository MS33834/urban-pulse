"""数据标准化模块 — MinMax 标准化

将原始指标数据映射到 [0, 100] 区间，
正向指标：值越大得分越高
逆向指标：值越小得分越高
双向指标：值越接近中位数得分越高
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from backend.analytics.competitiveness.framework import IndicatorFramework

logger = logging.getLogger(__name__)


def minmax_normalize(
    data: dict[str, dict[str, float]],
    framework: type[IndicatorFramework] = IndicatorFramework,
) -> dict[str, dict[str, float]]:
    """MinMax 标准化，结果映射到 [0, 100]

    Args:
        data: 输入数据，{城市名: {指标键: 原始值}}
        framework: 指标体系类，用于获取指标方向

    Returns:
        标准化后的数据，{城市名: {指标键: 标准分 (0-100)}}

    Raises:
        ValueError: 如果输入数据为空
    """
    if not data:
        raise ValueError("输入数据为空，无法进行标准化")

    city_names: list[str] = list(data.keys())
    all_indicator_keys: set[str] = set()
    for city_data in data.values():
        all_indicator_keys.update(city_data.keys())

    # 收集每个指标在所有城市的取值
    indicator_values: dict[str, list[float]] = {}
    for key in all_indicator_keys:
        values: list[float] = []
        for city_data in data.values():
            v = city_data.get(key)
            if v is not None and isinstance(v, (int, float)):
                values.append(float(v))
        if values:
            indicator_values[key] = values

    if not indicator_values:
        raise ValueError("所有指标数据均为空，无法标准化")

    # 计算每个指标的 min/max
    bounds: dict[str, dict[str, float]] = {}
    for key, values in indicator_values.items():
        bounds[key] = {
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "range": float(np.max(values)) - float(np.min(values)),
        }

    result: dict[str, dict[str, float]] = {}
    for city_name in city_names:
        result[city_name] = {}
        city_data = data[city_name]
        for key in all_indicator_keys:
            raw_value = city_data.get(key)
            if raw_value is None or not isinstance(raw_value, (int, float)):
                result[city_name][key] = 0.0
                continue

            bounds_info = bounds.get(key)
            if bounds_info is None:
                result[city_name][key] = 50.0  # 无对比基准时给中间值
                continue

            v_range = bounds_info["range"]
            if v_range == 0:
                result[city_name][key] = 50.0  # 所有城市值相同给中间值
                continue

            direction = framework.get_direction(key)
            raw_f = float(raw_value)
            normalized: float = 0.0

            if direction == "positive":
                # 正向：越大越好
                normalized = (raw_f - bounds_info["min"]) / v_range
            elif direction == "negative":
                # 逆向：越小越好
                normalized = (bounds_info["max"] - raw_f) / v_range
            elif direction == "bidirectional":
                # 双向：越接近中位数越好
                median = float(np.median(indicator_values[key]))
                # 使用到中位数的距离，归一化到 [0, 1]
                max_deviation = max(
                    abs(bounds_info["max"] - median),
                    abs(bounds_info["min"] - median),
                )
                if max_deviation > 0:
                    distance = abs(raw_f - median)
                    normalized = 1.0 - (distance / max_deviation)
                else:
                    normalized = 1.0
            else:
                # 默认按正向处理
                normalized = (raw_f - bounds_info["min"]) / v_range

            # 裁剪到 [0, 1] 并映射到 [0, 100]
            result[city_name][key] = round(max(0.0, min(1.0, normalized)) * 100.0, 1)

    return result
