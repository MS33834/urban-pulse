"""
预测模型插件基类

遵循 docs/PLUGIN_ARCHITECTURE.md 的 ForecastingPlugin 接口，
允许社区通过继承此类并 drop-in 文件的方式扩展新的预测算法。
"""

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class ForecastingPlugin(ABC):
    """预测模型插件基类。"""

    @abstractmethod
    def name(self) -> str:
        """模型名称，例如 'arima'、'prophet'、'lstm'。"""
        ...

    @abstractmethod
    def forecast(self, data: pd.Series, steps: int) -> tuple[np.ndarray, np.ndarray]:
        """
        对时间序列进行预测。

        Args:
            data: 历史时间序列数据
            steps: 需要预测的未来步数

        Returns:
            (mean_forecast, confidence_intervals)
            - mean_forecast: 每一步的预测均值
            - confidence_intervals: 与 mean_forecast 等长的区间半径（±值）
        """
        ...

    @abstractmethod
    def min_data_points(self) -> int:
        """运行该模型所需的最少历史数据点数。"""
        ...

    def is_applicable(self, data: pd.Series) -> bool:
        """检查当前数据是否满足该模型的最低数据量要求。"""
        return len(data.dropna()) >= self.min_data_points()
