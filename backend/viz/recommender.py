"""
图表推荐器

根据数据画像自动推荐合适的图表类型与视觉编码。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.viz.profiler import DataProfile
from backend.viz.schema import ChartType, ChartConfig, DataSource, Encoding


@dataclass
class ChartRecommendation:
    """单个图表推荐"""

    chart_type: str
    title: str
    description: str
    score: float  # 0-1，匹配度
    config: ChartConfig
    reason: str


def _build_config(
    chart_type: ChartType,
    profile: DataProfile,
    numeric_field: str | None = None,
    title: str = "",
    reason: str = "",
    extra: dict[str, Any] | None = None,
) -> ChartRecommendation:
    """根据画像构建一个 ChartConfig"""

    encoding = Encoding()
    if profile.time_field:
        encoding.x = profile.time_field
    if profile.entity_field:
        encoding.color = profile.entity_field

    if chart_type in (ChartType.LINE, ChartType.AREA):
        encoding.y = numeric_field or (profile.numeric_fields[0] if profile.numeric_fields else None)
    elif chart_type == ChartType.BAR:
        encoding.x = profile.entity_field or (profile.category_fields[0] if profile.category_fields else encoding.x)
        encoding.y = numeric_field or (profile.numeric_fields[0] if profile.numeric_fields else None)
    elif chart_type == ChartType.SCATTER:
        if len(profile.numeric_fields) >= 2:
            encoding.x = profile.numeric_fields[0]
            encoding.y = profile.numeric_fields[1]
            if len(profile.numeric_fields) >= 3:
                encoding.size = profile.numeric_fields[2]
        else:
            encoding.y = numeric_field
    elif chart_type == ChartType.RADAR:
        encoding.radius = numeric_field
    elif chart_type == ChartType.HEATMAP:
        encoding.x = profile.entity_field or (profile.category_fields[0] if profile.category_fields else None)
        encoding.y = profile.time_field or "metric"
    elif chart_type == ChartType.BOX:
        encoding.x = profile.category_fields[0] if profile.category_fields else profile.entity_field
        encoding.y = numeric_field
    elif chart_type == ChartType.GAUGE:
        encoding.y = numeric_field

    return ChartRecommendation(
        chart_type=chart_type.value,
        title=title,
        description=reason,
        score=0.8,
        config=ChartConfig(
            chart_type=chart_type,
            title=title,
            data_source=DataSource(
                entity_field=profile.entity_field,
                time_field=profile.time_field,
                value_fields=profile.numeric_fields,
            ),
            encoding=encoding,
            extra=extra or {},
        ),
        reason=reason,
    )


def recommend_charts(profile: DataProfile, data: list[dict[str, Any]] | None = None) -> list[ChartRecommendation]:
    """
    根据数据画像推荐图表。

    Args:
        profile: 数据集画像
        data: 原始数据（可选，用于更精确的推荐）

    Returns:
        推荐列表，按匹配度排序
    """
    recommendations: list[ChartRecommendation] = []

    has_time = profile.has_time_dim and profile.time_field is not None
    has_entity = profile.entity_field is not None
    num_numeric = len(profile.numeric_fields)

    # 时间序列推荐
    if has_time and num_numeric > 0:
        for field in profile.numeric_fields[:3]:
            recommendations.append(
                _build_config(
                    ChartType.LINE,
                    profile,
                    numeric_field=field,
                    title=f"{field} 时间序列趋势",
                    reason="数据集包含时间维度与数值指标，适合观察趋势",
                )
            )
            if has_entity:
                recommendations.append(
                    _build_config(
                        ChartType.AREA,
                        profile,
                        numeric_field=field,
                        title=f"{field} 堆叠面积趋势",
                        reason="多实体时间序列适合堆叠面积图",
                        extra={"stack": True},
                    )
                )

    # 多实体对比
    if has_entity and num_numeric > 0:
        for field in profile.numeric_fields[:2]:
            recommendations.append(
                _build_config(
                    ChartType.BAR,
                    profile,
                    numeric_field=field,
                    title=f"各实体 {field} 对比",
                    reason="分类实体 + 数值指标，适合柱状图对比",
                )
            )

    # 多指标关系
    if num_numeric >= 2:
        recommendations.append(
            _build_config(
                ChartType.SCATTER,
                profile,
                title=f"{profile.numeric_fields[0]} vs {profile.numeric_fields[1]}",
                reason="多个数值指标适合散点图观察相关关系",
            )
        )

    # 雷达图：多维度单实体或多实体对比
    if num_numeric >= 3 and has_entity:
        recommendations.append(
            _build_config(
                ChartType.RADAR,
                profile,
                title="多维度城市画像",
                reason="3 个以上数值指标可用雷达图做多维对比",
            )
        )

    # 热力图：实体 × 时间 / 实体 × 指标
    if has_entity and (has_time or num_numeric > 1):
        recommendations.append(
            _build_config(
                ChartType.HEATMAP,
                profile,
                title="指标热力分布",
                reason="实体 × 时间/指标矩阵适合热力图",
            )
        )

    # 箱线图：观察分布
    if num_numeric > 0 and (profile.category_fields or has_entity):
        recommendations.append(
            _build_config(
                ChartType.BOX,
                profile,
                numeric_field=profile.numeric_fields[0],
                title=f"{profile.numeric_fields[0]} 分布",
                reason="有分类维度时可用箱线图观察分布与异常",
            )
        )

    # 仪表盘：单指标总览
    if num_numeric > 0:
        recommendations.append(
            _build_config(
                ChartType.GAUGE,
                profile,
                numeric_field=profile.numeric_fields[0],
                title=f"{profile.numeric_fields[0]} 仪表盘",
                reason="单一关键指标可用仪表盘突出显示",
            )
        )

    # 地图：有经纬度字段时推荐
    has_longitude = any("lon" in f.name.lower() or "经度" in f.name for f in profile.fields)
    has_latitude = any("lat" in f.name.lower() or "纬度" in f.name for f in profile.fields)
    if has_longitude and has_latitude and num_numeric > 0:
        recommendations.append(
            _build_config(
                ChartType.MAP,
                profile,
                numeric_field=profile.numeric_fields[0],
                title="地理分布图",
                reason="数据包含经纬度字段，可在地图上展示空间分布",
            )
        )

    # 桑基图：有 source/target/value 字段时推荐
    has_source = any(f.name.lower() in {"source", "from", "来源"} for f in profile.fields)
    has_target = any(f.name.lower() in {"target", "to", "去向"} for f in profile.fields)
    if has_source and has_target and num_numeric > 0:
        recommendations.append(
            _build_config(
                ChartType.SANKEY,
                profile,
                title="流向桑基图",
                reason="数据包含 source/target 字段，适合桑基图展示流向",
            )
        )

    # 赛跑图：时间 + 实体 + 数值
    if has_time and has_entity and num_numeric > 0:
        recommendations.append(
            _build_config(
                ChartType.RACING_BAR,
                profile,
                numeric_field=profile.numeric_fields[0],
                title=f"{profile.numeric_fields[0]} 排名变化",
                reason="时间序列的多实体排名变化适合赛跑图",
            )
        )

    # 去重并按匹配度简单排序
    seen = set()
    unique_recs = []
    for rec in recommendations:
        key = (rec.chart_type, rec.title)
        if key not in seen:
            seen.add(key)
            unique_recs.append(rec)

    # 时间序列优先
    unique_recs.sort(key=lambda r: (r.chart_type != "line", -r.score))
    return unique_recs
