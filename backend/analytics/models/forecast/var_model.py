"""
向量自回归模型（VAR）

用于多变量时间序列的联动分析与预测。
参考：Sims (1980) 向量自回归框架；中国城市财政/债务/投资动态研究。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class VARResult:
    """VAR 模型结果"""

    variables: list[str]
    lags: int
    forecast: pd.DataFrame
    fitted_values: pd.DataFrame
    residuals: pd.DataFrame
    coefficients: dict[str, pd.DataFrame]
    summary: dict[str, Any]


class VARModel:
    """
    简化版 VAR 模型实现。

    使用普通最小二乘法估计每个变量的自回归方程：
        y_t = c + A1*y_{t-1} + ... + Ap*y_{t-p} + e_t
    """

    def __init__(self, lags: int = 2):
        self.lags = lags
        self.variables: list[str] = []
        self.coefficients: dict[str, pd.DataFrame] = {}
        self.residuals: pd.DataFrame | None = None
        self.fitted: pd.DataFrame | None = None

    def fit(self, df: pd.DataFrame) -> VARModel:
        """
        拟合 VAR 模型。

        Args:
            df: 列名为变量名的时间序列 DataFrame
        """
        df = df.dropna()
        self.variables = list(df.columns)
        n = len(df)

        # 构建滞后矩阵
        X = np.ones((n - self.lags, 1))
        for lag in range(1, self.lags + 1):
            X = np.hstack([X, df.iloc[self.lags - lag : n - lag].values])

        for i, var in enumerate(self.variables):
            y = df.iloc[self.lags :, i].values
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
            coef_names = ["const"] + [
                f"{v}_lag{lag}" for lag in range(1, self.lags + 1) for v in self.variables
            ]
            self.coefficients[var] = pd.DataFrame({"coef": beta}, index=coef_names)

        # 拟合值与残差
        fitted = np.column_stack(
            [X @ self.coefficients[var]["coef"].values for var in self.variables]
        )
        self.fitted = pd.DataFrame(fitted, columns=self.variables, index=df.index[self.lags :])
        self.residuals = df.iloc[self.lags :] - self.fitted
        return self

    def forecast(self, steps: int = 3) -> pd.DataFrame:
        """预测未来 steps 期"""
        if not self.coefficients:
            raise ValueError("模型尚未拟合")

        # 取最近 lags 期观测值
        last_values = self.fitted.iloc[-self.lags :].values
        forecasts = []
        current = last_values.copy()

        for _ in range(steps):
            X_new = np.ones((1, 1))
            for lag in range(self.lags):
                X_new = np.hstack([X_new, current[-(lag + 1) :, :]])
            pred = np.array(
                [X_new @ self.coefficients[var]["coef"].values for var in self.variables]
            )
            forecasts.append(pred.flatten())
            current = np.vstack([current, pred.flatten()])

        index = pd.RangeIndex(start=1, stop=steps + 1, name="step")
        return pd.DataFrame(forecasts, columns=self.variables, index=index)

    def run(self, df: pd.DataFrame, steps: int = 3) -> dict[str, Any]:
        """端到端运行并返回可序列化结果"""
        self.fit(df)
        fc = self.forecast(steps)

        return {
            "model": "VAR",
            "lags": self.lags,
            "variables": self.variables,
            "coefficients": {k: v.to_dict() for k, v in self.coefficients.items()},
            "forecast": fc.to_dict(orient="records"),
            "r2": {
                var: float(
                    1 - (self.residuals[var].var() / df.iloc[self.lags :][var].var())
                )
                for var in self.variables
            },
            "summary": {
                "observations": len(df),
                "fitted_observations": len(self.fitted),
                "variables": self.variables,
            },
        }
