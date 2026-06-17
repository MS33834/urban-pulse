"""权重计算模块 — 熵权法与默认权重

熵权法基于指标信息熵确定客观权重：
  1. 数据标准化（避免 log(0)）
  2. 计算概率矩阵
  3. 计算熵值
  4. 计算差异系数 → 权重
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from backend.analytics.competitiveness.framework import IndicatorFramework

logger = logging.getLogger(__name__)


def entropy_weight(data_matrix: pd.DataFrame) -> pd.Series:
    """熵权法计算客观权重

    Args:
        data_matrix: 数据矩阵，行=城市/样本，列=指标（均为正值），无缺失值

    Returns:
        pd.Series: {指标名: 权重}，权重和为 1

    Raises:
        ValueError: 如果 data_matrix 为空或包含非正值/NaN
    """
    if data_matrix.empty:
        raise ValueError("数据矩阵为空，无法计算熵权法权重")

    # 确保数值类型
    mat = data_matrix.select_dtypes(include=[np.number])

    if mat.empty:
        raise ValueError("数据矩阵中没有数值列")

    # 用列均值填充 NaN（缺失数据不应扭曲权重）
    mat = mat.apply(lambda col: col.fillna(col.mean()) if col.notna().any() else col)
    # 移除全 NaN 列
    mat = mat.dropna(axis=1, how="all")
    if mat.empty:
        raise ValueError("移除全 NaN 列后数据矩阵为空")

    # 熵权法要求正值：若有非正值，做最小正值平移（标准做法）
    min_val = mat.min().min()
    if min_val <= 0:
        # 平移使最小值变为一个小的正数 ε
        mat = mat + abs(min_val) + 1e-6

    n_samples, n_features = mat.shape
    if n_samples < 2:
        # 只有一个样本，无法计算熵，返回等权
        weights = pd.Series(1.0 / n_features, index=mat.columns)
        logger.warning("样本数 < 2，使用等权替代熵权法")
        return weights

    # Step 1: 概率矩阵 — 每列归一化
    col_sums = mat.sum(axis=0)
    # 避免除零
    col_sums = col_sums.replace(0, 1.0)
    prob = mat.div(col_sums)

    # Step 2: 计算熵值
    # 避免 log(0)：用很小的值替换 0
    prob_clipped = prob.clip(lower=1e-12)
    # 熵值公式：e_j = -k * sum(p_ij * ln(p_ij)), k = 1/ln(n)
    k = 1.0 / np.log(n_samples)
    entropy = -k * (prob_clipped * np.log(prob_clipped)).sum(axis=0)

    # Step 3: 差异系数 = 1 - e_j
    diff_coef = 1.0 - entropy

    # Step 4: 权重 = 差异系数 / sum(差异系数)
    total_diff = diff_coef.sum()
    if total_diff <= 0:
        # 所有指标熵值均为 1（完全均匀分布），使用等权
        weights = pd.Series(1.0 / n_features, index=mat.columns)
        logger.warning("所有指标熵值均为 1，使用等权替代")
    else:
        weights = diff_coef / total_diff

    return weights


def get_weights(
    method: str = "entropy",
    data_matrix: pd.DataFrame | None = None,
    framework: type[IndicatorFramework] = IndicatorFramework,
) -> dict[str, float]:
    """获取综合权重

    先用 framework 默认权重（等权），如果有数据矩阵则用熵权法覆盖。

    Args:
        method: 权重方法，"entropy" 使用熵权法，"default" 使用默认权重
        data_matrix: 数据矩阵（用于熵权法），行=城市，列=指标
        framework: 指标体系类

    Returns:
        dict[str, float]: {指标键: 权重}，权重和为 1
    """
    # 获取所有已覆盖指标的默认权重
    indicators = framework.get_covered_indicators()
    default_weights: dict[str, float] = {k: v["weight"] for k, v in indicators.items()}

    if method == "default" or data_matrix is None:
        logger.info("使用默认等权权重")
        return dict(default_weights)

    if method == "entropy":
        # 用数据矩阵计算熵权法权重
        entropy_result = entropy_weight(data_matrix)

        # 只取 framework 中有定义的指标
        covered_keys = set(indicators.keys())
        result: dict[str, float] = {}

        for key, w in entropy_result.items():
            if key in covered_keys:
                result[key] = w

        if not result:
            logger.warning("熵权法未返回任何有效权重，回退到默认权重")
            return dict(default_weights)

        # 归一化确保和为 1
        total = sum(result.values())
        result = {k: v / total for k, v in result.items()}

        # 补充 framework 中有但数据矩阵中没有的指标（用默认权重等比例缩小）
        missing = covered_keys - set(result.keys())
        if missing and result:
            # 等比例缩小现有权重，释放空间给缺失指标
            # 实际上缺失指标在数据矩阵中没出现，在榜单中也不会有，直接跳过
            pass

        logger.info("使用熵权法计算权重，共 %d 个指标", len(result))
        return result

    logger.warning("未知的权重方法: %s，回退到默认权重", method)
    return dict(default_weights)
