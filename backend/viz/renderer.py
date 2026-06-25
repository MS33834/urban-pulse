"""
ECharts option 渲染器

将通用图表配置协议（ChartConfig）转换为 ECharts 可用的 option 对象。
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.viz.schema import ChartConfig, ChartType

# Urban Pulse 主题色板
DEFAULT_PALETTE = [
    "#0E1F3F",
    "#B8714A",
    "#2D6A4F",
    "#D4A373",
    "#1D3557",
    "#E9C46A",
    "#264653",
    "#E76F51",
    "#2A9D8F",
    "#F4A261",
]


def _get_palette(config: ChartConfig) -> list[str]:
    return config.style.color_palette or DEFAULT_PALETTE


def _base_option(config: ChartConfig) -> dict[str, Any]:
    """生成基础 option"""
    opt: dict[str, Any] = {
        "title": {
            "text": config.title,
            "subtext": config.subtitle,
            "left": "center",
            "textStyle": {"fontSize": config.style.title_font_size},
        },
        "tooltip": {"trigger": "axis" if config.interaction.tooltip else "none"},
        "legend": {"bottom": 0, "show": config.interaction.legend_toggle},
        "color": _get_palette(config),
        "animation": config.interaction.animation,
    }
    if config.interaction.toolbox:
        opt["toolbox"] = {
            "feature": {
                "saveAsImage": {"title": "保存"},
                "dataZoom": {"title": {"zoom": "缩放", "back": "还原"}} if config.interaction.datazoom else None,
                "restore": {"title": "还原"},
            }
        }
    return opt


def _group_by(data: list[dict[str, Any]], field: str) -> dict[Any, list[dict[str, Any]]]:
    groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in data:
        key = row.get(field, "未知")
        groups[key].append(row)
    return dict(groups)


def _to_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def render_line_or_area(config: ChartConfig, data: list[dict[str, Any]]) -> dict[str, Any]:
    x_field = config.encoding.x
    y_field = config.encoding.y
    color_field = config.encoding.color
    if not x_field or not y_field:
        raise ValueError("折线图需要 encoding.x 和 encoding.y")

    opt = _base_option(config)
    is_area = config.chart_type == ChartType.AREA

    # 收集所有 X 轴值并排序
    x_values = sorted({str(row.get(x_field, "")) for row in data if row.get(x_field) is not None})
    opt["xAxis"] = {"type": "category", "data": x_values, "boundaryGap": not is_area}
    opt["yAxis"] = {"type": "value"}

    series = []
    if color_field:
        groups = _group_by(data, color_field)
        for name, group in groups.items():
            value_map = {str(row.get(x_field)): _to_number(row.get(y_field)) for row in group}
            series.append(
                {
                    "name": str(name),
                    "type": "line",
                    "data": [value_map.get(xv) for xv in x_values],
                    "smooth": True,
                    "areaStyle": {"opacity": 0.2} if is_area else None,
                    "stack": "total" if is_area and config.extra.get("stack") else None,
                }
            )
    else:
        value_map = {str(row.get(x_field)): _to_number(row.get(y_field)) for row in data}
        series.append(
            {
                "type": "line",
                "data": [value_map.get(xv) for xv in x_values],
                "smooth": True,
                "areaStyle": {"opacity": 0.2} if is_area else None,
            }
        )

    opt["series"] = series
    if config.interaction.datazoom:
        opt["dataZoom"] = [{"type": "inside"}, {"type": "slider", "bottom": 40}]
    return opt


def render_bar(config: ChartConfig, data: list[dict[str, Any]]) -> dict[str, Any]:
    x_field = config.encoding.x
    y_field = config.encoding.y
    color_field = config.encoding.color
    if not x_field or not y_field:
        raise ValueError("柱状图需要 encoding.x 和 encoding.y")

    opt = _base_option(config)
    opt["xAxis"] = {"type": "category", "data": [], "axisLabel": {"rotate": 45}}
    opt["yAxis"] = {"type": "value"}

    if color_field:
        groups = _group_by(data, color_field)
        x_values = sorted({str(row.get(x_field, "")) for row in data if row.get(x_field) is not None})
        opt["xAxis"]["data"] = x_values
        series = []
        for name, group in groups.items():
            value_map = {str(row.get(x_field)): _to_number(row.get(y_field)) for row in group}
            series.append(
                {
                    "name": str(name),
                    "type": "bar",
                    "data": [value_map.get(xv) for xv in x_values],
                }
            )
        opt["series"] = series
    else:
        sorted_data = sorted(data, key=lambda r: _to_number(r.get(y_field)) or 0, reverse=True)
        x_values = [str(row.get(x_field, "")) for row in sorted_data]
        values = [_to_number(row.get(y_field)) for row in sorted_data]
        opt["xAxis"]["data"] = x_values
        opt["series"] = [{"type": "bar", "data": values, "itemStyle": {"borderRadius": [4, 4, 0, 0]}}]

    return opt


def render_scatter(config: ChartConfig, data: list[dict[str, Any]]) -> dict[str, Any]:
    x_field = config.encoding.x
    y_field = config.encoding.y
    size_field = config.encoding.size
    color_field = config.encoding.color
    if not x_field or not y_field:
        raise ValueError("散点图需要 encoding.x 和 encoding.y")

    opt = _base_option(config)
    opt["xAxis"] = {"type": "value", "name": x_field}
    opt["yAxis"] = {"type": "value", "name": y_field}

    series_data = []
    for row in data:
        x = _to_number(row.get(x_field))
        y = _to_number(row.get(y_field))
        if x is None or y is None:
            continue
        item: list[Any] = [x, y]
        if size_field:
            item.append(_to_number(row.get(size_field)) or 5)
        item.append({
            "name": str(row.get(color_field, row.get(config.data_source.entity_field, "") or "")),
        })
        series_data.append(item)

    series = {
        "type": "scatter",
        "data": series_data,
        "symbolSize": lambda val, params: val[2] if len(val) > 2 and isinstance(val[2], (int, float)) else 10,
    }
    opt["series"] = [series]
    return opt


def render_radar(config: ChartConfig, data: list[dict[str, Any]]) -> dict[str, Any]:
    numeric_fields = config.data_source.value_fields or []
    if len(numeric_fields) < 3:
        raise ValueError("雷达图至少需要 3 个数值指标")

    entity_field = config.data_source.entity_field
    color_field = config.encoding.color or entity_field

    opt = _base_option(config)
    max_values = {}
    for field in numeric_fields:
        vals = [_to_number(row.get(field)) for row in data]
        vals = [v for v in vals if v is not None]
        max_values[field] = max(vals) * 1.1 if vals else 100

    opt["radar"] = {
        "indicator": [{"name": f, "max": max_values.get(f, 100)} for f in numeric_fields],
        "shape": "circle",
    }

    series_data = []
    if color_field:
        groups = _group_by(data, color_field)
        for name, group in groups.items():
            row = group[0]
            values = [_to_number(row.get(f)) or 0 for f in numeric_fields]
            series_data.append({"value": values, "name": str(name)})
    else:
        row = data[0]
        values = [_to_number(row.get(f)) or 0 for f in numeric_fields]
        series_data.append({"value": values, "name": "整体"})

    opt["series"] = [{"type": "radar", "data": series_data}]
    return opt


def render_heatmap(config: ChartConfig, data: list[dict[str, Any]]) -> dict[str, Any]:
    x_field = config.encoding.x or config.data_source.entity_field
    y_field = config.encoding.y or config.data_source.time_field
    value_field = config.data_source.value_fields[0] if config.data_source.value_fields else None
    if not x_field or not y_field or not value_field:
        raise ValueError("热力图需要 encoding.x, encoding.y 和 value_fields")

    x_values = sorted({str(row.get(x_field, "")) for row in data if row.get(x_field) is not None})
    y_values = sorted({str(row.get(y_field, "")) for row in data if row.get(y_field) is not None})

    value_map = {}
    for row in data:
        key = (str(row.get(x_field, "")), str(row.get(y_field, "")))
        value_map[key] = _to_number(row.get(value_field))

    heatmap_data = []
    for yi, yv in enumerate(y_values):
        for xi, xv in enumerate(x_values):
            heatmap_data.append([xi, yi, value_map.get((xv, yv))])

    opt = _base_option(config)
    opt["tooltip"] = {"position": "top"}
    opt["grid"] = {"height": "70%", "top": "10%"}
    opt["xAxis"] = {"type": "category", "data": x_values, "splitArea": {"show": True}}
    opt["yAxis"] = {"type": "category", "data": y_values, "splitArea": {"show": True}}
    opt["visualMap"] = {"min": 0, "max": max((v[2] for v in heatmap_data if v[2] is not None), default=100), "calculable": True, "orient": "horizontal", "left": "center", "bottom": "5%"}
    opt["series"] = [{"name": value_field, "type": "heatmap", "data": heatmap_data, "label": {"show": True}, "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0, 0, 0, 0.5)"}}}]
    return opt


def render_box(config: ChartConfig, data: list[dict[str, Any]]) -> dict[str, Any]:
    x_field = config.encoding.x or config.data_source.category_fields[0] if config.data_source.category_fields else None
    y_field = config.encoding.y
    if not x_field or not y_field:
        raise ValueError("箱线图需要 encoding.x 和 encoding.y")

    groups = _group_by(data, x_field)
    x_values = sorted(groups.keys())
    series_data = []
    for xv in x_values:
        values = sorted([_to_number(row.get(y_field)) for row in groups[xv] if _to_number(row.get(y_field)) is not None])
        series_data.append(values)

    opt = _base_option(config)
    opt["xAxis"] = {"type": "category", "data": x_values}
    opt["yAxis"] = {"type": "value"}
    opt["series"] = [{"type": "boxplot", "data": series_data}]
    return opt


def render_gauge(config: ChartConfig, data: list[dict[str, Any]]) -> dict[str, Any]:
    y_field = config.encoding.y
    if not y_field:
        raise ValueError("仪表盘需要 encoding.y")

    values = [_to_number(row.get(y_field)) for row in data]
    values = [v for v in values if v is not None]
    if not values:
        raise ValueError("没有有效的数值")

    value = sum(values) / len(values)
    max_val = max(values) * 1.2

    opt = _base_option(config)
    opt["series"] = [
        {
            "type": "gauge",
            "startAngle": 180,
            "endAngle": 0,
            "min": 0,
            "max": max_val,
            "splitNumber": 5,
            "axisLine": {"lineStyle": {"width": 8, "color": [[0.3, "#67e8f9"], [0.7, "#37a2da"], [1, "#fd666d"]]}},
            "pointer": {"icon": "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z", "length": "12%", "width": 20, "offsetCenter": [0, "-60%"], "itemStyle": {"color": "auto"}},
            "axisTick": {"length": 12, "lineStyle": {"color": "auto", "width": 2}},
            "splitLine": {"length": 20, "lineStyle": {"color": "auto", "width": 5}},
            "axisLabel": {"color": "#464646", "fontSize": 14, "distance": -60},
            "title": {"offsetCenter": [0, "-20%"], "fontSize": 20},
            "detail": {"fontSize": 30, "offsetCenter": [0, "0%"], "valueAnimation": True, "formatter": "{value}", "color": "auto"},
            "data": [{"value": round(value, 2), "name": y_field}],
        }
    ]
    return opt


def render_echarts_option(config: ChartConfig, data: list[dict[str, Any]]) -> dict[str, Any]:
    """
    根据配置渲染 ECharts option。
    """
    renderers = {
        ChartType.LINE: render_line_or_area,
        ChartType.AREA: render_line_or_area,
        ChartType.BAR: render_bar,
        ChartType.SCATTER: render_scatter,
        ChartType.RADAR: render_radar,
        ChartType.HEATMAP: render_heatmap,
        ChartType.BOX: render_box,
        ChartType.GAUGE: render_gauge,
    }
    renderer = renderers.get(config.chart_type)
    if renderer is None:
        raise ValueError(f"暂不支持的图表类型: {config.chart_type.value}")
    return renderer(config, data)
