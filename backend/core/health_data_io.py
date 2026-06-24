"""CEHI 指标数据的 Excel/CSV 导入导出工具。

提供：
1. export_indicator_template：根据 YAML 指标体系生成指标录入模板
2. parse_indicator_data：解析用户上传的 Excel/CSV，提取 {indicator_id: value}
"""

from __future__ import annotations

import io
import math
from typing import Literal, cast

import pandas as pd

from backend.core.health_index import CEHIConfig

TEMPLATE_COLUMNS = [
    "indicator_id",
    "indicator_name",
    "dimension",
    "unit",
    "direction",
    "value",
    "year",
    "data_source",
]


def _normalize_columns(columns: list[str]) -> dict[str, str]:
    """返回小写列名到原始列名的映射。"""
    return {str(col).strip().lower(): str(col) for col in columns}


def _detect_id_value_columns(df: pd.DataFrame) -> tuple[str, str]:
    """根据规则检测 indicator_id 列与 value 列。"""
    if df.columns.empty:
        raise ValueError("文件没有列标题")

    norm = _normalize_columns(list(df.columns))

    id_col: str | None = None
    value_col: str | None = None

    for key in ("indicator_id", "indicator id", "指标id", "指标 id", "指标编号"):
        if key in norm:
            id_col = norm[key]
            break

    for key in ("value", "数值", "值", "indicator_value"):
        if key in norm:
            value_col = norm[key]
            break

    if id_col is None or value_col is None:
        # 回退：第一列作为 indicator_id，第二列作为 value
        id_col = str(df.columns[0])
        if len(df.columns) < 2:
            raise ValueError("文件至少需要两列（指标标识与数值）")
        value_col = str(df.columns[1])

    return id_col, value_col


def _read_dataframe(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """根据文件名后缀读取 Excel 或 CSV。"""
    lower_name = filename.lower()
    buffer = io.BytesIO(file_bytes)

    if lower_name.endswith(".xlsx") or lower_name.endswith(".xls"):
        try:
            return pd.read_excel(buffer, engine="openpyxl")
        except Exception as exc:
            raise ValueError(f"无法解析 Excel 文件: {exc}") from exc

    if lower_name.endswith(".csv"):
        # 依次尝试常见编码
        for encoding in ("utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030"):
            try:
                buffer.seek(0)
                return pd.read_csv(buffer, encoding=encoding)
            except UnicodeDecodeError:
                continue
            except pd.errors.EmptyDataError as exc:
                raise ValueError("CSV 文件为空或没有数据行") from exc
            except pd.errors.ParserError:
                continue  # 尝试下一个编码
            except Exception as exc:
                raise ValueError(f"无法解析 CSV 文件: {exc}") from exc
        raise ValueError("CSV 文件编码无法识别，请使用 UTF-8 或 GBK 编码")

    raise ValueError(f"不支持的文件格式: {filename}，请上传 .xlsx 或 .csv 文件")


def export_indicator_template(format: Literal["xlsx", "csv"]) -> bytes:
    """根据 YAML 指标体系列表生成指标录入模板。

    列：indicator_id, indicator_name, dimension, unit, direction, value, year, data_source。
    每个指标一行，value 为空。
    """
    if format not in ("xlsx", "csv"):
        raise ValueError(f"不支持的模板格式: {format}，仅支持 xlsx 或 csv")

    config = CEHIConfig.default()
    rows = []
    for indicator in config.indicators:
        rows.append(
            {
                "indicator_id": indicator.id,
                "indicator_name": indicator.name,
                "dimension": indicator.dimension_id,
                "unit": indicator.unit,
                "direction": indicator.direction,
                "value": None,
                "year": None,
                "data_source": indicator.data_source,
            }
        )

    df = pd.DataFrame(rows, columns=TEMPLATE_COLUMNS)

    if format == "xlsx":
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:  # type: ignore[call-arg]
            df.to_excel(writer, index=False, sheet_name="CEHI 指标录入模板")
        return buffer.getvalue()

    # CSV
    return cast(bytes, df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"))


def parse_indicator_data(file_bytes: bytes, filename: str) -> dict[str, float]:
    """解析用户上传的 Excel/CSV 文件，返回 {indicator_id: value}。

    - 支持 .xlsx 与 .csv
    - 若列名包含 indicator_id / value，则使用这两列；否则使用第一、二列
    - 对空值跳过，对无效数值给出明确错误
    """
    if not file_bytes:
        raise ValueError("上传文件为空")

    df = _read_dataframe(file_bytes, filename)

    if df.empty:
        raise ValueError("文件没有数据行")

    id_col, value_col = _detect_id_value_columns(df)

    result: dict[str, float] = {}
    invalid_rows: list[str] = []

    for idx, row in df.iterrows():
        row_num = int(cast(int, idx)) + 2  # Excel/用户视角从 1 开始，第 1 行是标题
        raw_id = row.get(id_col)
        raw_value = row.get(value_col)

        if pd.isna(raw_id):
            continue

        indicator_id = str(raw_id).strip()
        if not indicator_id:
            continue

        if pd.isna(raw_value):
            # 空值不报错，由调用方在 missing 中体现
            continue

        try:
            value = float(raw_value)
        except (ValueError, TypeError):
            invalid_rows.append(f"第 {row_num} 行 ({indicator_id}): {raw_value!r}")
            continue

        if not _is_finite_float(value):
            invalid_rows.append(f"第 {row_num} 行 ({indicator_id}): {raw_value!r} (非有限数值)")
            continue

        result[indicator_id] = value

    if invalid_rows:
        raise ValueError("以下行包含无效数值，请修正后重新上传:\n" + "\n".join(invalid_rows))

    return result


def _is_finite_float(value: float) -> bool:
    """检查浮点数是否为有限值。"""
    return math.isfinite(value)
