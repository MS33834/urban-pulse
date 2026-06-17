"""
Record CRUD — the wide-table storage (entity × year × indicator × value).
"""

import logging
from typing import Any

from backend.core.storage import _lock, get_connection

logger = logging.getLogger(__name__)


def bulk_insert_records(dataset_id: str, records: list[dict[str, Any]]) -> int:
    """Insert records in bulk. Each record: {entity, year, indicator, value}.

    Returns the number of rows inserted.
    """
    conn = get_connection()
    data = [
        (dataset_id, r["entity"], r.get("year"), r["indicator"], r["value"])
        for r in records
    ]
    with _lock:
        conn.executemany(
            "INSERT INTO records (dataset_id, entity, year, indicator, value) VALUES (?, ?, ?, ?, ?)",
            data,
        )
        conn.commit()
    return len(data)


def get_records(
    dataset_id: str,
    entity: str | None = None,
    indicator: str | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    limit: int = 1000,
    offset: int = 0,
) -> list[dict[str, Any]]:
    conn = get_connection()
    conditions = ["dataset_id = ?"]
    params: list[Any] = [dataset_id]
    if entity:
        conditions.append("entity = ?")
        params.append(entity)
    if indicator:
        conditions.append("indicator = ?")
        params.append(indicator)
    if year_start is not None:
        conditions.append("year >= ?")
        params.append(year_start)
    if year_end is not None:
        conditions.append("year <= ?")
        params.append(year_end)

    # conditions 为代码内硬编码的占位符子句，所有值均已参数化；nosec B608
    sql = f"SELECT * FROM records WHERE {' AND '.join(conditions)} ORDER BY entity, year, indicator LIMIT ? OFFSET ?"  # nosec B608
    params.extend([limit, offset])
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_entities(dataset_id: str) -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT entity FROM records WHERE dataset_id = ? ORDER BY entity",
        (dataset_id,),
    ).fetchall()
    return [r["entity"] for r in rows]


def get_indicators(dataset_id: str) -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT indicator FROM records WHERE dataset_id = ? ORDER BY indicator",
        (dataset_id,),
    ).fetchall()
    return [r["indicator"] for r in rows]


def get_year_range(dataset_id: str) -> tuple[int | None, int | None]:
    conn = get_connection()
    row = conn.execute(
        "SELECT MIN(year) AS min_y, MAX(year) AS max_y FROM records WHERE dataset_id = ? AND year IS NOT NULL",
        (dataset_id,),
    ).fetchone()
    return (row["min_y"], row["max_y"])


def get_record_count(dataset_id: str) -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM records WHERE dataset_id = ?", (dataset_id,)
    ).fetchone()
    return row["cnt"]


def delete_records(dataset_id: str) -> None:
    from backend.core.storage import execute_write
    execute_write("DELETE FROM records WHERE dataset_id = ?", (dataset_id,))


def get_pivot(
    dataset_id: str,
    indicators: list[str] | None = None,
    entities: list[str] | None = None,
    year: int | None = None,
) -> list[dict[str, Any]]:
    """Return entity × indicator pivoted data.

    Each row: {entity, indicator_1: value, indicator_2: value, ...}
    """
    conn = get_connection()
    conditions = ["dataset_id = ?"]
    params: list[Any] = [dataset_id]
    if indicators:
        placeholders = ",".join("?" for _ in indicators)
        conditions.append(f"indicator IN ({placeholders})")
        params.extend(indicators)
    if entities:
        placeholders = ",".join("?" for _ in entities)
        conditions.append(f"entity IN ({placeholders})")
        params.extend(entities)
    if year is not None:
        conditions.append("year = ?")
        params.append(year)

    # conditions 为代码内硬编码的占位符子句，所有值均已参数化；nosec B608
    rows = conn.execute(
        f"SELECT entity, indicator, value FROM records WHERE {' AND '.join(conditions)}",  # nosec B608
        params,
    ).fetchall()

    # Pivot in Python
    pivot: dict[str, dict[str, float]] = {}
    for r in rows:
        pivot.setdefault(r["entity"], {})[r["indicator"]] = r["value"]

    result = []
    for entity, indicator_values in pivot.items():
        row: dict[str, Any] = {"entity": entity}
        row.update(indicator_values)
        result.append(row)
    return result
