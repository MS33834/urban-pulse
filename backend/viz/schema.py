"""
通用可视化配置协议（Viz Config Protocol, VCP）

目标：让后端用统一的数据结构描述「画什么图、用什么数据、如何编码、支持哪些交互」，
前端只负责按协议渲染，不感知业务语义。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ChartType(str, Enum):
    """支持的图表类型"""

    LINE = "line"
    BAR = "bar"
    SCATTER = "scatter"
    PIE = "pie"
    RADAR = "radar"
    HEATMAP = "heatmap"
    MAP = "map"
    SANKEY = "sankey"
    BOX = "box"
    RACING_BAR = "racing_bar"
    GAUGE = "gauge"
    AREA = "area"
    SCATTER_MATRIX = "scatter_matrix"


class DataSource(BaseModel):
    """数据源定义"""

    dataset_id: str | None = Field(None, description="数据集 ID，用于从 records 表读取")
    data: list[dict[str, Any]] | None = Field(None, description="内联数据，优先级高于 dataset_id")
    entity_field: str | None = Field(None, description="实体字段名，如 city")
    time_field: str | None = Field(None, description="时间字段名，如 year")
    value_fields: list[str] = Field(default_factory=list, description="数值字段列表")
    category_field: str | None = Field(None, description="分类字段名，如 region")


class Encoding(BaseModel):
    """视觉编码定义"""

    x: str | None = Field(None, description="X 轴字段")
    y: str | None = Field(None, description="Y 轴字段")
    color: str | None = Field(None, description="颜色分组字段")
    size: str | None = Field(None, description="大小编码字段")
    shape: str | None = Field(None, description="形状编码字段")
    facet: str | None = Field(None, description="分面字段")
    theta: str | None = Field(None, description="饼图角度字段")
    radius: str | None = Field(None, description="雷达图半径字段")


class Interaction(BaseModel):
    """交互能力开关"""

    zoom: bool = True
    brush: bool = False
    tooltip: bool = True
    legend_toggle: bool = True
    drilldown: bool = False
    datazoom: bool = True
    animation: bool = True
    toolbox: bool = True


class Style(BaseModel):
    """样式配置"""

    theme: str = "urban_pulse"
    height: int = 480
    width: int | None = None
    color_palette: list[str] | None = None
    background_color: str | None = None
    title_font_size: int = 18
    label_font_size: int = 12


class ChartConfig(BaseModel):
    """通用图表配置协议"""

    version: str = "1.0"
    chart_type: ChartType
    title: str = ""
    subtitle: str = ""
    data_source: DataSource
    encoding: Encoding = Field(default_factory=Encoding)
    interaction: Interaction = Field(default_factory=Interaction)
    style: Style = Field(default_factory=Style)
    extra: dict[str, Any] = Field(default_factory=dict, description="图表类型专有配置")

    @model_validator(mode="after")
    def check_required_encoding(self) -> "ChartConfig":
        ct = self.chart_type
        enc = self.encoding
        if ct in (ChartType.LINE, ChartType.BAR, ChartType.SCATTER, ChartType.AREA):
            if not enc.x or not enc.y:
                raise ValueError(f"{ct.value} 图必须指定 encoding.x 和 encoding.y")
        if ct == ChartType.RADAR and (not self.data_source.value_fields or len(self.data_source.value_fields) < 3):
            raise ValueError("雷达图至少需要 3 个数值指标（value_fields）")
        if ct == ChartType.PIE and not enc.theta:
            raise ValueError("饼图必须指定 encoding.theta")
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
