"""
全球城市注册表（Global City Registry）

管理 Urban Pulse 支持的全球城市元数据，提供按国家、区域、标签、名称等
维度的查询能力，为 Phase 2 全球城市扩展提供统一入口。
"""

from __future__ import annotations

import logging
from typing import Any

from backend.models.city import GlobalCity

logger = logging.getLogger(__name__)


# 内置全球主要城市示例数据
DEFAULT_GLOBAL_CITIES: list[dict[str, Any]] = [
    {
        "code": "new_york",
        "name": "纽约",
        "name_en": "New York",
        "country_code": "US",
        "country_name": "美国",
        "country_name_en": "United States",
        "region": "北美洲",
        "admin_level": "city",
        "population": 18_650_000,
        "gdp_usd": 2_000_000_000_000,
        "timezone": "America/New_York",
        "currency": "USD",
        "lat": 40.7128,
        "lon": -74.0060,
        "tags": ["global_finance_center", "us_tier1"],
        "aliases": ["NYC", "New York City", "纽约市"],
    },
    {
        "code": "london",
        "name": "伦敦",
        "name_en": "London",
        "country_code": "GB",
        "country_name": "英国",
        "country_name_en": "United Kingdom",
        "region": "欧洲",
        "admin_level": "city",
        "population": 8_950_000,
        "gdp_usd": 700_000_000_000,
        "timezone": "Europe/London",
        "currency": "GBP",
        "lat": 51.5074,
        "lon": -0.1278,
        "tags": ["global_finance_center", "europe_tier1"],
        "aliases": ["Greater London", "伦敦市"],
    },
    {
        "code": "tokyo",
        "name": "东京",
        "name_en": "Tokyo",
        "country_code": "JP",
        "country_name": "日本",
        "country_name_en": "Japan",
        "region": "亚洲",
        "admin_level": "metro",
        "population": 37_050_000,
        "gdp_usd": 1_750_000_000_000,
        "timezone": "Asia/Tokyo",
        "currency": "JPY",
        "lat": 35.6762,
        "lon": 139.6503,
        "tags": ["global_finance_center", "asia_tier1"],
        "aliases": ["Tokyo Metropolis", "東京都"],
    },
    {
        "code": "paris",
        "name": "巴黎",
        "name_en": "Paris",
        "country_code": "FR",
        "country_name": "法国",
        "country_name_en": "France",
        "region": "欧洲",
        "admin_level": "city",
        "population": 2_100_000,
        "gdp_usd": 700_000_000_000,
        "timezone": "Europe/Paris",
        "currency": "EUR",
        "lat": 48.8566,
        "lon": 2.3522,
        "tags": ["europe_tier1", "culture_center"],
        "aliases": ["Paris Region", "法兰西岛"],
    },
    {
        "code": "singapore",
        "name": "新加坡",
        "name_en": "Singapore",
        "country_code": "SG",
        "country_name": "新加坡",
        "country_name_en": "Singapore",
        "region": "亚洲",
        "admin_level": "country",
        "population": 5_900_000,
        "gdp_usd": 500_000_000_000,
        "timezone": "Asia/Singapore",
        "currency": "SGD",
        "lat": 1.3521,
        "lon": 103.8198,
        "tags": ["global_finance_center", "asia_tier1"],
        "aliases": ["SG", "狮城"],
    },
    {
        "code": "hong_kong",
        "name": "香港",
        "name_en": "Hong Kong",
        "country_code": "HK",
        "country_name": "中国香港",
        "country_name_en": "Hong Kong SAR",
        "region": "亚洲",
        "admin_level": "city",
        "population": 7_500_000,
        "gdp_usd": 400_000_000_000,
        "timezone": "Asia/Hong_Kong",
        "currency": "HKD",
        "lat": 22.3193,
        "lon": 114.1694,
        "tags": ["global_finance_center", "china_tier1"],
        "aliases": ["HK", "Hong Kong SAR", "中国香港"],
    },
    {
        "code": "shanghai",
        "name": "上海",
        "name_en": "Shanghai",
        "country_code": "CN",
        "country_name": "中国",
        "country_name_en": "China",
        "region": "亚洲",
        "admin_level": "city",
        "population": 24_650_000,
        "gdp_usd": 760_000_000_000,
        "timezone": "Asia/Shanghai",
        "currency": "CNY",
        "lat": 31.2304,
        "lon": 121.4737,
        "tags": ["global_finance_center", "china_tier1"],
        "aliases": ["SH", "魔都"],
    },
    {
        "code": "beijing",
        "name": "北京",
        "name_en": "Beijing",
        "country_code": "CN",
        "country_name": "中国",
        "country_name_en": "China",
        "region": "亚洲",
        "admin_level": "city",
        "population": 21_800_000,
        "gdp_usd": 650_000_000_000,
        "timezone": "Asia/Shanghai",
        "currency": "CNY",
        "lat": 39.9042,
        "lon": 116.4074,
        "tags": ["china_tier1", "political_center"],
        "aliases": ["BJ", "帝都"],
    },
    {
        "code": "shenzhen",
        "name": "深圳",
        "name_en": "Shenzhen",
        "country_code": "CN",
        "country_name": "中国",
        "country_name_en": "China",
        "region": "亚洲",
        "admin_level": "city",
        "population": 17_600_000,
        "gdp_usd": 510_000_000_000,
        "timezone": "Asia/Shanghai",
        "currency": "CNY",
        "lat": 22.5431,
        "lon": 114.0579,
        "tags": ["china_tier1", "tech_hub"],
        "aliases": ["SZ", "鹏城"],
    },
    {
        "code": "sydney",
        "name": "悉尼",
        "name_en": "Sydney",
        "country_code": "AU",
        "country_name": "澳大利亚",
        "country_name_en": "Australia",
        "region": "大洋洲",
        "admin_level": "city",
        "population": 5_300_000,
        "gdp_usd": 350_000_000_000,
        "timezone": "Australia/Sydney",
        "currency": "AUD",
        "lat": -33.8688,
        "lon": 151.2093,
        "tags": ["oceania_tier1"],
        "aliases": ["Sydney Region", "雪梨"],
    },
    {
        "code": "toronto",
        "name": "多伦多",
        "name_en": "Toronto",
        "country_code": "CA",
        "country_name": "加拿大",
        "country_name_en": "Canada",
        "region": "北美洲",
        "admin_level": "city",
        "population": 2_900_000,
        "gdp_usd": 400_000_000_000,
        "timezone": "America/Toronto",
        "currency": "CAD",
        "lat": 43.6510,
        "lon": -79.3470,
        "tags": ["north_america_tier1"],
        "aliases": ["Greater Toronto Area", "GTA"],
    },
    {
        "code": "berlin",
        "name": "柏林",
        "name_en": "Berlin",
        "country_code": "DE",
        "country_name": "德国",
        "country_name_en": "Germany",
        "region": "欧洲",
        "admin_level": "city",
        "population": 3_700_000,
        "gdp_usd": 200_000_000_000,
        "timezone": "Europe/Berlin",
        "currency": "EUR",
        "lat": 52.5200,
        "lon": 13.4050,
        "tags": ["europe_tier1"],
        "aliases": ["Berlin Region"],
    },
    {
        "code": "dubai",
        "name": "迪拜",
        "name_en": "Dubai",
        "country_code": "AE",
        "country_name": "阿联酋",
        "country_name_en": "United Arab Emirates",
        "region": "亚洲",
        "admin_level": "city",
        "population": 3_300_000,
        "gdp_usd": 120_000_000_000,
        "timezone": "Asia/Dubai",
        "currency": "AED",
        "lat": 25.2048,
        "lon": 55.2708,
        "tags": ["middle_east_hub"],
        "aliases": ["Dubai Emirate", "杜拜"],
    },
    {
        "code": "mumbai",
        "name": "孟买",
        "name_en": "Mumbai",
        "country_code": "IN",
        "country_name": "印度",
        "country_name_en": "India",
        "region": "亚洲",
        "admin_level": "city",
        "population": 20_400_000,
        "gdp_usd": 250_000_000_000,
        "timezone": "Asia/Kolkata",
        "currency": "INR",
        "lat": 19.0760,
        "lon": 72.8777,
        "tags": ["india_tier1", "finance_center"],
        "aliases": ["Bombay", "孟買"],
    },
    {
        "code": "sao_paulo",
        "name": "圣保罗",
        "name_en": "São Paulo",
        "country_code": "BR",
        "country_name": "巴西",
        "country_name_en": "Brazil",
        "region": "南美洲",
        "admin_level": "city",
        "population": 12_300_000,
        "gdp_usd": 280_000_000_000,
        "timezone": "America/Sao_Paulo",
        "currency": "BRL",
        "lat": -23.5505,
        "lon": -46.6333,
        "tags": ["south_america_tier1"],
        "aliases": ["Sampa", "圣保罗市"],
    },
]


class GlobalCityRegistry:
    """
    全球城市注册表

    - 维护 GlobalCity 实例集合
    - 支持按城市代码、中英文名称、别名、国家、区域、标签查询
    - 支持自定义加载器扩展
    """

    def __init__(self) -> None:
        self._cities: dict[str, GlobalCity] = {}

    # ------------------------------------------------------------------
    # 注册
    # ------------------------------------------------------------------
    def register(self, city: GlobalCity) -> bool:
        """注册一个城市。"""
        if city.code in self._cities:
            logger.warning(f"城市已存在: {city.code}")
            return False
        self._cities[city.code] = city
        logger.debug(f"城市注册成功: {city.display_name}")
        return True

    def register_many(self, cities: list[GlobalCity]) -> int:
        """批量注册，返回成功数量。"""
        return sum(1 for city in cities if self.register(city))

    def unregister(self, code: str) -> bool:
        """注销城市。"""
        if code not in self._cities:
            return False
        del self._cities[code]
        return True

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def get(self, code: str) -> GlobalCity | None:
        """按城市代码获取。"""
        return self._cities.get(code)

    def get_by_name(self, name: str) -> GlobalCity | None:
        """按中文名、英文名或别名获取（不区分大小写）。"""
        name_lower = name.lower()
        for city in self._cities.values():
            if city.name == name:
                return city
            if city.name_en.lower() == name_lower:
                return city
            if any(alias.lower() == name_lower for alias in city.aliases):
                return city
        return None

    def list_all(self) -> list[GlobalCity]:
        """返回所有城市，按代码排序。"""
        return sorted(self._cities.values(), key=lambda c: c.code)

    def list_by_country(self, country_code: str) -> list[GlobalCity]:
        """按 ISO 国家代码列出城市。"""
        return sorted(
            [c for c in self._cities.values() if c.country_code.upper() == country_code.upper()],
            key=lambda c: c.code,
        )

    def list_by_region(self, region: str) -> list[GlobalCity]:
        """按大洲/区域列出城市。"""
        return sorted(
            [c for c in self._cities.values() if c.region == region],
            key=lambda c: c.code,
        )

    def list_by_tag(self, tag: str) -> list[GlobalCity]:
        """按标签列出城市。"""
        return sorted(
            [c for c in self._cities.values() if tag in c.tags],
            key=lambda c: c.code,
        )

    def search(self, query: str) -> list[GlobalCity]:
        """
        模糊搜索城市。

        匹配范围包括：code、name、name_en、aliases、country_name、country_name_en。
        """
        query_lower = query.lower()
        results: list[GlobalCity] = []
        for city in self._cities.values():
            candidates = [
                city.code,
                city.name,
                city.name_en,
                city.country_name,
                city.country_name_en,
                city.region,
                *city.aliases,
                *city.tags,
            ]
            if any(query_lower in str(candidate).lower() for candidate in candidates):
                results.append(city)
        return sorted(results, key=lambda c: c.code)

    def list_country_codes(self) -> list[str]:
        """返回所有不重复的国家代码。"""
        return sorted({c.country_code.upper() for c in self._cities.values()})

    def list_regions(self) -> list[str]:
        """返回所有不重复的区域名称。"""
        return sorted({c.region for c in self._cities.values()})

    def list_tags(self) -> list[str]:
        """返回所有不重复的标签。"""
        return sorted({tag for c in self._cities.values() for tag in c.tags})

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------
    def summary(self) -> dict[str, Any]:
        """注册表统计摘要。"""
        by_region: dict[str, int] = {}
        by_country: dict[str, int] = {}
        for city in self._cities.values():
            by_region[city.region] = by_region.get(city.region, 0) + 1
            by_country[city.country_code.upper()] = by_country.get(city.country_code.upper(), 0) + 1
        return {
            "total": len(self._cities),
            "by_region": by_region,
            "by_country": by_country,
            "country_codes": self.list_country_codes(),
            "regions": self.list_regions(),
            "tags": self.list_tags(),
        }

    def to_dicts(self) -> list[dict[str, Any]]:
        """导出为字典列表。"""
        return [city.to_dict() for city in self.list_all()]


# 全局单例
_global_registry: GlobalCityRegistry | None = None


def get_global_city_registry() -> GlobalCityRegistry:
    """获取全局全球城市注册表（延迟初始化，加载默认城市）。"""
    global _global_registry
    if _global_registry is None:
        _global_registry = load_default_global_cities()
    return _global_registry


def load_default_global_cities() -> GlobalCityRegistry:
    """加载内置默认全球城市。"""
    registry = GlobalCityRegistry()
    for item in DEFAULT_GLOBAL_CITIES:
        try:
            registry.register(GlobalCity(**item))
        except Exception:
            logger.exception(f"加载默认城市失败: {item.get('code')}")
    return registry
