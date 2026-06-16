"""
Dataset CRUD operations.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from backend.core.storage import get_connection

logger = logging.getLogger(__name__)


def create_dataset(
    name: str,
    description: str = "",
    source: str = "",
    row_count: int = 0,
    col_count: int = 0,
    has_time_dim: bool = False,
) -> dict[str, Any]:
    conn = get_connection()
    dataset_id = str(uuid.uuid4())[:8]
    conn.execute(
        """INSERT INTO datasets (id, name, description, source, row_count, col_count, has_time_dim)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (dataset_id, name, description, source, row_count, col_count, int(has_time_dim)),
    )
    conn.commit()
    return get_dataset(dataset_id)


def get_dataset(dataset_id: str) -> dict[str, Any] | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
    if row is None:
        return None
    return dict(row)


def list_datasets() -> list[dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM datasets ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def update_dataset(dataset_id: str, **kwargs) -> dict[str, Any] | None:
    conn = get_connection()
    allowed = {"name", "description", "source", "row_count", "col_count", "has_time_dim"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return get_dataset(dataset_id)
    fields["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [dataset_id]
    conn.execute(f"UPDATE datasets SET {set_clause} WHERE id = ?", values)
    conn.commit()
    return get_dataset(dataset_id)


def delete_dataset(dataset_id: str) -> bool:
    conn = get_connection()
    cur = conn.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
    conn.commit()
    return cur.rowcount > 0


def get_dataset_columns(dataset_id: str) -> list[dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM dataset_columns WHERE dataset_id = ? ORDER BY col_index",
        (dataset_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def save_column_info(dataset_id: str, cols: list[dict[str, Any]]) -> None:
    """Save column metadata. `cols` items: {col_name, col_index, detected_role, data_type, human_label?}"""
    conn = get_connection()
    conn.execute("DELETE FROM dataset_columns WHERE dataset_id = ?", (dataset_id,))
    for c in cols:
        conn.execute(
            """INSERT INTO dataset_columns
               (dataset_id, col_name, col_index, detected_role, data_type, human_label)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (dataset_id, c["col_name"], c["col_index"],
             c.get("detected_role"), c.get("data_type"),
             c.get("human_label", c["col_name"])),
        )
    conn.commit()
