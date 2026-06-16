"""
Dataset API routes — upload, list, inspect, and delete datasets.
"""

import logging

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from backend.core.importer import import_data
from backend.core.storage.dataset_store import (
    delete_dataset,
    get_dataset,
    get_dataset_columns,
    list_datasets,
    update_dataset,
)
from backend.core.storage.record_store import (
    get_entities,
    get_indicators,
    get_pivot,
    get_records,
    get_year_range,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/datasets", tags=["数据集"])


class UpdateMetaRequest(BaseModel):
    name: str | None = None
    description: str | None = None


# ── Upload ────────────────────────────────────────────────────────────────


@router.post("/upload", summary="上传 CSV / JSON 数据")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(None),
    description: str = Form(""),
):
    """Upload a CSV or JSON file. Auto-detects entity/time/indicator columns."""
    if file.filename is None:
        raise HTTPException(400, "filename required")
    ext = file.filename.lower()
    if not (ext.endswith(".csv") or ext.endswith(".json")):
        raise HTTPException(400, "Only .csv and .json files are supported")

    content = await file.read()
    try:
        ds = import_data(
            content=content,
            filename=file.filename,
            name=name,
            description=description,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Upload failed for %s", file.filename)
        raise HTTPException(500, f"Import error: {e}")

    if ds is None:
        raise HTTPException(400, "No data could be extracted from the file")

    return {"message": "imported", "dataset": ds}


# ── CRUD ──────────────────────────────────────────────────────────────────


@router.get("", summary="数据集列表")
def list_all_datasets():
    """Return all datasets, newest first."""
    return {"datasets": list_datasets()}


@router.get("/{dataset_id}", summary="数据集详情")
def get_dataset_detail(dataset_id: str):
    """Return dataset metadata + column info."""
    ds = get_dataset(dataset_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")
    cols = get_dataset_columns(dataset_id)
    entities = get_entities(dataset_id)
    indicators = get_indicators(dataset_id)
    year_range = get_year_range(dataset_id)
    return {
        "dataset": ds,
        "columns": cols,
        "entities": entities,
        "indicators": indicators,
        "year_range": {"min": year_range[0], "max": year_range[1]},
    }


@router.put("/{dataset_id}", summary="更新数据集元信息")
def update_dataset_meta(dataset_id: str, body: UpdateMetaRequest):
    """Update dataset name and/or description."""
    ds = update_dataset(dataset_id, **body.model_dump(exclude_none=True))
    if ds is None:
        raise HTTPException(404, "Dataset not found")
    return {"dataset": ds}


@router.delete("/{dataset_id}", summary="删除数据集")
def delete_dataset_endpoint(dataset_id: str):
    """Delete a dataset and all its records."""
    ok = delete_dataset(dataset_id)
    if not ok:
        raise HTTPException(404, "Dataset not found")
    return {"message": "deleted"}


# ── Data access ───────────────────────────────────────────────────────────


@router.get("/{dataset_id}/data", summary="原始数据")
def get_dataset_data(
    dataset_id: str,
    entity: str | None = Query(None),
    indicator: str | None = Query(None),
    year_start: int | None = Query(None),
    year_end: int | None = Query(None),
    limit: int = Query(200, ge=1, le=5000),
    offset: int = Query(0, ge=0),
):
    """Return raw records with optional filters."""
    rows = get_records(
        dataset_id, entity=entity, indicator=indicator,
        year_start=year_start, year_end=year_end,
        limit=limit, offset=offset,
    )
    return {"records": rows, "count": len(rows)}


@router.get("/{dataset_id}/pivot", summary="透视数据")
def get_dataset_pivot(
    dataset_id: str,
    indicators: str = Query(None, description="Comma-separated indicator names"),
    entities: str = Query(None, description="Comma-separated entity names"),
    year: int | None = Query(None),
):
    """Return pivoted table (entity × indicators as columns)."""
    ind_list = [i.strip() for i in indicators.split(",")] if indicators else None
    ent_list = [e.strip() for e in entities.split(",")] if entities else None
    data = get_pivot(dataset_id, indicators=ind_list, entities=ent_list, year=year)
    return {"data": data, "count": len(data)}


@router.get("/{dataset_id}/entities", summary="实体列表")
def list_dataset_entities(dataset_id: str):
    """Return all distinct entity names."""
    return {"entities": get_entities(dataset_id)}


@router.get("/{dataset_id}/indicators", summary="指标列表")
def list_dataset_indicators(dataset_id: str):
    """Return all distinct indicator names."""
    return {"indicators": get_indicators(dataset_id)}
