"""
预测快照存档 API

- 运行预测并一键存档
- 查询 / 筛选历史预测快照
- 回填真实值，形成预测-实际对账数据
- 为 validation dashboard 提供数据基础
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from backend.core.forecast_archive import ForecastArchive, ForecastSnapshot
from backend.core.forecast_engine import forecast_full_pipeline
from backend.core.province_aggregator import SUPPORTED_INDICATORS
from backend.data.city_data import get_all_forecast_cities, get_historical_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/forecast/archives", tags=["预测存档"])


def _get_archive() -> ForecastArchive:
    """获取默认存档管理器实例。"""
    return ForecastArchive()


class ArchiveCreateRequest(BaseModel):
    """创建预测存档请求"""

    city_name: str = Field(..., min_length=1, description="城市名称")
    indicator: str = Field("gdp", description=f"指标代码,支持: {', '.join(SUPPORTED_INDICATORS)}")
    forecast_years: int = Field(5, ge=1, le=20, description="预测年数")
    model: str = Field("ensemble", description="模型标识，默认 ensemble")
    plugin_type: str = Field("forecaster", description="插件类型")

    @field_validator("indicator")
    @classmethod
    def _validate_indicator(cls, v: str) -> str:
        if v not in SUPPORTED_INDICATORS:
            raise ValueError(f"不支持的指标 '{v}'")
        return v


class BackfillRequest(BaseModel):
    """回填真实值请求"""

    actual_value: float = Field(..., description="真实值")


class BackfillByMatchRequest(BaseModel):
    """按条件批量回填真实值请求"""

    model: str | None = None
    city_code: str | None = None
    indicator: str | None = None
    target_year: int | None = None
    actual_value: float = Field(..., description="真实值")


class ArchiveSnapshotOut(BaseModel):
    """预测快照输出"""

    forecast_id: str
    model: str
    city_code: str
    indicator: str
    forecast_date: str
    target_year: int
    predicted_value: float
    plugin_type: str
    confidence_interval: tuple[float, float] | None = None
    actual_value: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("", response_model=list[ArchiveSnapshotOut], summary="运行预测并一键存档")
async def create_archive(request: ArchiveCreateRequest) -> list[ArchiveSnapshotOut]:
    """
    对指定城市指标运行预测，并将每年的预测结果保存为快照。

    返回创建的预测快照列表，可用于后续真实值回填与准确率验证。
    """
    if request.city_name not in get_all_forecast_cities():
        raise HTTPException(status_code=404, detail=f"城市 {request.city_name} 不在预测城市列表中")

    df = get_historical_data(request.city_name)
    if df.empty or "year" not in df.columns or request.indicator not in df.columns:
        available = [c for c in df.columns if c != "year"] if not df.empty else []
        raise HTTPException(
            status_code=400,
            detail=f"城市 {request.city_name} 缺少指标 '{request.indicator}' 数据，可用: {available}",
        )

    df = df.sort_values("year").reset_index(drop=True)
    years = df["year"].astype(int).tolist()
    values = df[request.indicator].astype(float).tolist()

    if len(values) < 3:
        raise HTTPException(status_code=400, detail="历史样本不足，至少需要 3 年数据")

    try:
        result = forecast_full_pipeline(values, start_year=years[0], years=request.forecast_years)
    except Exception as e:
        logger.error("预测失败: %s", e, exc_info=True)
        raise HTTPException(status_code=503, detail="预测计算失败") from None

    predictions = result["ensemble"]["predictions"]
    ci_lower = result["ensemble"].get("confidence_interval_lower")
    ci_upper = result["ensemble"].get("confidence_interval_upper")
    start_forecast_year = years[-1] + 1

    archive = _get_archive()
    created: list[ForecastSnapshot] = []
    today = date.today().isoformat()

    for idx, pred in enumerate(predictions):
        ci = None
        if ci_lower is not None and ci_upper is not None:
            ci = (float(ci_lower[idx]), float(ci_upper[idx]))

        snapshot = ForecastSnapshot(
            model=request.model,
            city_code=request.city_name,
            indicator=request.indicator,
            forecast_date=today,
            target_year=start_forecast_year + idx,
            predicted_value=float(pred),
            plugin_type=request.plugin_type,
            confidence_interval=ci,
            metadata={
                "historical_start_year": years[0],
                "historical_end_year": years[-1],
                "engine_stack": result.get("engine_stack", {}),
            },
        )
        archive.save(snapshot)
        created.append(snapshot)

    return [ArchiveSnapshotOut(**s.to_dict()) for s in created]


@router.get("", summary="列出预测存档")
async def list_archives(
    city_code: str | None = Query(None, description="按城市筛选"),
    indicator: str | None = Query(None, description="按指标筛选"),
    model: str | None = Query(None, description="按模型筛选"),
    pending_only: bool = Query(False, description="仅返回待回填真实值的快照"),
) -> dict[str, Any]:
    """列出所有预测快照，支持城市、指标、模型筛选与待回填过滤。"""
    archive = _get_archive()
    snapshots = archive.list_all()

    if city_code:
        snapshots = [s for s in snapshots if s.city_code == city_code]
    if indicator:
        snapshots = [s for s in snapshots if s.indicator == indicator]
    if model:
        snapshots = [s for s in snapshots if s.model == model]
    if pending_only:
        snapshots = [s for s in snapshots if s.actual_value is None]

    return {
        "total": len(snapshots),
        "pending": sum(1 for s in snapshots if s.actual_value is None),
        "validated": sum(1 for s in snapshots if s.actual_value is not None),
        "snapshots": [ArchiveSnapshotOut(**s.to_dict()).model_dump() for s in snapshots],
    }


@router.get("/{forecast_id}", response_model=ArchiveSnapshotOut, summary="获取单个预测快照")
async def get_archive(forecast_id: str) -> ArchiveSnapshotOut:
    """按 forecast_id 获取预测快照详情。"""
    archive = _get_archive()
    snapshot = archive.find_by_id(forecast_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"未找到预测快照 {forecast_id}")
    return ArchiveSnapshotOut(**snapshot.to_dict())


@router.post("/{forecast_id}/backfill", response_model=ArchiveSnapshotOut, summary="回填单个快照真实值")
async def backfill_archive(forecast_id: str, request: BackfillRequest) -> ArchiveSnapshotOut:
    """为指定 forecast_id 回填真实值，用于后续准确率验证。"""
    archive = _get_archive()
    if not archive.find_by_id(forecast_id):
        raise HTTPException(status_code=404, detail=f"未找到预测快照 {forecast_id}")

    success = archive.update_actual(forecast_id, request.actual_value)
    if not success:
        raise HTTPException(status_code=503, detail="回填失败")

    snapshot = archive.find_by_id(forecast_id)
    return ArchiveSnapshotOut(**snapshot.to_dict())


@router.post("/backfill-by-match", summary="按条件批量回填真实值")
async def backfill_by_match(request: BackfillByMatchRequest) -> dict[str, Any]:
    """
    按 model + city_code + indicator + target_year 批量匹配并回填真实值。

    返回成功回填的记录数。
    """
    if not request.city_code or not request.indicator or not request.target_year:
        raise HTTPException(status_code=400, detail="city_code、indicator、target_year 不能为空")

    archive = _get_archive()
    count = archive.update_actual_by_match(
        model=request.model or "",
        city_code=request.city_code,
        indicator=request.indicator,
        target_year=request.target_year,
        actual_value=request.actual_value,
    )
    return {"updated": count}


@router.delete("/{forecast_id}", summary="删除预测快照")
async def delete_archive(forecast_id: str) -> dict[str, Any]:
    """删除指定 forecast_id 的预测快照。"""
    archive = _get_archive()
    snapshot = archive.find_by_id(forecast_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"未找到预测快照 {forecast_id}")

    snapshots = archive.list_all()
    remaining = [s for s in snapshots if s.forecast_id != forecast_id]
    with archive._write_lock:
        archive._rewrite_locked(remaining)
        archive._cache = None
        archive._cache_mtime = None

    return {"deleted": forecast_id, "remaining": len(remaining)}
