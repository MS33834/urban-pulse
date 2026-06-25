"""
全要素生产率（TFP）测算模型

使用 DEA-Malmquist 方法测算技术进步与效率变化。
参考：张自然《中国上市公司全要素生产率的异质性与收敛性》
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


class TFPModel:
    """
    简化版 TFP 模型：基于 Cobb-Douglas 生产函数的对数线性回归。

    ln(Y) = ln(A) + alpha * ln(K) + beta * ln(L) + epsilon
    TFP = Y / (K^alpha * L^beta)
    """

    def __init__(self, output_col: str = "gdp", capital_col: str = "capital", labor_col: str = "labor"):
        self.output_col = output_col
        self.capital_col = capital_col
        self.labor_col = labor_col
        self.alpha: float | None = None
        self.beta: float | None = None
        self.tfp_values: pd.Series | None = None

    def fit(self, df: pd.DataFrame) -> "TFPModel":
        data = df[[self.output_col, self.capital_col, self.labor_col]].dropna().copy()
        data = data[data[self.output_col] > 0]
        data = data[data[self.capital_col] > 0]
        data = data[data[self.labor_col] > 0]

        log_y = np.log(data[self.output_col])
        log_k = np.log(data[self.capital_col])
        log_l = np.log(data[self.labor_col])

        X = np.column_stack([np.ones(len(data)), log_k, log_l])
        beta = np.linalg.lstsq(X, log_y, rcond=None)[0]

        self.alpha = float(beta[1])
        self.beta = float(beta[2])

        # 计算 TFP
        tfp = np.exp(log_y - self.alpha * log_k - self.beta * log_l)
        self.tfp_values = pd.Series(tfp, index=data.index)
        return self

    def run(self, df: pd.DataFrame) -> dict[str, Any]:
        self.fit(df)
        tfp = self.tfp_values
        return {
            "model": "TFP_Cobb_Douglas",
            "output": self.output_col,
            "capital": self.capital_col,
            "labor": self.labor_col,
            "alpha": self.alpha,
            "beta": self.beta,
            "returns_to_scale": round(self.alpha + self.beta, 4),
            "tfp": tfp.to_dict(),
            "summary": {
                "mean_tfp": float(tfp.mean()),
                "median_tfp": float(tfp.median()),
                "min_tfp": float(tfp.min()),
                "max_tfp": float(tfp.max()),
                "observations": len(tfp),
            },
        }
