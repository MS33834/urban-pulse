"""
城市竞争力指数 REST API

端点：
  POST /api/v1/index/compute   — 计算综合竞争力指数
  GET  /api/v1/index/rankings  — 获取排名列表（分维度）
  POST /api/v1/index/report/{city} — 单城市分析报告
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.analytics.competitiveness.framework import IndicatorFramework
from backend.analytics.competitiveness.ranker import CompetitivenessRanker
from backend.data.city_data import CITY_DATA

logger = logging.getLogger(__name__)

router = APIRouter(tags=["竞争力指数"], prefix="/index")


# ── data_provider: 从 CITY_DATA 提取指标值 ──────────────────────────
def _data_provider() -> dict[str, dict[str, float]]:
    """从 CITY_DATA 提取框架关心的指标值

    Returns:
        {城市名: {指标键: 原始值}}
    """
    covered_keys = set(IndicatorFramework.COVERED_INDICATOR_KEYS)

    result: dict[str, dict[str, float]] = {}
    for city_name, fields in CITY_DATA.items():
        filtered: dict[str, float] = {}
        for key in covered_keys:
            val = fields.get(key)
            if val is not None and isinstance(val, (int, float)):
                filtered[key] = float(val)
        if filtered:
            result[city_name] = filtered
    return result


# ── ranker 实例（单例） ──────────────────────────────────────────────
_ranker: CompetitivenessRanker | None = None


def get_ranker() -> CompetitivenessRanker:
    global _ranker
    if _ranker is None:
        _ranker = CompetitivenessRanker(
            data_provider=_data_provider,
            framework=IndicatorFramework,
        )
    return _ranker


# ── Pydantic 模型 ────────────────────────────────────────────────────


class ComputeRequest(BaseModel):
    city_codes: list[str] | None = None
    method: str = "entropy"


class ReportRequest(BaseModel):
    pass  # 仅用于 POST body 占位


# ── 端点 ────────────────────────────────────────────────────────────


@router.post("/compute")
def compute_index(req: ComputeRequest):
    """计算综合竞争力指数

    - city_codes: 可选，指定城市名称列表，默认全部
    - method: "entropy"（熵权法，默认）或 "default"（等权）
    """
    city_names = req.city_codes
    method = req.method if req.method in ("entropy", "default") else "entropy"

    try:
        ranker = get_ranker()
        result = ranker.compute_index(city_names=city_names, method=method)
    except Exception:
        logger.exception("计算竞争力指数失败")
        raise HTTPException(status_code=500, detail="计算竞争力指数失败，请稍后重试") from None

    return JSONResponse(
        content=result,
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.get("/rankings")
async def get_rankings(dimension: str | None = None):
    """获取排名列表

    - dimension: 可选，指定维度名（如 "科技力"），默认返回综合排名
    """
    try:
        ranker = get_ranker()
        result = ranker.compute_index()
    except Exception:
        logger.exception("获取排名失败")
        raise HTTPException(status_code=500, detail="获取排名失败，请稍后重试") from None

    if dimension:
        dim_rankings = result.get("rankings", {}).get(dimension)
        if dim_rankings is None:
            raise HTTPException(
                status_code=404,
                detail=f"维度「{dimension}」不存在。可用维度: {list(result.get('dimensions', {}).keys())}",
            )
        payload = {
            "dimension": dimension,
            "rankings": [{"city": city, "score": score} for city, score in dim_rankings],
        }
    else:
        payload = {
            "dimension": "overall",
            "rankings": [{"city": city, "score": score} for city, score in result["rankings"]["overall"]],
        }

    return JSONResponse(
        content=payload,
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.post("/report/{city}")
async def city_report(city: str):
    """单城市竞争力分析报告"""
    ranker = get_ranker()
    report = ranker.generate_report(city)

    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"]) from None

    return JSONResponse(
        content=report,
        headers={"Cache-Control": "private, max-age=300"},
    )
