"""
数据画像模块

分析数据集的结构特征，为图表推荐器提供输入。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldProfile:
    """单个字段的画像"""

    name: str
    data_type: str  # number | text | time | category | unknown
    non_null_count: int = 0
    unique_count: int = 0
    min_value: float | None = None
    max_value: float | None = None
    sample_values: list[Any] = field(default_factory=list)


@dataclass
class DataProfile:
    """数据集画像"""

    total_rows: int = 0
    total_cols: int = 0
    fields: list[FieldProfile] = field(default_factory=list)
    has_time_dim: bool = False
    time_field: str | None = None
    entity_field: str | None = None
    numeric_fields: list[str] = field(default_factory=list)
    text_fields: list[str] = field(default_factory=list)
    category_fields: list[str] = field(default_factory=list)
    entity_candidates: list[str] = field(default_factory=list)
    time_candidates: list[str] = field(default_factory=list)


def _infer_type(values: Sequence[Any]) -> str:
    """根据样本推断字段类型"""
    non_null = [v for v in values if v is not None and v != ""]
    if not non_null:
        return "unknown"

    # 时间模式识别
    time_keywords = {"year", "month", "date", "time", "day", "quarter", "timestamp"}
    if any(kw in str(non_null[0]).lower() for kw in time_keywords):
        return "time"

    numeric_count = 0
    for v in non_null[:20]:
        try:
            float(v)
            numeric_count += 1
        except (TypeError, ValueError):
            pass

    if numeric_count >= len(non_null[:20]) * 0.8:
        return "number"

    # 类别：去重值少且为文本
    unique_ratio = len(set(str(v) for v in non_null)) / len(non_null)
    if unique_ratio < 0.2:
        return "category"

    return "text"


def _is_time_field(name: str, values: Sequence[Any]) -> bool:
    """判断字段是否为时间字段"""
    name_lower = name.lower()
    time_names = {"year", "month", "date", "time", "quarter", "timestamp"}
    if any(tn in name_lower for tn in time_names):
        return True

    # 尝试解析为年份
    for v in values[:10]:
        if v is None:
            continue
        try:
            iv = int(float(v))
            if 1900 <= iv <= 2100:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _is_entity_field(name: str, values: Sequence[Any]) -> bool:
    """判断字段是否为实体字段（城市/地区/省份等）"""
    name_lower = name.lower()
    entity_names = {"city", "region", "province", "district", "entity", "area", "name", "城市", "省份", "地区"}
    if any(en in name_lower for en in entity_names):
        return True

    # 去重比例低且为文本，可能是实体
    non_null = [v for v in values if v is not None and v != ""]
    if not non_null:
        return False
    unique_ratio = len(set(str(v) for v in non_null)) / len(non_null)
    return 0.05 < unique_ratio < 0.5


def profile_dataset(data: list[dict[str, Any]]) -> DataProfile:
    """
    对数据集进行画像。

    Args:
        data: 数据行列表，每行是一个字典

    Returns:
        DataProfile 对象
    """
    if not data:
        return DataProfile()

    columns = list(data[0].keys())
    total_rows = len(data)
    total_cols = len(columns)

    fields: list[FieldProfile] = []
    numeric_fields: list[str] = []
    text_fields: list[str] = []
    category_fields: list[str] = []
    entity_candidates: list[str] = []
    time_candidates: list[str] = []

    for col in columns:
        values = [row.get(col) for row in data]
        non_null = [v for v in values if v is not None and v != ""]
        data_type = _infer_type(non_null)

        profile = FieldProfile(
            name=col,
            data_type=data_type,
            non_null_count=len(non_null),
            unique_count=len(set(str(v) for v in non_null)),
            sample_values=non_null[:5],
        )

        if data_type == "number":
            numeric_values = []
            for v in non_null:
                try:
                    numeric_values.append(float(v))
                except (TypeError, ValueError):
                    pass
            if numeric_values:
                profile.min_value = min(numeric_values)
                profile.max_value = max(numeric_values)
            numeric_fields.append(col)
        elif data_type == "category":
            category_fields.append(col)
        else:
            text_fields.append(col)

        if _is_time_field(col, values):
            time_candidates.append(col)
            profile.data_type = "time"
        elif _is_entity_field(col, values):
            entity_candidates.append(col)
            profile.data_type = "category"

        fields.append(profile)

    has_time_dim = len(time_candidates) > 0
    time_field = time_candidates[0] if time_candidates else None
    entity_field = entity_candidates[0] if entity_candidates else None

    return DataProfile(
        total_rows=total_rows,
        total_cols=total_cols,
        fields=fields,
        has_time_dim=has_time_dim,
        time_field=time_field,
        entity_field=entity_field,
        numeric_fields=numeric_fields,
        text_fields=text_fields,
        category_fields=category_fields,
        entity_candidates=entity_candidates,
        time_candidates=time_candidates,
    )
