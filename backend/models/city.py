"""
全球城市数据模型（Global City Schema）

定义 Urban Pulse 支持的城市标准字段，为 Phase 2 全球城市扩展提供统一数据结构。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GlobalCity(BaseModel):
    """全球城市标准模型。"""

    code: str = Field(..., description="城市唯一代码，例如 new_york, shanghai")
    name: str = Field(..., description="城市中文名")
    name_en: str = Field(..., description="城市英文名")
    country_code: str = Field(..., description="ISO 3166-1 alpha-2 国家代码，例如 US, CN")
    country_name: str = Field(..., description="国家中文名")
    country_name_en: str = Field(..., description="国家英文名")
    region: str = Field(..., description="大洲/区域，例如 亚洲、北美洲")
    admin_level: str = Field(default="city", description="行政级别：city / metro / province")
    population: int | None = Field(default=None, description="人口数量")
    gdp_usd: float | None = Field(default=None, description="GDP（美元）")
    timezone: str | None = Field(default=None, description="时区")
    currency: str | None = Field(default=None, description="货币代码，例如 USD, CNY")
    lat: float | None = Field(default=None, description="纬度")
    lon: float | None = Field(default=None, description="经度")
    tags: list[str] = Field(default_factory=list, description="标签，例如 ['global_finance_center']")
    aliases: list[str] = Field(default_factory=list, description="别名，用于查询匹配")

    class Config:
        frozen = True

    def to_dict(self) -> dict:
        """返回字典形式，便于序列化。"""
        return self.model_dump()

    @property
    def display_name(self) -> str:
        """返回展示名称。"""
        return f"{self.name} ({self.name_en})"
