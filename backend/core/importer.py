"""
Universal CSV / JSON importer with auto column detection.

Detects entity, time, indicator, and categorical columns automatically.
"""

import csv
import io
import json
import logging
import re
from typing import Any

from backend.core.storage.dataset_store import get_dataset  # re-exported below

logger = logging.getLogger(__name__)

__all__ = [
    "detect_column_roles",
    "import_data",
    "parse_csv",
    "parse_json",
    "get_dataset",
]

# ── pattern lists for role detection ───────────────────────────────────────
_ENTITY_PATTERNS = re.compile(
    r"^(city|城市|area|地区|region|entity|name|名称|company|公司|"
    r"province|省份|省|市|district|country|国家|brand|品牌)$",
    re.IGNORECASE,
)

_TIME_PATTERNS = re.compile(
    r"^(year|年份|time|日期|period|period|date|季度|month|月份)$",
    re.IGNORECASE,
)


def _is_numeric(val: Any) -> bool:
    if isinstance(val, (int, float)):
        return True
    if isinstance(val, str):
        try:
            float(val.replace(",", ""))
            return True
        except (ValueError, AttributeError):
            return False
    return False


def _coerce_value(val: Any) -> float | None:
    """Try to coerce a value to float, return None on failure."""
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.replace(",", "").replace(" ", ""))
        except ValueError:
            return None
    return None


def detect_column_roles(
    headers: list[str], sample_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Auto-detect the role of each column.

    Returns list of {col_name, col_index, detected_role, data_type}.
    """
    result: list[dict[str, Any]] = []
    for idx, col in enumerate(headers):
        role = "indicator"  # default
        dtype = "number"

        # 1) Check name patterns for entity / time
        if _ENTITY_PATTERNS.match(col):
            role = "entity"
            dtype = "text"
        elif _TIME_PATTERNS.match(col):
            role = "time"
            dtype = "text"

        # 2) Check sample values to refine
        if role == "indicator":
            values = [r.get(col) for r in sample_rows if r.get(col) is not None]
            numeric_count = sum(1 for v in values if _is_numeric(v))
            if len(values) > 0 and numeric_count < len(values) * 0.5:
                dtype = "text"
                # Not enough numeric → could be categorical
                role = "categorical"

        result.append({
            "col_name": col,
            "col_index": idx,
            "detected_role": role,
            "data_type": dtype,
        })

    return result


def _records_from_rows(
    headers: list[str],
    rows: list[dict[str, Any]],
    col_roles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert parsed rows to wide-table records (entity × year × indicator × value)."""
    # Find entity/time column indices
    entity_col = next(
        (c["col_name"] for c in col_roles if c["detected_role"] == "entity"), None
    )
    time_col = next(
        (c["col_name"] for c in col_roles if c["detected_role"] == "time"), None
    )
    indicator_cols = [c["col_name"] for c in col_roles if c["detected_role"] in ("indicator", "categorical")]

    if entity_col is None:
        logger.warning("No entity column detected — records will be flat")
        entity_col = "__row_index__"

    records: list[dict[str, Any]] = []
    for row_idx, row in enumerate(rows):
        entity = row.get(entity_col, f"row_{row_idx}") if entity_col != "__row_index__" else f"row_{row_idx}"
        year = None
        if time_col:
            raw_year = row.get(time_col)
            if raw_year is not None:
                try:
                    year = int(float(str(raw_year).strip()))
                except (ValueError, TypeError):
                    year = None

        for ic in indicator_cols:
            raw_val = row.get(ic)
            val = _coerce_value(raw_val)
            if val is not None:
                records.append({
                    "entity": str(entity),
                    "year": year,
                    "indicator": ic,
                    "value": val,
                })

    return records


def parse_csv(content: str | bytes) -> tuple[list[str], list[dict[str, Any]]]:
    """Parse CSV string → (headers, list of dict rows)."""
    if isinstance(content, bytes):
        # Try utf-8-sig (BOM) first, then gbk, then utf-8
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = content.decode("gbk")
            except UnicodeDecodeError:
                text = content.decode("utf-8", errors="replace")
    else:
        text = content

    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    rows = list(reader)
    return headers, rows


def parse_json(content: str | bytes) -> tuple[list[str], list[dict[str, Any]]]:
    """Parse JSON content → (headers, list of dict rows).

    Supports: [{...}, {...}] array-of-objects, or {key: {...}} object-of-objects.
    """
    if isinstance(content, bytes):
        text = content.decode("utf-8")
    else:
        text = content

    data = json.loads(text)
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = list(data.values())
    else:
        raise ValueError(f"Unsupported JSON structure: expected list or dict, got {type(data).__name__}")

    if not rows:
        return [], []

    headers = list(rows[0].keys())
    return headers, rows


def import_data(
    content: str | bytes,
    filename: str,
    name: str | None = None,
    description: str = "",
) -> dict[str, Any] | None:
    """Main entry: parse content, detect columns, store in SQLite.

    Returns dataset info dict, or None on failure.
    """
    from backend.core.storage.dataset_store import create_dataset, save_column_info, update_dataset
    from backend.core.storage.record_store import bulk_insert_records, get_record_count

    # 1) Parse
    ext = filename.lower()
    if ext.endswith(".json"):
        headers, rows = parse_json(content)
    elif ext.endswith(".csv"):
        headers, rows = parse_csv(content)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    if not headers or not rows:
        logger.warning("No data found in uploaded file: %s", filename)
        return None

    # 2) Detect column roles
    col_roles = detect_column_roles(headers, rows[:20])

    has_time = any(c["detected_role"] == "time" for c in col_roles)

    # 3) Create dataset entry
    dataset_name = name or filename.rsplit(".", 1)[0]
    ds = create_dataset(
        name=dataset_name,
        description=description,
        source=filename,
        row_count=0,
        col_count=len(headers),
        has_time_dim=has_time,
    )

    # 4) Save column metadata
    save_column_info(ds["id"], col_roles)

    # 5) Convert to records & insert
    records = _records_from_rows(headers, rows, col_roles)
    if records:
        bulk_insert_records(ds["id"], records)

    # 6) Update row count
    count = get_record_count(ds["id"])
    update_dataset(ds["id"], row_count=count)

    logger.info("Imported %d records from %s (dataset=%s)", count, filename, ds["id"])
    return get_dataset(ds["id"])
