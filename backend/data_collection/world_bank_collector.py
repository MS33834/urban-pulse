"""
世界银行数据采集器（插件示例）

支持通过世界银行开放 API 获取国家层面宏观经济指标，
并按主要全球城市进行映射，作为 Urban Pulse 全球城市扩展的示例插件。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests

from backend.data_collection.base_collector import DataCollector

logger = logging.getLogger(__name__)

# 城市 -> 国家代码映射（用于从世界银行国家指标映射到城市）
CITY_COUNTRY_MAP: dict[str, str] = {
    "new_york": "US",
    "london": "GB",
    "tokyo": "JP",
    "paris": "FR",
    "singapore": "SG",
    "hong_kong": "HK",
    "shanghai": "CN",
    "beijing": "CN",
    "shenzhen": "CN",
    "sydney": "AU",
    "toronto": "CA",
    "berlin": "DE",
    "dubai": "AE",
    "mumbai": "IN",
    "sao_paulo": "BR",
}

# 世界银行指标代码 -> Urban Pulse 指标代码
INDICATORS: dict[str, str] = {
    "NY.GDP.MKTP.CD": "gdp_current_usd",
    "NY.GDP.PCAP.CD": "gdp_per_capita_usd",
    "SP.POP.TOTL": "population",
    "FP.CPI.TOTL.ZG": "cpi_yoy_pct",
    "SL.UEM.TOTL.ZS": "unemployment_rate",
}

FALLBACK_YEARS = [2021, 2022, 2023, 2024]

# 当世界银行 API 不可用时使用的回退数据（近似值，仅用于演示）
FALLBACK_DATA: dict[str, dict[str, dict[str, float]]] = {
    "new_york": {
        "gdp_current_usd": {
            2021: 1_700_000_000_000,
            2022: 1_800_000_000_000,
            2023: 1_900_000_000_000,
            2024: 2_000_000_000_000,
        },
        "gdp_per_capita_usd": {2021: 90_000, 2022: 95_000, 2023: 98_000, 2024: 102_000},
        "population": {2021: 18_900_000, 2022: 18_800_000, 2023: 18_700_000, 2024: 18_650_000},
        "cpi_yoy_pct": {2021: 4.7, 2022: 8.0, 2023: 4.1, 2024: 3.4},
        "unemployment_rate": {2021: 8.5, 2022: 7.2, 2023: 6.8, 2024: 6.5},
    },
    "london": {
        "gdp_current_usd": {2021: 600_000_000_000, 2022: 650_000_000_000, 2023: 680_000_000_000, 2024: 700_000_000_000},
        "gdp_per_capita_usd": {2021: 68_000, 2022: 72_000, 2023: 75_000, 2024: 77_000},
        "population": {2021: 8_800_000, 2022: 8_850_000, 2023: 8_900_000, 2024: 8_950_000},
        "cpi_yoy_pct": {2021: 2.6, 2022: 9.1, 2023: 7.3, 2024: 3.0},
        "unemployment_rate": {2021: 4.5, 2022: 3.7, 2023: 4.0, 2024: 4.2},
    },
    "tokyo": {
        "gdp_current_usd": {
            2021: 1_600_000_000_000,
            2022: 1_550_000_000_000,
            2023: 1_700_000_000_000,
            2024: 1_750_000_000_000,
        },
        "gdp_per_capita_usd": {2021: 45_000, 2022: 44_000, 2023: 48_000, 2024: 49_000},
        "population": {2021: 37_300_000, 2022: 37_200_000, 2023: 37_100_000, 2024: 37_050_000},
        "cpi_yoy_pct": {2021: -0.2, 2022: 2.5, 2023: 3.3, 2024: 2.8},
        "unemployment_rate": {2021: 2.8, 2022: 2.6, 2023: 2.6, 2024: 2.5},
    },
    "shanghai": {
        "gdp_current_usd": {2021: 650_000_000_000, 2022: 680_000_000_000, 2023: 720_000_000_000, 2024: 760_000_000_000},
        "gdp_per_capita_usd": {2021: 26_000, 2022: 27_000, 2023: 28_500, 2024: 30_000},
        "population": {2021: 24_900_000, 2022: 24_800_000, 2023: 24_700_000, 2024: 24_650_000},
        "cpi_yoy_pct": {2021: 1.2, 2022: 2.0, 2023: 0.3, 2024: 0.5},
        "unemployment_rate": {2021: 3.5, 2022: 4.2, 2023: 4.5, 2024: 4.3},
    },
}


class WorldBankCollector(DataCollector):
    """世界银行数据采集器插件示例。"""

    def __init__(self, use_api: bool = True):
        super().__init__()
        self.source_name = "world_bank"
        self.use_api = use_api

    def name(self) -> str:
        return "world_bank"

    def supported_cities(self) -> list[str]:
        return list(CITY_COUNTRY_MAP.keys())

    def fetch_data(self, **kwargs) -> list[dict[str, Any]]:
        """采集指定城市的全部指标数据。"""
        city = kwargs.get("city", "new_york")
        if city not in CITY_COUNTRY_MAP:
            logger.warning(f"World Bank 采集器不支持城市: {city}")
            return []

        records: list[dict[str, Any]] = []
        for wb_code, indicator in INDICATORS.items():
            try:
                records.extend(self._fetch_indicator(city, wb_code, indicator))
            except Exception as exc:
                logger.warning(f"获取 {city}/{indicator} 失败: {exc}")

        return records

    def _fetch_indicator(self, city: str, wb_code: str, indicator: str) -> list[dict[str, Any]]:
        country_code = CITY_COUNTRY_MAP[city]
        records: list[dict[str, Any]] = []

        if self.use_api:
            try:
                url = (
                    f"https://api.worldbank.org/v2/country/{country_code}/"
                    f"indicator/{wb_code}?format=json&per_page=50&date=2020:2024"
                )
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                data = response.json()

                # 世界银行 API 返回 [[page_info], [data]] 或 [data]
                items = data[1] if isinstance(data, list) and len(data) > 1 else data
                for item in items:
                    value = item.get("value")
                    year = item.get("date")
                    if value is None or year is None:
                        continue
                    records.append(self._build_record(city, indicator, int(year), float(value)))
                if records:
                    return records
            except Exception as exc:
                logger.warning(f"世界银行 API 请求失败，使用回退数据: {exc}")

        # 回退到本地静态数据
        city_data = FALLBACK_DATA.get(city, {})
        indicator_data = city_data.get(indicator, {})
        for year, value in indicator_data.items():
            records.append(self._build_record(city, indicator, year, value))
        return records

    def _build_record(self, city: str, indicator: str, year: int, value: float) -> dict[str, Any]:
        return {
            "city_code": city,
            "city": city.replace("_", " ").title(),
            "indicator": indicator,
            "value": value,
            "year": year,
            "source": "world_bank",
            "timestamp": datetime.now().isoformat(),
        }

    def fetch_all(self, indicators: list[str] | None = None) -> dict[str, list[dict]]:
        """批量采集所有支持城市的数据。"""
        all_data: dict[str, list[dict]] = {}
        target_cities = list(CITY_COUNTRY_MAP.keys())

        for city in target_cities:
            records = self.fetch_data(city=city)
            if records:
                all_data[city] = records

        return all_data


# 单例
world_bank_collector = WorldBankCollector()
