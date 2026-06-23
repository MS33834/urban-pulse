"""Tests for backend.utils helpers."""

from __future__ import annotations

import json

import pandas as pd

from backend.utils.export_utils import ExportUtils
from backend.utils.file_utils import FileUtils


class TestFileUtils:
    def test_ensure_directory(self, tmp_path):
        target = tmp_path / "nested" / "dir"
        result = FileUtils.ensure_directory(target)
        assert result.exists()

    def test_save_and_load_json(self, tmp_path):
        path = tmp_path / "data.json"
        data = {"city": "深圳", "gdp": 100}
        FileUtils.save_json(data, path)
        loaded = FileUtils.load_json(path)
        assert loaded == data

    def test_save_and_load_csv(self, tmp_path):
        path = tmp_path / "data.csv"
        df = pd.DataFrame({"city": ["深圳"], "gdp": [100]})
        FileUtils.save_csv(df, path)
        loaded = FileUtils.load_csv(path)
        assert loaded["city"].iloc[0] == "深圳"

    def test_save_and_load_excel(self, tmp_path):
        path = tmp_path / "data.xlsx"
        df = pd.DataFrame({"city": ["深圳"], "gdp": [100]})
        FileUtils.save_excel(df, path)
        loaded = FileUtils.load_excel(path)
        assert loaded["city"].iloc[0] == "深圳"

    def test_list_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.csv").write_text("b")
        files = FileUtils.list_files(tmp_path, "*.csv")
        assert len(files) == 1
        assert files[0].name == "b.csv"

    def test_list_files_missing_dir(self, tmp_path):
        files = FileUtils.list_files(tmp_path / "missing")
        assert files == []

    def test_file_exists(self, tmp_path):
        path = tmp_path / "exists.txt"
        path.write_text("x")
        assert FileUtils.file_exists(path) is True
        assert FileUtils.file_exists(tmp_path / "missing.txt") is False


class TestExportUtils:
    def test_export_csv(self, tmp_path):
        path = str(tmp_path / "out.csv")
        df = pd.DataFrame({"x": [1, 2]})
        result = ExportUtils.export_csv(df, path)
        assert result == path
        assert pd.read_csv(path).shape == (2, 1)

    def test_export_excel(self, tmp_path):
        path = str(tmp_path / "out.xlsx")
        df = pd.DataFrame({"x": [1, 2]})
        result = ExportUtils.export_excel(df, path)
        assert result == path

    def test_export_json(self, tmp_path):
        path = str(tmp_path / "out.json")
        data = {"x": 1}
        result = ExportUtils.export_json(data, path)
        assert result == path
        with open(path, encoding="utf-8") as f:
            assert json.load(f) == data

    def test_export_html(self, tmp_path):
        path = tmp_path / "out.html"
        df = pd.DataFrame({"x": [1, 2]})
        result = ExportUtils.export_html(df, str(path), title="报表")
        assert result == str(path)
        content = path.read_text(encoding="utf-8")
        assert "报表" in content
        assert "<table" in content

    def test_export_dict_to_csv(self, tmp_path):
        path = str(tmp_path / "dict.csv")
        data = {"city": ["深圳", "广州"], "gdp": [100, 90]}
        result = ExportUtils.export_dict_to_csv(data, path)
        assert result == path

    def test_merge_dataframes(self, tmp_path):
        path = str(tmp_path / "merged.xlsx")
        dfs = {"sheet1": pd.DataFrame({"x": [1]}), "sheet2": pd.DataFrame({"y": [2]})}
        result = ExportUtils.merge_dataframes(dfs, path)
        assert result == path
