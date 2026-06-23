"""Tests for backend.seed_data."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

import backend.seed_data as seed_module
from backend.seed_data import seed_if_missing


class TestSeedIfMissing:
    def test_seed_if_missing_already_exists(self, monkeypatch):
        """If seed dataset already exists, function should return False."""
        called = {"get_dataset": 0}

        def fake_get_dataset(dataset_id: str) -> dict[str, Any] | None:
            called["get_dataset"] += 1
            if dataset_id == seed_module._SEED_DATASET_ID:
                return {"id": dataset_id, "row_count": 100}
            return None

        monkeypatch.setattr(seed_module, "get_dataset", fake_get_dataset)

        assert seed_if_missing() is False
        assert called["get_dataset"] == 1

    def test_seed_if_missing_creates_and_inserts(self, monkeypatch):
        """Seeding a fresh temp DB creates dataset, columns, and records."""
        store: dict[str, Any] = {"dataset": None, "columns": [], "records": []}

        def fake_get_dataset(dataset_id: str) -> dict[str, Any] | None:
            if dataset_id == seed_module._SEED_DATASET_ID:
                return store["dataset"]
            return None

        def fake_create_dataset(**kwargs) -> dict[str, Any]:
            ds = {"id": "orig-id", **kwargs}
            store["dataset"] = ds
            return ds

        def fake_save_column_info(dataset_id: str, cols: list[dict]) -> None:
            store["columns"] = cols

        def fake_bulk_insert_records(dataset_id: str, records: list[dict]) -> int:
            store["records"] = records
            return len(records)

        def fake_get_record_count(dataset_id: str) -> int:
            return len(store["records"])

        def fake_update_dataset(dataset_id: str, **kwargs) -> dict[str, Any] | None:
            store["dataset"].update(kwargs)
            return store["dataset"]

        monkeypatch.setattr(seed_module, "get_dataset", fake_get_dataset)
        monkeypatch.setattr(seed_module, "create_dataset", fake_create_dataset)
        monkeypatch.setattr(seed_module, "save_column_info", fake_save_column_info)
        monkeypatch.setattr(seed_module, "bulk_insert_records", fake_bulk_insert_records)
        monkeypatch.setattr(seed_module, "get_record_count", fake_get_record_count)
        monkeypatch.setattr(seed_module, "update_dataset", fake_update_dataset)

        monkeypatch.setattr(seed_module, "init_db", lambda: None)
        monkeypatch.setattr(seed_module, "get_connection", lambda: MagicMock())

        result = seed_if_missing()

        assert result is True
        assert store["dataset"] is not None
        assert store["dataset"]["id"] == "orig-id"
        assert store["dataset"]["row_count"] == len(store["records"])
        assert len(store["columns"]) == seed_module._SNAPSHOT_INDICATORS.__len__() + 2
        assert len(store["records"]) > 0

        # Column metadata includes entity/time/indicator roles.
        roles = {c["detected_role"] for c in store["columns"]}
        assert "entity" in roles
        assert "time" in roles
        assert "indicator" in roles

    def test_seed_if_missing_dataset_retrieval_failure(self, monkeypatch):
        """If freshly created dataset cannot be retrieved, RuntimeError is raised."""

        def fake_get_dataset(dataset_id: str) -> dict[str, Any] | None:
            return None

        def fake_create_dataset(**kwargs) -> dict[str, Any]:
            return {"id": "orig-id", **kwargs}

        monkeypatch.setattr(seed_module, "get_dataset", fake_get_dataset)
        monkeypatch.setattr(seed_module, "create_dataset", fake_create_dataset)
        monkeypatch.setattr(seed_module, "init_db", lambda: None)
        monkeypatch.setattr(seed_module, "get_connection", lambda: MagicMock())

        with pytest.raises(RuntimeError, match="Failed to retrieve seeded dataset"):
            seed_if_missing()

    def test_seed_indicator_lists_are_disjoint_from_blacklist(self):
        """Snapshot/historical indicator names should not collide with blacklist."""
        for ind in seed_module._SNAPSHOT_INDICATORS:
            assert ind not in seed_module._INDICATOR_BLACKLIST
        for ind in seed_module._HISTORICAL_INDICATORS:
            assert ind not in seed_module._INDICATOR_BLACKLIST
