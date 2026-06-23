"""
Tests for backend.core.storage modules.

Uses a per-test temporary SQLite database to keep tests isolated.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

import backend.core.storage as storage_mod
from backend.core.storage.dataset_store import (
    create_dataset,
    delete_dataset,
    get_dataset,
    get_dataset_columns,
    list_datasets,
    save_column_info,
    update_dataset,
)
from backend.core.storage.record_store import (
    bulk_insert_records,
    delete_records,
    get_entities,
    get_indicators,
    get_pivot,
    get_record_count,
    get_records,
    get_year_range,
)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Replace the singleton DB with a fresh temporary database for each test."""
    storage_mod.close_db()
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage_mod, "_DEFAULT_DB_PATH", str(db_path))
    storage_mod.init_db()
    yield
    storage_mod.close_db()
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass


def _make_dataset(name: str = "Test Dataset", **kwargs) -> dict[str, Any]:
    return create_dataset(name=name, **kwargs)


class TestStorageInit:
    def test_get_db_path_returns_default(self, monkeypatch, tmp_path):
        storage_mod.close_db()
        custom = tmp_path / "custom.db"
        monkeypatch.setattr(storage_mod, "_DEFAULT_DB_PATH", str(custom))
        assert storage_mod.get_db_path() == str(custom)

    def test_init_db_creates_tables(self):
        conn = storage_mod.get_connection()
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "datasets" in tables
        assert "dataset_columns" in tables
        assert "records" in tables

    def test_close_db_releases_connection(self):
        conn = storage_mod.get_connection()
        assert conn is not None
        storage_mod.close_db()
        assert storage_mod._connection is None


class TestDatasetStore:
    def test_create_and_get_dataset(self):
        ds = _make_dataset("深圳半导体", description="测试", source="test.csv")
        assert ds["name"] == "深圳半导体"
        assert ds["description"] == "测试"
        fetched = get_dataset(ds["id"])
        assert fetched is not None
        assert fetched["id"] == ds["id"]

    def test_list_datasets_order(self):
        ds1 = _make_dataset("Dataset A")
        ds2 = _make_dataset("Dataset B")
        datasets = list_datasets()
        ids = [d["id"] for d in datasets]
        assert ds2["id"] in ids
        assert ds1["id"] in ids

    def test_update_dataset(self):
        ds = _make_dataset("Original")
        updated = update_dataset(ds["id"], name="Updated", row_count=42)
        assert updated is not None
        assert updated["name"] == "Updated"
        assert updated["row_count"] == 42
        assert "updated_at" in updated

    def test_update_dataset_no_fields(self):
        ds = _make_dataset("NoChange")
        updated = update_dataset(ds["id"])
        assert updated is not None
        assert updated["name"] == "NoChange"

    def test_delete_dataset(self):
        ds = _make_dataset("ToDelete")
        assert delete_dataset(ds["id"]) is True
        assert get_dataset(ds["id"]) is None
        assert delete_dataset("missing") is False

    def test_save_and_get_column_info(self):
        ds = _make_dataset("WithColumns")
        cols = [
            {"col_name": "city", "col_index": 0, "detected_role": "entity", "data_type": "text"},
            {"col_name": "year", "col_index": 1, "detected_role": "time", "data_type": "number"},
            {"col_name": "gdp", "col_index": 2, "detected_role": "indicator", "data_type": "number"},
        ]
        save_column_info(ds["id"], cols)
        fetched = get_dataset_columns(ds["id"])
        assert len(fetched) == 3
        assert fetched[0]["col_name"] == "city"
        assert fetched[2]["human_label"] == "gdp"


class TestRecordStore:
    def _ds(self):
        return _make_dataset("Records")

    def test_bulk_insert_and_count(self):
        ds = self._ds()
        records = [
            {"entity": "深圳", "year": 2023, "indicator": "gdp", "value": 100.0},
            {"entity": "深圳", "year": 2024, "indicator": "gdp", "value": 110.0},
            {"entity": "广州", "year": 2024, "indicator": "gdp", "value": 90.0},
        ]
        inserted = bulk_insert_records(ds["id"], records)
        assert inserted == 3
        assert get_record_count(ds["id"]) == 3

    def test_get_records_filters(self):
        ds = self._ds()
        bulk_insert_records(
            ds["id"],
            [
                {"entity": "深圳", "year": 2023, "indicator": "gdp", "value": 100.0},
                {"entity": "深圳", "year": 2024, "indicator": "gdp", "value": 110.0},
                {"entity": "广州", "year": 2024, "indicator": "population", "value": 20.0},
            ],
        )

        all_records = get_records(ds["id"])
        assert len(all_records) == 3

        shenzhen = get_records(ds["id"], entity="深圳")
        assert len(shenzhen) == 2

        gdp = get_records(ds["id"], indicator="gdp")
        assert len(gdp) == 2

        year_range = get_records(ds["id"], year_start=2024, year_end=2024)
        assert len(year_range) == 2

        paged = get_records(ds["id"], limit=1, offset=1)
        assert len(paged) == 1

    def test_get_entities_indicators_year_range(self):
        ds = self._ds()
        bulk_insert_records(
            ds["id"],
            [
                {"entity": "深圳", "year": 2023, "indicator": "gdp", "value": 100.0},
                {"entity": "广州", "year": 2024, "indicator": "population", "value": 20.0},
            ],
        )
        assert set(get_entities(ds["id"])) == {"深圳", "广州"}
        assert set(get_indicators(ds["id"])) == {"gdp", "population"}
        assert get_year_range(ds["id"]) == (2023, 2024)

    def test_get_year_range_empty(self):
        ds = self._ds()
        assert get_year_range(ds["id"]) == (None, None)

    def test_delete_records(self):
        ds = self._ds()
        bulk_insert_records(
            ds["id"],
            [{"entity": "深圳", "year": 2024, "indicator": "gdp", "value": 1.0}],
        )
        assert get_record_count(ds["id"]) == 1
        delete_records(ds["id"])
        assert get_record_count(ds["id"]) == 0

    def test_get_pivot(self):
        ds = self._ds()
        bulk_insert_records(
            ds["id"],
            [
                {"entity": "深圳", "year": 2024, "indicator": "gdp", "value": 100.0},
                {"entity": "深圳", "year": 2024, "indicator": "population", "value": 20.0},
                {"entity": "广州", "year": 2024, "indicator": "gdp", "value": 90.0},
            ],
        )
        pivot = get_pivot(ds["id"])
        assert len(pivot) == 2
        by_entity = {row["entity"]: row for row in pivot}
        assert by_entity["深圳"]["gdp"] == 100.0
        assert by_entity["深圳"]["population"] == 20.0
        assert by_entity["广州"]["gdp"] == 90.0

        filtered = get_pivot(ds["id"], indicators=["gdp"], entities=["深圳"], year=2024)
        assert len(filtered) == 1
        assert filtered[0]["gdp"] == 100.0
