"""
社会实践与调查数据采集器

支持从 CSV/Excel 加载调查数据，按标准格式（区域编码、年份、指标、数值）
接入区域注册表，实现民意调查、社会感知、田野调查等数据与城市经济预测的关联。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

import pandas as pd

from backend.data_collection.base_collector import BaseCollector

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"region_code", "year", "indicator", "value"}
OPTIONAL_COLUMNS = {"region_name", "source", "survey_type", "unit", "notes"}
SUPPORTED_INDICATOR_TYPES = {
    "social_satisfaction",
    "public_service_score",
    "employment_confidence",
    "housing_pressure",
    "environment_satisfaction",
    "traffic_satisfaction",
    "health_satisfaction",
    "education_satisfaction",
    "migration_intent",
    "custom",
}


class SurveyCollector(BaseCollector):
    """
    调查数据采集器

    预期输入格式（CSV/Excel）：
        region_code, year, indicator, value, [source], [survey_type], [unit], [notes]

    示例：
        CN-GD-SZ, 2023, social_satisfaction, 78.5, 深圳市统计局, 社会调查, 分, 随机抽样 n=2000
    """

    def __init__(self, source_name: str = "survey") -> None:
        super().__init__()
        self.source_name = source_name
        self._records: list[dict[str, Any]] = []

    def load_file(self, path: Path | str) -> list[dict[str, Any]]:
        """从 CSV 或 Excel 文件加载调查数据"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"调查数据文件不存在: {path}")

        suffix = path.suffix.lower()
        if suffix == ".csv":
            df = pd.read_csv(path, dtype={"region_code": str})
        elif suffix in (".xlsx", ".xls"):
            df = pd.read_excel(path, dtype={"region_code": str})
        else:
            raise ValueError(f"不支持的调查数据格式: {suffix}")

        return self.load_dataframe(df)

    def load_dataframe(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """从 pandas DataFrame 加载并校验调查数据"""
        columns = set(df.columns)
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"调查数据缺少必要列: {sorted(missing)}")

        records: list[dict[str, Any]] = []
        for idx, row in df.iterrows():
            record = self._parse_row(row)
            if record is not None:
                records.append(record)
            else:
                row_index = cast(int, idx)
                logger.warning(f"跳过第 {row_index + 1} 行无效调查数据")

        self._records.extend(records)
        logger.info(f"成功加载 {len(records)} 条调查数据记录")
        return records

    def fetch_data(self, **kwargs) -> list[dict[str, Any]]:
        """BaseCollector 接口：按路径加载数据"""
        path = kwargs.get("path")
        if path is None:
            raise ValueError("SurveyCollector.fetch_data 需要提供 path 参数")
        return self.load_file(path)

    def fetch_all(self, indicators: list[str] | None = None) -> dict[str, list[dict]]:
        """BaseCollector 接口：按指标分组返回数据"""
        result: dict[str, list[dict]] = {}
        for record in self._records:
            indicator = str(record["indicator"])
            if indicators is not None and indicator not in indicators:
                continue
            result.setdefault(indicator, []).append(record)
        return result

    def list_indicators(self) -> list[str]:
        """返回已加载的所有指标名"""
        return sorted({str(r["indicator"]) for r in self._records})

    def by_region(self, region_code: str) -> list[dict[str, Any]]:
        """返回指定区域的所有调查记录"""
        return [r for r in self._records if r["region_code"] == region_code]

    def clear(self) -> None:
        """清空已加载记录"""
        self._records.clear()

    def _parse_row(self, row: pd.Series) -> dict[str, Any] | None:
        """解析并校验单行数据"""
        region_code = str(row.get("region_code", "")).strip()
        if not region_code:
            return None

        year = row.get("year")
        try:
            year = int(cast(Any, year))
        except (TypeError, ValueError):
            return None

        indicator = str(row.get("indicator", "")).strip()
        if not indicator:
            return None

        value = row.get("value")
        try:
            value = float(cast(Any, value))
        except (TypeError, ValueError):
            return None

        record: dict[str, Any] = {
            "region_code": region_code,
            "year": year,
            "indicator": indicator,
            "value": value,
            "source": self.source_name,
            "survey_type": "survey",
        }

        for col in OPTIONAL_COLUMNS:
            if col in row and pd.notna(row[col]):
                record[col] = row[col]

        return record
