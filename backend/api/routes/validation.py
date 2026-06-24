"""
预测准确率验证 API

将 ForecastValidator 与 ValidationDashboard 暴露为 REST 接口，
支持 JSON 报告、HTML 仪表板与核心指标查询。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse

from backend.core.forecast_validation import ForecastValidator
from backend.core.validation_dashboard import ValidationDashboard

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/validation", tags=["预测验证"])


def _get_validator() -> ForecastValidator:
    """获取默认验证器实例。"""
    return ForecastValidator()


@router.get("/metrics", summary="核心验证指标")
async def validation_metrics() -> dict[str, Any]:
    """返回总体验证指标摘要（已回填真实值的样本）。"""
    validator = _get_validator()
    metrics = validator.summary()
    return {
        "count": metrics.count,
        "mae": metrics.mae,
        "mape": metrics.mape,
        "rmse": metrics.rmse,
        "bias": metrics.bias,
        "hit_rate": metrics.hit_rate,
    }


@router.get("/report", summary="完整验证报告（JSON）")
async def validation_report() -> dict[str, Any]:
    """按模型、城市、指标维度拆分准确率，并返回置信区间命中率。"""
    validator = _get_validator()
    return validator.report()


@router.get("/dashboard", response_class=HTMLResponse, summary="验证仪表板（HTML）")
async def validation_dashboard() -> str:
    """渲染可嵌入 GitHub Pages 的静态 HTML 验证仪表板。"""
    try:
        return ValidationDashboard().render()
    except Exception as e:
        logger.error("渲染验证仪表板失败: %s", e, exc_info=True)
        return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>Urban Pulse 预测准确率验证仪表板</title></head>
<body><h1>渲染失败</h1><p>{str(e)}</p></body></html>"""


@router.get("/dashboard-download", summary="下载验证仪表板 HTML")
async def download_dashboard() -> Response:
    """下载验证仪表板 HTML 文件。"""
    html_content = ValidationDashboard().render()
    return Response(
        content=html_content,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=validation_dashboard.html"},
    )
