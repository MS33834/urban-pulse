"""
基础分析器 - 定义通用分析流程接口
所有场景分析器（零售选址、销售预测、企业分析、政府分析）都应继承此基类
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class AnalysisPlugin(ABC):
    """
    插件化分析器基类。

    与 BaseAnalyzer 面向 DataFrame 工作流的接口不同，AnalysisPlugin 面向
    city_data 字典，便于通过 drop-in 文件扩展新的城市经济分析方法。
    """

    @abstractmethod
    def name(self) -> str:
        """分析器名称。"""
        ...

    @abstractmethod
    def required_indicators(self) -> list[str]:
        """运行该分析所需的经济指标代码列表。"""
        ...

    @abstractmethod
    def analyze(self, city_data: dict, **params) -> dict:
        """
        执行分析。

        Args:
            city_data: 包含城市指标数据的字典
            **params: 分析参数

        Returns:
            分析结果字典
        """
        ...


class BaseAnalyzer(ABC):
    def __init__(self):
        self.name = self.__class__.__name__
        self.raw_data: pd.DataFrame | None = None
        self.cleaned_data: pd.DataFrame | None = None
        self.processed_data: pd.DataFrame | None = None
        self.analysis_result: dict[str, Any] | None = None

    @abstractmethod
    def run_full_analysis(
        self, data: pd.DataFrame, save_results: bool = True, output_dir: str = "data/output", **kwargs
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def predict(self, data: pd.DataFrame) -> Any:
        pass

    def get_analysis_result(self) -> dict[str, Any] | None:
        return self.analysis_result

    def summarize_data(self, df: pd.DataFrame) -> dict[str, Any]:
        summary = {
            "shape": df.shape,
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "memory_usage_mb": float(df.memory_usage(deep=True).sum() / 1024 / 1024),
        }

        numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
        if len(numeric_cols) > 0:
            summary["numeric_summary"] = df[numeric_cols].describe().to_dict()

        return summary

    def calculate_growth_rates(self, df: pd.DataFrame, value_col: str, time_col: str, periods: int = 1) -> pd.DataFrame:
        df_sorted = df.sort_values(time_col).copy()
        # 用 NaN 替换 0 避免 pct_change 产生 inf
        df_sorted[f"{value_col}_growth"] = df_sorted[value_col].replace(0, np.nan).pct_change(periods=periods) * 100
        return df_sorted

    def calculate_moving_average(self, df: pd.DataFrame, value_col: str, window: int = 4) -> pd.DataFrame:
        df_ma = df.copy()
        df_ma[f"{value_col}_ma{window}"] = df_ma[value_col].rolling(window=window).mean()
        return df_ma

    def calculate_correlation(self, df: pd.DataFrame) -> pd.DataFrame:
        numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
        return df[numeric_cols].corr()

    def detect_trend(self, df: pd.DataFrame, value_col: str, time_col: str) -> dict[str, Any]:
        df_sorted = df.sort_values(time_col).copy()
        values = df_sorted[value_col].dropna()

        if len(values) < 2:
            return {"trend": "insufficient_data"}

        first = values.iloc[0]
        last = values.iloc[-1]

        if last > first:
            trend = "upward"
        elif last < first:
            trend = "downward"
        else:
            trend = "flat"

        return {
            "trend": trend,
            "change_pct": ((last - first) / first * 100) if first != 0 else None,
            "first_value": first,
            "last_value": last,
        }

    def data_quality_check(self, df: pd.DataFrame) -> dict[str, Any]:
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = df.isnull().sum().sum()
        completeness = (1 - missing_cells / total_cells) * 100 if total_cells > 0 else 0

        numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
        outlier_count = 0
        for col in numeric_cols:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            outlier_count += int(((df[col] < (q1 - 1.5 * iqr)) | (df[col] > (q3 + 1.5 * iqr))).sum())

        duplicate_rows = df.duplicated().sum()

        # 异常值比率分母应为总单元格数（行数×数值列数），而非行数
        total_numeric_cells = len(df) * len(numeric_cols) if len(numeric_cols) > 0 else 1
        outlier_ratio = min(outlier_count / total_numeric_cells * 100, 100) if total_numeric_cells > 0 else 0
        quality_score = min(
            100,
            (
                completeness * 0.5
                + (100 - outlier_ratio) * 0.3
                + (100 - min(duplicate_rows / max(len(df), 1) * 100, 100)) * 0.2
            ),
        )

        return {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "missing_cells": int(missing_cells),
            "completeness_pct": round(completeness, 2),
            "outlier_count": int(outlier_count),
            "duplicate_rows": int(duplicate_rows),
            "overall_quality": {
                "quality_score": round(quality_score, 1),
                "level": "excellent"
                if quality_score >= 90
                else "good"
                if quality_score >= 75
                else "fair"
                if quality_score >= 60
                else "poor",
            },
        }
