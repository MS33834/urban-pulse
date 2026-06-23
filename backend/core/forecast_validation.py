"""
预测准确率验证（Phase 5 — Community validation dashboard）

对已回填真实值的预测快照计算各类准确率指标，
支持按模型、城市、指标维度拆分，用于社区评估与模型选型。
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from backend.core.forecast_archive import ForecastArchive

logger = logging.getLogger(__name__)


@dataclass
class ValidationMetrics:
    """单组验证指标。"""

    count: int
    mae: float | None
    mape: float | None
    rmse: float | None
    bias: float | None
    hit_rate: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "mae": self._fmt(self.mae),
            "mape": self._fmt(self.mape),
            "rmse": self._fmt(self.rmse),
            "bias": self._fmt(self.bias),
            "hit_rate": self._fmt(self.hit_rate),
        }

    @staticmethod
    def _fmt(value: float | None) -> float | None:
        if value is None or not math.isfinite(value):
            return None
        return round(value, 4)


class ForecastValidator:
    """预测准确率验证器。"""

    def __init__(self, archive: ForecastArchive | None = None) -> None:
        self.archive = archive or ForecastArchive()

    def _load_validated(self) -> pd.DataFrame:
        """加载已回填真实值的记录。"""
        df = self.archive.to_dataframe()
        if df.empty:
            return df
        return df[df["actual_value"].notna()].copy()

    @staticmethod
    def compute_metrics(actual: list[float], predicted: list[float]) -> ValidationMetrics:
        """根据 actual / predicted 列表计算指标。"""
        if len(actual) == 0 or len(actual) != len(predicted):
            return ValidationMetrics(count=0, mae=None, mape=None, rmse=None, bias=None, hit_rate=None)

        a = np.asarray(actual, dtype=float)
        p = np.asarray(predicted, dtype=float)
        errors = p - a
        mae = float(np.mean(np.abs(errors)))
        mape = float(np.mean(np.abs(errors / np.where(a == 0, np.nan, a)))) * 100
        rmse = float(np.sqrt(np.mean(errors**2)))
        bias = float(np.mean(errors))
        return ValidationMetrics(count=len(actual), mae=mae, mape=mape, rmse=rmse, bias=bias, hit_rate=None)

    def summary(self) -> ValidationMetrics:
        """总体验证指标。"""
        df = self._load_validated()
        if df.empty:
            return ValidationMetrics(count=0, mae=None, mape=None, rmse=None, bias=None, hit_rate=None)
        return self.compute_metrics(df["actual_value"].tolist(), df["predicted_value"].tolist())

    def by_model(self) -> dict[str, ValidationMetrics]:
        """按模型分组的验证指标。"""
        df = self._load_validated()
        result: dict[str, ValidationMetrics] = {}
        if df.empty:
            return result
        for model, group in df.groupby("model"):
            result[str(model)] = self.compute_metrics(group["actual_value"].tolist(), group["predicted_value"].tolist())
        return dict(sorted(result.items(), key=lambda x: x[1].mae if x[1].mae is not None else float("inf")))

    def by_city(self) -> dict[str, ValidationMetrics]:
        """按城市分组的验证指标。"""
        df = self._load_validated()
        result: dict[str, ValidationMetrics] = {}
        if df.empty:
            return result
        for city, group in df.groupby("city_code"):
            result[str(city)] = self.compute_metrics(group["actual_value"].tolist(), group["predicted_value"].tolist())
        return result

    def by_indicator(self) -> dict[str, ValidationMetrics]:
        """按指标分组的验证指标。"""
        df = self._load_validated()
        result: dict[str, ValidationMetrics] = {}
        if df.empty:
            return result
        for indicator, group in df.groupby("indicator"):
            result[str(indicator)] = self.compute_metrics(
                group["actual_value"].tolist(), group["predicted_value"].tolist()
            )
        return result

    def hit_rate(self) -> dict[str, float]:
        """
        计算预测值落在置信区间内的命中率。

        返回按模型聚合的命中率。
        """
        df = self._load_validated()
        return self._hit_rate_from_df(df)

    def report(self) -> dict[str, Any]:
        """生成完整验证报告（dict 形式）。"""
        df = self._load_validated()
        return {
            "generated_at": pd.Timestamp.now().isoformat(),
            "summary": self._summary_from_df(df).to_dict(),
            "by_model": {k: v.to_dict() for k, v in self._by_group_from_df(df, "model").items()},
            "by_city": {k: v.to_dict() for k, v in self._by_group_from_df(df, "city_code").items()},
            "by_indicator": {k: v.to_dict() for k, v in self._by_group_from_df(df, "indicator").items()},
            "hit_rate_by_model": self._hit_rate_from_df(df),
        }

    def _summary_from_df(self, df: pd.DataFrame) -> ValidationMetrics:
        if df.empty:
            return ValidationMetrics(count=0, mae=None, mape=None, rmse=None, bias=None, hit_rate=None)
        return self.compute_metrics(df["actual_value"].tolist(), df["predicted_value"].tolist())

    def _by_group_from_df(self, df: pd.DataFrame, col: str) -> dict[str, ValidationMetrics]:
        result: dict[str, ValidationMetrics] = {}
        if df.empty:
            return result
        for key, group in df.groupby(col):
            result[str(key)] = self.compute_metrics(group["actual_value"].tolist(), group["predicted_value"].tolist())
        if col == "model":
            result = dict(sorted(result.items(), key=lambda x: x[1].mae if x[1].mae is not None else float("inf")))
        return result

    def _hit_rate_from_df(self, df: pd.DataFrame) -> dict[str, float]:
        result: dict[str, float] = {}
        if df.empty:
            return result
        for model, group in df.groupby("model"):
            # 向量化计算命中率,避免逐行 iterrows。
            ci = group["confidence_interval"]
            valid = ci.apply(lambda x: isinstance(x, (list, tuple)) and len(x) == 2)
            if not valid.any():
                continue
            sub = group[valid]
            actual = sub["actual_value"].to_numpy(dtype=float)
            lower = sub["confidence_interval"].apply(lambda x: x[0]).to_numpy(dtype=float)
            upper = sub["confidence_interval"].apply(lambda x: x[1]).to_numpy(dtype=float)
            total = len(sub)
            if total == 0:
                continue
            hits = int(np.count_nonzero((actual >= lower) & (actual <= upper)))
            result[str(model)] = round(hits / total, 4)
        return result

    def to_json(self, indent: int = 2) -> str:
        """导出为 JSON 字符串。"""
        return json.dumps(self.report(), indent=indent, ensure_ascii=False, default=str)

    def to_markdown(self) -> str:
        """导出为 Markdown 验证报告。"""
        lines: list[str] = ["# Urban Pulse 预测准确率验证报告\n"]
        report = self.report()

        lines.append(f"_生成时间: {report['generated_at']}_\n")

        summary = report["summary"]
        lines.append("## 总体指标\n")
        lines.append(f"- 已验证样本数: {summary['count']}")
        lines.append(f"- MAE: {summary['mae']}")
        lines.append(f"- MAPE: {summary['mape']} %")
        lines.append(f"- RMSE: {summary['rmse']}")
        lines.append(f"- Bias: {summary['bias']}\n")

        def _metrics_table(title: str, data: dict[str, Any]) -> None:
            lines.append(f"## {title}\n")
            if not data:
                lines.append("_暂无数据_\n")
                return
            lines.append("| 维度 | 样本数 | MAE | MAPE | RMSE | Bias |")
            lines.append("|------|--------|-----|------|------|------|")
            for key, metrics in data.items():
                lines.append(
                    f"| {key} | {metrics['count']} | {metrics['mae']} | "
                    f"{metrics['mape']} | {metrics['rmse']} | {metrics['bias']} |"
                )
            lines.append("")

        _metrics_table("按模型", report["by_model"])
        _metrics_table("按城市", report["by_city"])
        _metrics_table("按指标", report["by_indicator"])

        hit_rate = report["hit_rate_by_model"]
        lines.append("## 置信区间命中率（按模型）\n")
        if hit_rate:
            lines.append("| 模型 | 命中率 |")
            lines.append("|------|--------|")
            for model, rate in hit_rate.items():
                lines.append(f"| {model} | {rate} |")
        else:
            lines.append("_暂无置信区间数据_")
        lines.append("")
        return "\n".join(lines)
