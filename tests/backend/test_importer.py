"""Tests for backend.core.importer."""

from __future__ import annotations

import os

import pytest

import backend.core.storage as storage_mod
from backend.core.importer import (
    _coerce_value,
    _is_numeric,
    detect_column_roles,
    import_data,
    parse_csv,
    parse_json,
)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Use a fresh temporary SQLite database for importer tests."""
    storage_mod.close_db()
    db_path = tmp_path / "importer.db"
    monkeypatch.setattr(storage_mod, "_DEFAULT_DB_PATH", str(db_path))
    storage_mod.init_db()
    yield
    storage_mod.close_db()
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass


class TestHelpers:
    def test_is_numeric(self):
        assert _is_numeric(42) is True
        assert _is_numeric(3.14) is True
        assert _is_numeric("1,234.5") is True
        assert _is_numeric("abc") is False
        assert _is_numeric(None) is False

    def test_coerce_value(self):
        assert _coerce_value(42) == 42.0
        assert _coerce_value("1,234") == 1234.0
        assert _coerce_value("") is None
        assert _coerce_value(None) is None
        assert _coerce_value("abc") is None

    def test_detect_column_roles(self):
        headers = ["city", "year", "gdp", "category"]
        rows = [
            {"city": "深圳", "year": 2023, "gdp": "100", "category": "A"},
            {"city": "广州", "year": 2024, "gdp": "90", "category": "B"},
        ]
        roles = {r["col_name"]: r for r in detect_column_roles(headers, rows)}
        assert roles["city"]["detected_role"] == "entity"
        assert roles["year"]["detected_role"] == "time"
        assert roles["gdp"]["detected_role"] == "indicator"
        assert roles["category"]["detected_role"] == "categorical"


class TestParsers:
    def test_parse_csv(self):
        content = "city,year,gdp\n深圳,2023,100\n广州,2023,90\n"
        headers, rows = parse_csv(content)
        assert headers == ["city", "year", "gdp"]
        assert len(rows) == 2
        assert rows[0]["city"] == "深圳"

    def test_parse_csv_bytes(self):
        content = b"city,year,gdp\n\xe6\xb7\xb1\xe5\x9c\xb3,2023,100\n"
        headers, rows = parse_csv(content)
        assert rows[0]["city"] == "深圳"

    def test_parse_json_list(self):
        content = '[{"city": "深圳", "year": 2023, "gdp": 100}]'
        headers, rows = parse_json(content)
        assert headers == ["city", "year", "gdp"]
        assert len(rows) == 1

    def test_parse_json_object(self):
        content = '{"sz": {"city": "深圳", "year": 2023, "gdp": 100}}'
        headers, rows = parse_json(content)
        assert len(rows) == 1
        assert rows[0]["city"] == "深圳"

    def test_parse_json_invalid_structure(self):
        with pytest.raises(ValueError, match="Unsupported JSON structure"):
            parse_json("123")


class TestImportData:
    def test_import_csv(self):
        csv = "city,year,gdp\n深圳,2023,100\n深圳,2024,110\n广州,2024,90\n"
        ds = import_data(csv, "test.csv", name="城市GDP")
        assert ds is not None
        assert ds["name"] == "城市GDP"
        assert ds["row_count"] == 3
        assert ds["col_count"] == 3

    def test_import_json(self):
        json = '[{"city": "深圳", "year": 2023, "gdp": 100}, {"city": "广州", "year": 2023, "gdp": 90}]'
        ds = import_data(json, "test.json")
        assert ds is not None
        assert ds["name"] == "test"
        assert ds["row_count"] == 2

    def test_import_unsupported_extension(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            import_data("content", "test.txt")

    def test_import_empty_data(self):
        assert import_data("city,year\n", "empty.csv") is None

    def test_import_without_entity_column(self):
        csv = "year,gdp\n2023,100\n2024,110\n"
        ds = import_data(csv, "no_entity.csv")
        assert ds is not None
        assert ds["row_count"] == 2
