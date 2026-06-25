"""
通用可视化 API

- POST /api/v1/viz/profile   : 数据集画像
- POST /api/v1/viz/recommend : 图表推荐
- POST /api/v1/viz/render    : 根据配置预渲染 ECharts option
- POST /api/v1/viz/auto      : 上传数据 → 自动推荐 + 渲染
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.viz import profile_dataset, recommend_charts
from backend.viz.renderer import render_echarts_option
from backend.viz.schema import ChartConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/viz", tags=["可视化"])


class DataInput(BaseModel):
    """数据输入"""

    data: list[dict[str, Any]] = Field(..., min_length=1, description="数据行列表")
    title: str = ""


class RenderRequest(BaseModel):
    """渲染请求"""

    config: ChartConfig
    data: list[dict[str, Any]] = Field(..., min_length=1, description="数据行列表")


class AutoVizRequest(BaseModel):
    """自动可视化请求"""

    data: list[dict[str, Any]] = Field(..., min_length=1, description="数据行列表")
    max_charts: int = Field(3, ge=1, le=10, description="返回图表数量")


@router.post("/profile", summary="数据集画像")
async def viz_profile(body: DataInput) -> dict[str, Any]:
    """分析数据集结构，返回字段类型、时间维度、实体维度、数值指标等。"""
    try:
        profile = profile_dataset(body.data)
        return {
            "success": True,
            "profile": {
                "total_rows": profile.total_rows,
                "total_cols": profile.total_cols,
                "has_time_dim": profile.has_time_dim,
                "time_field": profile.time_field,
                "entity_field": profile.entity_field,
                "numeric_fields": profile.numeric_fields,
                "category_fields": profile.category_fields,
                "text_fields": profile.text_fields,
                "fields": [
                    {
                        "name": f.name,
                        "data_type": f.data_type,
                        "non_null_count": f.non_null_count,
                        "unique_count": f.unique_count,
                        "min_value": f.min_value,
                        "max_value": f.max_value,
                        "sample_values": f.sample_values,
                    }
                    for f in profile.fields
                ],
            },
        }
    except Exception as e:
        logger.error("数据画像失败: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"数据画像失败: {e}") from None


@router.post("/recommend", summary="图表推荐")
async def viz_recommend(body: DataInput) -> dict[str, Any]:
    """根据数据画像推荐图表类型与配置。"""
    try:
        profile = profile_dataset(body.data)
        recs = recommend_charts(profile, body.data)
        return {
            "success": True,
            "count": len(recs),
            "recommendations": [
                {
                    "chart_type": r.chart_type,
                    "title": r.title,
                    "description": r.description,
                    "score": r.score,
                    "reason": r.reason,
                    "config": r.config.to_dict(),
                }
                for r in recs
            ],
        }
    except Exception as e:
        logger.error("图表推荐失败: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"图表推荐失败: {e}") from None


@router.post("/render", summary="渲染 ECharts 配置")
async def viz_render(body: RenderRequest) -> dict[str, Any]:
    """根据通用图表配置协议，生成 ECharts option。"""
    try:
        option = render_echarts_option(body.config, body.data)
        return {
            "success": True,
            "chart_type": body.config.chart_type.value,
            "title": body.config.title,
            "echarts_option": option,
        }
    except Exception as e:
        logger.error("渲染失败: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"渲染失败: {e}") from None


@router.post("/auto", summary="自动可视化")
async def viz_auto(body: AutoVizRequest) -> dict[str, Any]:
    """上传数据，自动完成画像、推荐、渲染全流程。"""
    try:
        profile = profile_dataset(body.data)
        recs = recommend_charts(profile, body.data)
        results = []
        for r in recs[: body.max_charts]:
            try:
                option = render_echarts_option(r.config, body.data)
                results.append(
                    {
                        "chart_type": r.chart_type,
                        "title": r.title,
                        "description": r.description,
                        "reason": r.reason,
                        "config": r.config.to_dict(),
                        "echarts_option": option,
                    }
                )
            except Exception as ex:
                logger.warning("渲染推荐图表失败: %s", ex)
                continue

        return {
            "success": True,
            "profile": {
                "total_rows": profile.total_rows,
                "total_cols": profile.total_cols,
                "has_time_dim": profile.has_time_dim,
                "time_field": profile.time_field,
                "entity_field": profile.entity_field,
                "numeric_fields": profile.numeric_fields,
            },
            "charts": results,
        }
    except Exception as e:
        logger.error("自动可视化失败: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"自动可视化失败: {e}") from None
