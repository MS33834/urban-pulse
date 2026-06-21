"""CEHI 指标数据导入导出工具测试。"""

from __future__ import annotations

import io

import pandas as pd
import pytest

from backend.core.health_data_io import (
    export_indicator_template,
    parse_indicator_data,
)
from backend.core.health_index import CEHIConfig


class TestExportIndicatorTemplate:
    """模板导出测试。"""

    @pytest.mark.parametrize("fmt", ["xlsx", "csv"])
    def test_export_template_returns_bytes(self, fmt: str):
        """导出结果为非空 bytes。"""
        content = export_indicator_template(fmt)  # type: ignore[arg-type]
        assert isinstance(content, bytes)
        assert len(content) > 0

    def test_export_template_csv_columns(self):
        """CSV 模板包含预期列与全部指标。"""
        content = export_indicator_template("csv")
        df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
        config = CEHIConfig.default()

        expected_columns = [
            "indicator_id",
            "indicator_name",
            "dimension",
            "unit",
            "direction",
            "value",
            "year",
            "data_source",
        ]
        assert list(df.columns) == expected_columns
        assert len(df) == len(config.indicators)
        assert df["indicator_id"].isna().sum() == 0
        assert df["value"].isna().all()

    def test_export_template_xlsx_columns(self):
        """Excel 模板包含预期列与全部指标。"""
        content = export_indicator_template("xlsx")
        df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
        config = CEHIConfig.default()

        expected_columns = [
            "indicator_id",
            "indicator_name",
            "dimension",
            "unit",
            "direction",
            "value",
            "year",
            "data_source",
        ]
        assert list(df.columns) == expected_columns
        assert len(df) == len(config.indicators)
        assert df["value"].isna().all()

    def test_export_template_invalid_format(self):
        """不支持格式抛出 ValueError。"""
        with pytest.raises(ValueError, match="不支持的模板格式"):
            export_indicator_template("pdf")  # type: ignore[arg-type]


class TestParseIndicatorData:
    """指标数据解析测试。"""

    def test_parse_csv_with_named_columns(self):
        """CSV 列名包含 indicator_id 与 value 时正确解析。"""
        csv = "indicator_id,value\ngdp_growth,5.8\ndebt_ratio,200\n"
        result = parse_indicator_data(csv.encode("utf-8"), "data.csv")
        assert result == {"gdp_growth": 5.8, "debt_ratio": 200.0}

    def test_parse_csv_fallback_columns(self):
        """CSV 没有标准列名时回退到第一、二列。"""
        csv = "指标,数值\ngdp_growth,5.8\n"
        result = parse_indicator_data(csv.encode("utf-8"), "data.csv")
        assert result == {"gdp_growth": 5.8}

    def test_parse_xlsx_with_named_columns(self):
        """Excel 列名包含 indicator_id 与 value 时正确解析。"""
        df = pd.DataFrame({"indicator_id": ["gdp_growth", "debt_ratio"], "value": [5.8, 200]})
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        result = parse_indicator_data(buffer.read(), "data.xlsx")
        assert result == {"gdp_growth": 5.8, "debt_ratio": 200.0}

    def test_parse_xlsx_fallback_columns(self):
        """Excel 没有标准列名时回退到第一、二列。"""
        df = pd.DataFrame({"指标": ["gdp_growth"], "数值": [5.8]})
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        result = parse_indicator_data(buffer.read(), "data.xlsx")
        assert result == {"gdp_growth": 5.8}

    def test_parse_skips_empty_value_rows(self):
        """空 value 行被跳过，不报错。"""
        csv = "indicator_id,value\ngdp_growth,\ndebt_ratio,200\n"
        result = parse_indicator_data(csv.encode("utf-8"), "data.csv")
        assert result == {"debt_ratio": 200.0}

    def test_parse_invalid_value_raises(self):
        """无效数值抛出明确 ValueError。"""
        csv = "indicator_id,value\ngdp_growth,abc\n"
        with pytest.raises(ValueError, match="无效数值"):
            parse_indicator_data(csv.encode("utf-8"), "data.csv")

    def test_parse_empty_file_raises(self):
        """空文件 bytes 抛出 ValueError。"""
        with pytest.raises(ValueError, match="上传文件为空"):
            parse_indicator_data(b"", "data.csv")

    def test_parse_empty_csv_raises(self):
        """仅标题行的 CSV 抛出 ValueError。"""
        csv = "indicator_id,value\n"
        with pytest.raises(ValueError, match="文件没有数据行"):
            parse_indicator_data(csv.encode("utf-8"), "data.csv")

    def test_parse_unsupported_extension_raises(self):
        """不支持的文件扩展名抛出 ValueError。"""
        with pytest.raises(ValueError, match="不支持的文件格式"):
            parse_indicator_data(b"data", "data.pdf")

    def test_parse_gbk_csv(self):
        """GBK 编码 CSV 可正确解析。"""
        csv = "indicator_id,value\ngdp_growth,5.8\n".encode("gbk")
        result = parse_indicator_data(csv, "data.csv")
        assert result == {"gdp_growth": 5.8}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
