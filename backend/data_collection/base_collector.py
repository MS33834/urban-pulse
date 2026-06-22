"""
数据采集基类
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """数据采集基类"""

    def __init__(self):
        self.source_name = ""

    @abstractmethod
    def fetch_data(self, **kwargs) -> list[dict[str, Any]]:
        """
        采集数据

        Returns:
            数据列表
        """
        pass

    @abstractmethod
    def fetch_all(self, indicators: list[str] | None = None) -> dict[str, list[dict]]:
        """
        批量采集所有数据

        Args:
            indicators: 指定采集的指标列表，None表示全部

        Returns:
            指标名到数据列表的映射
        """
        pass


class DataCollector(BaseCollector, ABC):
    """
    插件化数据采集器基类。

    继承 BaseCollector 的能力，同时增加插件注册表要求的 name() / supported_cities()
    接口，使新的数据源可以通过 drop-in 文件自动被发现。
    """

    @abstractmethod
    def name(self) -> str:
        """插件唯一名称，例如 'nbs'、'world_bank'。"""
        ...

    def source_name(self) -> str:
        """人类可读的数据源名称，默认返回 self.source_name 属性或类名。"""
        return getattr(self, "source_name", self.__class__.__name__)

    @abstractmethod
    def supported_cities(self) -> list[str]:
        """返回该采集器支持的城市代码列表。"""
        ...

    def collect(self, **kwargs) -> dict[str, pd.DataFrame]:
        """
        默认采集实现：调用 fetch_all 后将数据按城市分组为 DataFrame。

        Args:
            **kwargs: 透传给 fetch_all 的参数

        Returns:
            {city_code: DataFrame} 的字典
        """
        all_data = self.fetch_all(**kwargs)
        result: dict[str, pd.DataFrame] = {}

        for indicator, records in all_data.items():
            df = pd.DataFrame(records)
            if df.empty:
                continue
            city_col = "city" if "city" in df.columns else "city_code"
            if city_col not in df.columns:
                df[city_col] = "unknown"
            for city, group in df.groupby(city_col):
                group = group.copy()
                group["indicator"] = indicator
                if city not in result:
                    result[city] = group
                else:
                    result[city] = pd.concat([result[city], group], ignore_index=True)

        return result
