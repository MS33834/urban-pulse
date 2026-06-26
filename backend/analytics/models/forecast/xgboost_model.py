"""
基于 XGBoost 的多因素经济预测模型

参考：HansPub《预测中国 GDP 增长率：基于 R 语言和机器学习的分析》
"""

from __future__ import annotations

from typing import Any

import pandas as pd


class XGBoostForecastModel:
    """
    简化版梯度提升预测模型。

    如果未安装 xgboost，则使用 sklearn 的 GradientBoostingRegressor 作为 fallback。
    """

    def __init__(self, target: str, features: list[str], lags: int = 2):
        self.target = target
        self.features = features
        self.lags = lags
        self.model = None

    def _build_lagged_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """构建滞后特征"""
        cols = [self.target] + self.features
        data = df[cols].copy()
        for lag in range(1, self.lags + 1):
            for col in cols:
                data[f"{col}_lag{lag}"] = data[col].shift(lag)
        return data.dropna()

    def fit(self, df: pd.DataFrame) -> XGBoostForecastModel:
        data = self._build_lagged_features(df)
        X = data.drop(columns=[self.target] + self.features)
        y = data[self.target]

        try:
            from xgboost import XGBRegressor

            self.model = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
        except ImportError:
            from sklearn.ensemble import GradientBoostingRegressor

            self.model = GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=42)

        self.model.fit(X, y)
        self.feature_names_ = list(X.columns)
        return self

    def forecast(self, df: pd.DataFrame, steps: int = 3) -> list[dict[str, Any]]:
        if self.model is None:
            raise ValueError("模型尚未拟合")

        predictions = []
        current = df.copy()

        for step in range(1, steps + 1):
            data = self._build_lagged_features(current)
            X = data[self.feature_names_].iloc[-1:].values
            pred = float(self.model.predict(X)[0])
            predictions.append({"step": step, self.target: round(pred, 4)})

            # 将预测值追加到序列末尾用于下一步预测
            new_row = current.iloc[-1:].copy()
            new_row[self.target] = pred
            current = pd.concat([current, new_row], ignore_index=True)

        return predictions

    def feature_importance(self) -> dict[str, float]:
        if self.model is None:
            raise ValueError("模型尚未拟合")
        importance = self.model.feature_importances_
        return {name: float(val) for name, val in zip(self.feature_names_, importance)}

    def run(self, df: pd.DataFrame, steps: int = 3) -> dict[str, Any]:
        self.fit(df)
        forecast = self.forecast(df, steps)
        return {
            "model": "XGBoost",
            "target": self.target,
            "features": self.features,
            "lags": self.lags,
            "forecast": forecast,
            "feature_importance": self.feature_importance(),
            "summary": {"observations": len(df)},
        }
