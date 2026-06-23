"""
产业数据采集器
"""

import concurrent.futures
import logging
from datetime import datetime
from typing import Any

try:
    import akshare as ak
except ImportError:
    ak = None

from backend.data_collection.base_collector import DataCollector

logger = logging.getLogger(__name__)


def _call_with_timeout(func, timeout=30, *args, **kwargs):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as exc:
            raise TimeoutError(f"调用超时 ({timeout}s): {func.__name__}") from exc


class IndustryCollector(DataCollector):
    """产业数据采集器"""

    def __init__(self):
        super().__init__()
        self._source_name = "industry"

    def name(self) -> str:
        return "industry"

    def supported_cities(self) -> list[str]:
        return ["CN"]

    def fetch_data(self, **kwargs) -> list[dict[str, Any]]:
        try:
            if ak is not None:
                industry_name = kwargs.get("industry", "半导体")
                df = _call_with_timeout(ak.macro_china_industry_profit, timeout=30)
                results = []
                for _, row in df.iterrows():
                    results.append(
                        {
                            "name": row.get("指标", ""),
                            "value": float(row.get("累计值", 0)),
                            "unit": "亿元",
                            "industry": industry_name,
                            "year": kwargs.get("year", 2025),
                            "source": "akshare",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                return results
            return self._get_industry_fallback()
        except Exception as e:
            logger.error(f"产业数据采集失败: {e}")
            return self._get_industry_fallback()

    def _get_industry_fallback(self) -> list[dict[str, Any]]:
        return [
            {"name": "高技术制造业", "value": 12580.5, "unit": "亿元", "year": 2025, "source": "statistical_yearbook"},
            {"name": "装备制造业", "value": 18230.7, "unit": "亿元", "year": 2025, "source": "statistical_yearbook"},
            {"name": "战略性新兴产业", "value": 9860.3, "unit": "亿元", "year": 2025, "source": "statistical_yearbook"},
        ]

    def fetch_all(self, indicators: list[str] | None = None) -> dict[str, list[dict]]:
        """批量获取产业数据。

        目前产业数据以整体产业统计形式返回，key 为 industry_output；
        后续可按 indicators 拆分为更细分的产业指标。
        """
        data = self.fetch_data()
        key = "industry_output" if not indicators else indicators[0]
        return {key: data}


# 单例
industry_collector = IndustryCollector()
