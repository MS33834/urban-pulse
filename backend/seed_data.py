"""
Seed the SQLite database with existing hardcoded city data (10 cities, 2020-2025).

This runs once at startup if the seed dataset doesn't exist yet.
"""

import logging

from backend.core.storage import get_connection, init_db
from backend.core.storage.dataset_store import (
    create_dataset,
    get_dataset,
    save_column_info,
    update_dataset,
)
from backend.core.storage.record_store import bulk_insert_records, get_record_count

logger = logging.getLogger(__name__)

_SEED_DATASET_ID = "_seed_10_cities"
_INDICATOR_BLACKLIST = {"name", "year", "region", "industry", "industry_code",
                         "data_source", "data_quality"}

_SNAPSHOT_INDICATORS = [
    "land_price", "salary_level", "energy_cost", "financing_cost",
    "local_support_rate", "avg_delivery_time", "location_quotient",
    "supplier_count", "tax_reduction", "policy_coverage", "tax_coverage",
    "rd_subsidy", "avg_approval_time", "gdp", "gdp_growth",
    "population", "fiscal_revenue", "rd_intensity",
    "industry_high_tech_ratio",
]

_HISTORICAL_INDICATORS = ["gdp", "population", "fiscal_revenue",
                           "rd_intensity", "industry_high_tech_ratio"]


def seed_if_missing() -> bool:
    """Seed database with the 10-city dataset if it doesn't exist yet.

    Returns True if seeded, False if already present.
    """
    existing = get_dataset(_SEED_DATASET_ID)
    if existing is not None:
        logger.info("Seed dataset already exists (%d rows), skipping", existing.get("row_count", 0))
        return False

    init_db()

    from backend.data.city_data import CITY_DATA, HISTORICAL_DATA

    conn = get_connection()

    # ── 1) Create seed dataset ──
    ds = create_dataset(
        name="中国10城经济数据 (示例)",
        description="深圳、上海、北京、广州、杭州、武汉、成都、南京 — 19项经济指标, 2020-2025年",
        source="internal_seed",
        row_count=0,
        col_count=len(_SNAPSHOT_INDICATORS) + 2,
        has_time_dim=True,
    )
    # Override ID so we can reference it consistently
    conn.execute("UPDATE datasets SET id = ? WHERE id = ?", (_SEED_DATASET_ID, ds["id"]))
    conn.commit()
    ds = get_dataset(_SEED_DATASET_ID)

    # ── 2) Column metadata ──
    columns = [
        {"col_name": "城市", "col_index": 0, "detected_role": "entity", "data_type": "text"},
        {"col_name": "年份", "col_index": 1, "detected_role": "time", "data_type": "number"},
    ]
    for idx, ind in enumerate(_SNAPSHOT_INDICATORS, start=2):
        columns.append({
            "col_name": ind,
            "col_index": idx,
            "detected_role": "indicator",
            "data_type": "number",
        })
    save_column_info(_SEED_DATASET_ID, columns)

    # ── 3) Convert CITY_DATA → records ──
    records: list[dict] = []
    for city_name, fields in CITY_DATA.items():
        year = fields.get("year", 2025)
        for ind in _SNAPSHOT_INDICATORS:
            val = fields.get(ind)
            if val is not None:
                records.append({
                    "entity": city_name,
                    "year": year,
                    "indicator": ind,
                    "value": float(val),
                })

    # ── 4) Convert HISTORICAL_DATA → records ──
    for city_name, rows in HISTORICAL_DATA.items():
        for row in rows:
            year = row.get("year")
            if year is None:
                continue
            for ind in _HISTORICAL_INDICATORS:
                val = row.get(ind)
                if val is not None:
                    records.append({
                        "entity": city_name,
                        "year": year,
                        "indicator": ind,
                        "value": float(val),
                    })

    # ── 5) Bulk insert ──
    bulk_insert_records(_SEED_DATASET_ID, records)
    count = get_record_count(_SEED_DATASET_ID)
    update_dataset(_SEED_DATASET_ID, row_count=count)

    logger.info("Seeded %d records from 10-city data (dataset=%s)", count, _SEED_DATASET_ID)
    return True
