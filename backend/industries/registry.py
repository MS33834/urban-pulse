"""
产业注册表

按区域维护产业实体，支持查询、注册和按区域检索。
"""

from __future__ import annotations

import logging
from typing import Any

from backend.industries.models import Industry

logger = logging.getLogger(__name__)


class IndustryRegistry:
    """产业注册表"""

    def __init__(self) -> None:
        self._industries: dict[str, Industry] = {}

    def register(self, industry: Industry) -> bool:
        """注册一个产业"""
        key = f"{industry.region_code}:{industry.code}"
        if key in self._industries:
            logger.warning(f"产业已存在: {key}")
            return False
        self._industries[key] = industry
        logger.debug(f"产业注册成功: {industry.name} ({key})")
        return True

    def get(self, region_code: str, industry_code: str) -> Industry | None:
        """按区域编码和产业编码获取产业"""
        return self._industries.get(f"{region_code}:{industry_code}")

    def list_by_region(self, region_code: str) -> list[Industry]:
        """返回某区域下的所有产业"""
        return sorted(
            [i for i in self._industries.values() if i.region_code == region_code],
            key=lambda i: i.code,
        )

    def list_all(self) -> list[Industry]:
        """返回所有产业"""
        return sorted(self._industries.values(), key=lambda i: (i.region_code, i.code))

    def summary(self) -> dict[str, Any]:
        """返回注册表概览"""
        return {
            "total": len(self._industries),
            "by_region": {
                region: len(self.list_by_region(region))
                for region in sorted({i.region_code for i in self._industries.values()})
            },
        }


_INDUSTRY_REGISTRY: IndustryRegistry | None = None


def get_industry_registry() -> IndustryRegistry:
    """全局产业注册表单例"""
    global _INDUSTRY_REGISTRY
    if _INDUSTRY_REGISTRY is None:
        _INDUSTRY_REGISTRY = IndustryRegistry()
    return _INDUSTRY_REGISTRY
