"""
线性趋势预测器（插件示例）

基于简单线性回归对未来值进行预测，数据需求低、计算轻量，
适合作为 ForecastingPlugin 的入门示例与基准模型。
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from backend.core.forecast_base import ForecastingPlugin

logger = logging.getLogger(__name__)


class LinearTrendForecaster(ForecastingPlugin):
    """线性趋势预测器插件。"""

    def metadata(self) -> dict[str, Any]:
        return {
            "description": "基于简单线性回归对未来值进行预测，数据需求低、计算轻量，适合作为基准模型。",
            "version": "0.1.0",
            "author": "Urban Pulse Team",
            "tags": ["forecast", "linear", "baseline"],
            "parameters": [
                {
                    "name": "steps",
                    "type": "int",
                    "required": True,
                    "default": None,
                    "description": "需要预测的未来步数",
                },
            ],
            "example": {
                "data": [1.0, 2.0, 3.0, 4.0, 5.0],
                "steps": 3,
            },
        }

    def name(self) -> str:
        return "linear_trend"

    def min_data_points(self) -> int:
        return 3

    def forecast(self, data: pd.Series, steps: int) -> tuple[np.ndarray, np.ndarray]:
        """
        对时间序列做线性外推预测。

        Args:
            data: 历史时间序列（等间隔）
            steps: 预测步数

        Returns:
            (mean_forecast, confidence_intervals)
        """
        values = np.asarray(data.dropna(), dtype=float)
        n = len(values)
        if n < self.min_data_points():
            raise ValueError(f"线性趋势预测至少需要 {self.min_data_points()} 个数据点")

        x = np.arange(n)
        slope, intercept, r_value, _, std_err = stats.linregress(x, values)

        # 预测未来 steps 个点
        future_x = np.arange(n, n + steps)
        forecast = slope * future_x + intercept

        # 置信区间：用残差标准差近似
        predictions = slope * x + intercept
        residuals = values - predictions
        residual_std = np.std(residuals, ddof=1) if len(residuals) > 1 else 0.0
        confidence_intervals = np.full(steps, residual_std * 1.96)

        logger.debug(f"线性趋势预测: slope={slope:.4f}, intercept={intercept:.4f}, r²={r_value**2:.4f}")
        return forecast, confidence_intervals
