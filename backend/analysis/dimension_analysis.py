"""
灵活的维度分析框架
支持自定义分析维度和多维度组合分析
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, cast

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """分析类型"""

    DESCRIPTIVE = "descriptive"  # 描述性分析
    COMPARATIVE = "comparative"  # 对比分析
    TREND = "trend"  # 趋势分析
    CORRELATION = "correlation"  # 相关性分析
    DISTRIBUTION = "distribution"  # 分布分析
    BREAKDOWN = "breakdown"  # 分解分析
    FORECAST = "forecast"  # 预测分析
    BENCHMARK = "benchmark"  # 标杆分析
    CUSTOM = "custom"  # 自定义分析


@dataclass
class DimensionDefinition:
    """维度定义"""

    code: str  # 维度代码
    name: str  # 维度名称
    data_fields: list[str]  # 所需数据字段
    analysis_type: AnalysisType  # 分析类型
    aggregator: str | None = None  # 聚合方式: sum, avg, count, min, max
    filters: dict[str, Any] | None = None  # 过滤条件
    group_by: list[str] | None = None  # 分组字段
    metadata: dict[str, Any] = field(default_factory=dict)  # 额外配置


@dataclass
class AnalysisResult:
    """分析结果"""

    dimension_code: str
    analysis_type: AnalysisType
    raw_data: Any
    summary: dict[str, Any]
    insights: list[str]
    visualizations: list[str]  # 可视化类型列表
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_code": self.dimension_code,
            "analysis_type": self.analysis_type.value,
            "summary": self.summary,
            "insights": self.insights,
            "visualizations": self.visualizations,
            "metadata": self.metadata,
        }


class BaseAnalyzer:
    """分析器基类"""

    def __init__(self, dimension: DimensionDefinition):
        self.dimension = dimension
        self.name = dimension.name

    def analyze(self, data: pd.DataFrame | dict[str, Any]) -> AnalysisResult:
        """执行分析"""
        raise NotImplementedError

    def preprocess(self, data: pd.DataFrame | dict[str, Any]) -> pd.DataFrame:
        """数据预处理"""
        if isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            df = data.copy()

        # 应用过滤器
        if self.dimension.filters:
            for col, value in self.dimension.filters.items():
                if col in df.columns:
                    df = df[df[col] == value]

        return df


class DescriptiveAnalyzer(BaseAnalyzer):
    """描述性分析器"""

    def analyze(self, data: pd.DataFrame | dict[str, Any]) -> AnalysisResult:
        df = self.preprocess(data)

        summary = {}
        for field_name in self.dimension.data_fields:
            if field_name in df.columns:
                col_data = df[field_name].dropna()
                if len(col_data) > 0:
                    summary[field_name] = {
                        "count": int(len(col_data)),
                        "mean": float(col_data.mean()),
                        "median": float(col_data.median()),
                        "std": float(col_data.std()) if len(col_data) > 1 else 0,
                        "min": float(col_data.min()),
                        "max": float(col_data.max()),
                        "sum": float(col_data.sum()),
                    }

        insights = []
        for field_name, field_stats in summary.items():
            if field_stats["std"] == 0:
                insights.append(f"{field_name} 保持稳定，无显著变化")
            elif field_stats["max"] > field_stats["mean"] * 2:
                insights.append(
                    f"{field_name} 存在较大波动，峰值是均值的 {field_stats['max'] / field_stats['mean']:.1f} 倍"
                )

        return AnalysisResult(
            dimension_code=self.dimension.code,
            analysis_type=self.dimension.analysis_type,
            raw_data=df,
            summary=summary,
            insights=insights,
            visualizations=["histogram", "boxplot", "summary_table"],
        )


class ComparativeAnalyzer(BaseAnalyzer):
    """对比分析器"""

    def __init__(self, dimension: DimensionDefinition):
        super().__init__(dimension)
        self.compare_fields = dimension.metadata.get("compare_fields", [])

    def analyze(self, data: pd.DataFrame | dict[str, Any]) -> AnalysisResult:
        df = self.preprocess(data)

        summary = {}
        if self.dimension.group_by and self.dimension.group_by[0] in df.columns:
            group_col = self.dimension.group_by[0]
            for field in self.dimension.data_fields:
                if field in df.columns:
                    grouped = df.groupby(group_col)[field].agg(["mean", "sum", "count"])
                    summary[field] = grouped.to_dict()

        # 计算差异
        insights = []
        for field in self.dimension.data_fields:
            if field in summary and "mean" in summary[field]:
                means = list(summary[field]["mean"].values())
                if len(means) >= 2:
                    max_mean = max(means)
                    min_mean = min(means)
                    diff_pct = (max_mean - min_mean) / min_mean * 100 if min_mean != 0 else 0
                    insights.append(f"{field} 极差为 {diff_pct:.1f}%，最大/最小比值 {max_mean / min_mean:.2f}")

        return AnalysisResult(
            dimension_code=self.dimension.code,
            analysis_type=self.dimension.analysis_type,
            raw_data=df,
            summary=summary,
            insights=insights,
            visualizations=["bar_chart", "comparison_table", "radar_chart"],
        )


class TrendAnalyzer(BaseAnalyzer):
    """趋势分析器"""

    def analyze(self, data: pd.DataFrame | dict[str, Any]) -> AnalysisResult:
        df = self.preprocess(data)

        # 确保按时间排序
        time_col = self.dimension.metadata.get("time_col", "year")
        if time_col in df.columns:
            df = df.sort_values(time_col)

        summary = {}
        for field_name in self.dimension.data_fields:
            if field_name in df.columns:
                values = cast(np.ndarray, np.asarray(df[field_name].dropna(), dtype=float))
                if len(values) >= 2:
                    # 计算趋势
                    x = np.arange(len(values))
                    coeffs = np.polyfit(x, values, 1)
                    slope = coeffs[0]

                    # 计算增长率
                    growth_rate = (values[-1] - values[0]) / values[0] * 100 if values[0] != 0 else 0

                    summary[field_name] = {
                        "trend_direction": "up" if slope > 0 else "down",
                        "slope": float(slope),
                        "total_change": float(values[-1] - values[0]),
                        "total_change_pct": float(growth_rate),
                        "values": values.tolist(),
                    }

        insights = []
        for field_name, field_stats in summary.items():
            direction = "上升" if field_stats["trend_direction"] == "up" else "下降"
            insights.append(f"{field_name} 呈{direction}趋势，累计变化 {field_stats['total_change_pct']:.1f}%")

        return AnalysisResult(
            dimension_code=self.dimension.code,
            analysis_type=self.dimension.analysis_type,
            raw_data=df,
            summary=summary,
            insights=insights,
            visualizations=["line_chart", "area_chart", "trend_indicator"],
        )


class CorrelationAnalyzer(BaseAnalyzer):
    """相关性分析器"""

    def analyze(self, data: pd.DataFrame | dict[str, Any]) -> AnalysisResult:
        df = self.preprocess(data)

        # 选择数值列
        numeric_cols = df[self.dimension.data_fields].select_dtypes(include=[np.number]).columns.tolist()

        correlation_matrix = df[numeric_cols].corr() if len(numeric_cols) > 0 else pd.DataFrame()

        # 找出强相关
        strong_correlations: list[dict[str, Any]] = []
        if not correlation_matrix.empty:
            for i in range(len(numeric_cols)):
                for j in range(i + 1, len(numeric_cols)):
                    corr = cast(float, correlation_matrix.iloc[i, j])
                    if abs(corr) > 0.7:
                        strong_correlations.append(
                            {
                                "var1": numeric_cols[i],
                                "var2": numeric_cols[j],
                                "correlation": corr,
                                "strength": "强正相关" if corr > 0 else "强负相关",
                            }
                        )

        summary = {
            "correlation_matrix": correlation_matrix.to_dict(),
            "strong_correlations": strong_correlations,
            "total_pairs": len(numeric_cols) * (len(numeric_cols) - 1) // 2,
        }

        insights = []
        for corr_info in strong_correlations:
            insights.append(
                f"{corr_info['var1']} 与 {corr_info['var2']} 存在{corr_info['strength']}（r={corr_info['correlation']:.2f}）"
            )

        if not strong_correlations:
            insights.append("未发现显著相关关系")

        return AnalysisResult(
            dimension_code=self.dimension.code,
            analysis_type=self.dimension.analysis_type,
            raw_data=df,
            summary=summary,
            insights=insights,
            visualizations=["heatmap", "scatter_plot", "correlation_matrix"],
        )


class DistributionAnalyzer(BaseAnalyzer):
    """分布分析器：描述数据分布形态、偏度、峰度与分位数。"""

    def analyze(self, data: pd.DataFrame | dict[str, Any]) -> AnalysisResult:
        df = self.preprocess(data)

        summary: dict[str, Any] = {}
        for field_name in self.dimension.data_fields:
            if field_name not in df.columns:
                continue
            col_data = df[field_name].dropna()
            if len(col_data) == 0:
                continue

            values = np.asarray(col_data, dtype=float)
            summary[field_name] = {
                "count": int(len(values)),
                "mean": float(np.mean(values)),
                "median": float(np.median(values)),
                "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "q1": float(np.percentile(values, 25)),
                "q3": float(np.percentile(values, 75)),
                "iqr": float(np.percentile(values, 75) - np.percentile(values, 25)),
                "skewness": float(stats.skew(values)) if len(values) > 2 else 0.0,
                "kurtosis": float(stats.kurtosis(values)) if len(values) > 2 else 0.0,
            }

        insights: list[str] = []
        for field_name, stats_dict in summary.items():
            skew = stats_dict["skewness"]
            if abs(skew) > 1:
                direction = "右偏" if skew > 0 else "左偏"
                insights.append(f"{field_name} 分布明显{direction}（偏度={skew:.2f}）")
            elif abs(skew) > 0.5:
                direction = "右偏" if skew > 0 else "左偏"
                insights.append(f"{field_name} 分布轻度{direction}（偏度={skew:.2f}）")
            else:
                insights.append(f"{field_name} 分布基本对称（偏度={skew:.2f}）")

            kurt = stats_dict["kurtosis"]
            if kurt > 1:
                insights.append(f"{field_name} 分布峰度较高（峰度={kurt:.2f}），尾部较厚")
            elif kurt < -1:
                insights.append(f"{field_name} 分布峰度较低（峰度={kurt:.2f}），尾部较薄")

        return AnalysisResult(
            dimension_code=self.dimension.code,
            analysis_type=self.dimension.analysis_type,
            raw_data=df,
            summary=summary,
            insights=insights,
            visualizations=["histogram", "boxplot", "kde"],
        )


class BreakdownAnalyzer(BaseAnalyzer):
    """分解分析器：按分组计算结构占比，或按时间计算增长贡献。"""

    def analyze(self, data: pd.DataFrame | dict[str, Any]) -> AnalysisResult:
        df = self.preprocess(data)

        summary: dict[str, Any] = {}
        group_by = self.dimension.group_by[0] if self.dimension.group_by else None

        if group_by and group_by in df.columns:
            # 结构分解：每个分组占总量的比例
            for field_name in self.dimension.data_fields:
                if field_name not in df.columns:
                    continue
                grouped = df.groupby(group_by)[field_name].sum()
                total = grouped.sum()
                if total == 0:
                    continue
                summary[field_name] = {
                    "total": float(total),
                    "components": {
                        str(k): {"value": float(v), "share_pct": round(float(v) / total * 100, 2)}
                        for k, v in grouped.items()
                    },
                }
        else:
            # 时间分解：逐期增长贡献
            time_col = self.dimension.metadata.get("time_col", "year")
            if time_col in df.columns:
                df = df.sort_values(time_col)
            for field_name in self.dimension.data_fields:
                if field_name not in df.columns:
                    continue
                values = np.asarray(df[field_name].dropna(), dtype=float)
                if len(values) < 2:
                    continue
                changes = np.diff(values)
                total_change = float(values[-1] - values[0])
                summary[field_name] = {
                    "total_change": total_change,
                    "total_change_pct": round(total_change / values[0] * 100, 2) if values[0] != 0 else 0.0,
                    "period_changes": [round(float(c), 4) for c in changes],
                    "avg_period_change": round(float(np.mean(changes)), 4),
                }

        insights: list[str] = []
        for field_name, field_summary in summary.items():
            if "components" in field_summary:
                components = field_summary["components"]
                if components:
                    max_component = max(components.items(), key=lambda x: x[1]["share_pct"])
                    insights.append(
                        f"{field_name} 中 {max_component[0]} 占比最高（{max_component[1]['share_pct']:.1f}%）"
                    )
            elif "total_change" in field_summary:
                direction = "增长" if field_summary["total_change"] > 0 else "下降"
                insights.append(f"{field_name} 累计{direction} {abs(field_summary['total_change_pct']):.1f}%")

        return AnalysisResult(
            dimension_code=self.dimension.code,
            analysis_type=self.dimension.analysis_type,
            raw_data=df,
            summary=summary,
            insights=insights,
            visualizations=["pie_chart", "stacked_bar", "waterfall"],
        )


class ForecastAnalyzer(BaseAnalyzer):
    """预测分析器：基于现有预测引擎对时间序列做未来 N 年预测。"""

    def analyze(self, data: pd.DataFrame | dict[str, Any]) -> AnalysisResult:
        from backend.core.forecast_engine import (
            arima_forecast,
            ensemble_forecast,
            ets_forecast,
            linear_regression_forecast,
        )

        df = self.preprocess(data)
        time_col = self.dimension.metadata.get("time_col", "year")
        forecast_years = int(self.dimension.metadata.get("forecast_years", 5))

        if time_col in df.columns:
            df = df.sort_values(time_col)

        summary: dict[str, Any] = {}
        for field_name in self.dimension.data_fields:
            if field_name not in df.columns:
                continue
            values = [float(v) for v in df[field_name].dropna().tolist()]
            if len(values) < 3:
                summary[field_name] = {"error": "数据不足，无法预测"}
                continue

            arima = arima_forecast(values, forecast_years)
            ets = ets_forecast(values, forecast_years)
            lr = linear_regression_forecast(values, forecast_years)
            ensemble = ensemble_forecast(arima, ets, lr)

            summary[field_name] = {
                "historical_values": values,
                "forecast_values": ensemble["predictions"],
                "lower_ci": ensemble["lower_ci"],
                "upper_ci": ensemble["upper_ci"],
                "weights": ensemble["weights"],
                "method": ensemble["method"],
                "forecast_years": forecast_years,
            }

        insights: list[str] = []
        for field_name, field_summary in summary.items():
            if "error" in field_summary:
                insights.append(f"{field_name}: {field_summary['error']}")
                continue
            hist = field_summary["historical_values"]
            fc = field_summary["forecast_values"]
            if not hist or not fc:
                continue
            change_pct = (fc[-1] - hist[-1]) / hist[-1] * 100 if hist[-1] != 0 else 0.0
            direction = "上升" if change_pct > 0 else "下降"
            insights.append(f"{field_name} 预测未来 {forecast_years} 年{direction} {abs(change_pct):.1f}%")

        return AnalysisResult(
            dimension_code=self.dimension.code,
            analysis_type=self.dimension.analysis_type,
            raw_data=df,
            summary=summary,
            insights=insights,
            visualizations=["line_chart", "fan_chart", "forecast_table"],
        )


class BenchmarkAnalyzer(BaseAnalyzer):
    """标杆分析器：将实际值与目标/基准值对比，计算达成率与差距。"""

    def analyze(self, data: pd.DataFrame | dict[str, Any]) -> AnalysisResult:
        df = self.preprocess(data)
        benchmarks = self.dimension.metadata.get("benchmarks", {})
        group_by = self.dimension.group_by[0] if self.dimension.group_by else None

        summary: dict[str, Any] = {}

        if group_by and group_by in df.columns:
            # 分组标杆：找出每组中表现最好的作为标杆
            for field_name in self.dimension.data_fields:
                if field_name not in df.columns:
                    continue
                grouped = df.groupby(group_by)[field_name].mean()
                if grouped.empty:
                    continue
                best_value = grouped.max()
                best_group = grouped.idxmax()
                summary[field_name] = {
                    "best_group": str(best_group),
                    "best_value": float(best_value),
                    "groups": {
                        str(k): {
                            "value": float(v),
                            "gap_to_best": round(float(best_value - v), 4),
                            "achievement_pct": round(float(v) / best_value * 100, 2) if best_value != 0 else 0.0,
                        }
                        for k, v in grouped.items()
                    },
                }
        else:
            # 与预设目标对比
            for field_name in self.dimension.data_fields:
                if field_name not in df.columns:
                    continue
                target = benchmarks.get(field_name)
                if target is None:
                    continue
                col_data = df[field_name].dropna()
                if col_data.empty:
                    continue
                latest = float(col_data.iloc[-1])
                summary[field_name] = {
                    "target": float(target),
                    "latest": latest,
                    "gap": round(latest - float(target), 4),
                    "achievement_pct": round(latest / float(target) * 100, 2) if target != 0 else 0.0,
                }

        insights: list[str] = []
        for field_name, field_summary in summary.items():
            if "best_group" in field_summary:
                insights.append(
                    f"{field_name} 标杆为 {field_summary['best_group']}（{field_summary['best_value']:.2f}）"
                )
            elif "target" in field_summary:
                ach = field_summary["achievement_pct"]
                if ach >= 100:
                    insights.append(f"{field_name} 已达成目标（{ach:.1f}%）")
                else:
                    insights.append(f"{field_name} 距目标还差 {100 - ach:.1f}%")

        return AnalysisResult(
            dimension_code=self.dimension.code,
            analysis_type=self.dimension.analysis_type,
            raw_data=df,
            summary=summary,
            insights=insights,
            visualizations=["bullet_chart", "gap_bar", "ranking_table"],
        )


class CustomAnalyzer(BaseAnalyzer):
    """自定义分析器：按 metadata 中指定的 aggregator 执行聚合，或返回原始统计。"""

    def analyze(self, data: pd.DataFrame | dict[str, Any]) -> AnalysisResult:
        df = self.preprocess(data)
        aggregator = self.dimension.metadata.get("aggregator", "descriptive")

        summary: dict[str, Any] = {}
        for field_name in self.dimension.data_fields:
            if field_name not in df.columns:
                continue
            col_data = df[field_name].dropna()
            if col_data.empty:
                continue

            values = np.asarray(col_data, dtype=float)
            result: float | dict[str, Any]
            if aggregator == "sum":
                result = float(np.sum(values))
            elif aggregator == "avg":
                result = float(np.mean(values))
            elif aggregator == "max":
                result = float(np.max(values))
            elif aggregator == "min":
                result = float(np.min(values))
            elif aggregator == "count":
                result = int(len(values))
            else:
                # 默认描述性统计
                result = {
                    "count": int(len(values)),
                    "mean": float(np.mean(values)),
                    "median": float(np.median(values)),
                    "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                }

            summary[field_name] = {"aggregator": aggregator, "value": result}

        insights: list[str] = [f"自定义分析（{aggregator}）完成，覆盖 {len(summary)} 个字段"]

        return AnalysisResult(
            dimension_code=self.dimension.code,
            analysis_type=self.dimension.analysis_type,
            raw_data=df,
            summary=summary,
            insights=insights,
            visualizations=["custom_table"],
        )


class DimensionAnalyzerFactory:
    """维度分析器工厂"""

    _analyzers: dict[AnalysisType, type[BaseAnalyzer]] = {
        AnalysisType.DESCRIPTIVE: DescriptiveAnalyzer,
        AnalysisType.COMPARATIVE: ComparativeAnalyzer,
        AnalysisType.TREND: TrendAnalyzer,
        AnalysisType.CORRELATION: CorrelationAnalyzer,
        AnalysisType.DISTRIBUTION: DistributionAnalyzer,
        AnalysisType.BREAKDOWN: BreakdownAnalyzer,
        AnalysisType.FORECAST: ForecastAnalyzer,
        AnalysisType.BENCHMARK: BenchmarkAnalyzer,
        AnalysisType.CUSTOM: CustomAnalyzer,
    }

    @classmethod
    def register(cls, analysis_type: AnalysisType, analyzer_class: type):
        """注册自定义分析器"""
        cls._analyzers[analysis_type] = analyzer_class

    @classmethod
    def create(cls, dimension: DimensionDefinition) -> BaseAnalyzer:
        """创建分析器"""
        analyzer_class = cls._analyzers.get(dimension.analysis_type, DescriptiveAnalyzer)
        return analyzer_class(dimension)


class FlexibleAnalysisEngine:
    """灵活的维度分析引擎"""

    def __init__(self):
        self._dimensions: dict[str, DimensionDefinition] = {}
        self._results_cache: dict[str, AnalysisResult] = {}

        self._initialize_default_dimensions()

    def _initialize_default_dimensions(self):
        """初始化默认维度"""
        default_dimensions = [
            DimensionDefinition(
                code="macro_overview",
                name="宏观经济概览",
                data_fields=["gdp", "gdp_growth", "cpi", "pmi"],
                analysis_type=AnalysisType.DESCRIPTIVE,
            ),
            DimensionDefinition(
                code="industry_comparison",
                name="产业对比分析",
                data_fields=["output_value", "growth_rate", "market_share"],
                analysis_type=AnalysisType.COMPARATIVE,
                group_by=["industry"],
            ),
            DimensionDefinition(
                code="cost_trend",
                name="成本趋势分析",
                data_fields=["land_cost", "labor_cost", "energy_cost"],
                analysis_type=AnalysisType.TREND,
                metadata={"time_col": "year"},
            ),
            DimensionDefinition(
                code="factor_correlation",
                name="要素相关性分析",
                data_fields=["gdp", "investment", "employment", "rd_intensity"],
                analysis_type=AnalysisType.CORRELATION,
            ),
            DimensionDefinition(
                code="policy_effect",
                name="政策效果评估",
                data_fields=["tax_incentive", "subsidy_amount", "satisfaction_rate"],
                analysis_type=AnalysisType.DESCRIPTIVE,
            ),
        ]

        for dim in default_dimensions:
            self.register_dimension(dim)

    def register_dimension(self, dimension: DimensionDefinition) -> bool:
        """注册分析维度"""
        self._dimensions[dimension.code] = dimension
        logger.debug(f"注册分析维度: {dimension.code} - {dimension.name}")
        return True

    def unregister_dimension(self, code: str) -> bool:
        """注销分析维度"""
        if code in self._dimensions:
            del self._dimensions[code]
            return True
        return False

    def get_dimension(self, code: str) -> DimensionDefinition | None:
        """获取维度定义"""
        return self._dimensions.get(code)

    def list_dimensions(self) -> list[DimensionDefinition]:
        """列出所有维度"""
        return list(self._dimensions.values())

    def analyze(
        self, dimension_code: str, data: pd.DataFrame | dict[str, Any], use_cache: bool = False
    ) -> AnalysisResult | None:
        """
        执行维度分析

        Args:
            dimension_code: 维度代码
            data: 数据
            use_cache: 是否使用缓存

        Returns:
            AnalysisResult
        """
        # 检查缓存
        cache_key = f"{dimension_code}:{id(data)}"
        if use_cache and cache_key in self._results_cache:
            return self._results_cache[cache_key]

        # 获取维度定义
        dimension = self._dimensions.get(dimension_code)
        if not dimension:
            logger.error(f"未知维度: {dimension_code}")
            return None

        # 创建分析器
        analyzer = DimensionAnalyzerFactory.create(dimension)

        # 执行分析
        try:
            result = analyzer.analyze(data)

            # 缓存结果
            if use_cache:
                self._results_cache[cache_key] = result

            return result
        except Exception as e:
            logger.error(f"分析失败: {dimension_code} - {e}")
            return None

    def analyze_batch(
        self, dimension_codes: list[str], data: pd.DataFrame | dict[str, Any], use_cache: bool = False
    ) -> dict[str, AnalysisResult | None]:
        """批量分析"""
        results = {}
        for code in dimension_codes:
            results[code] = self.analyze(code, data, use_cache)
        return results

    def analyze_all(self, data: pd.DataFrame | dict[str, Any]) -> dict[str, AnalysisResult]:
        """分析所有维度"""
        results = {}
        for dimension in self._dimensions.values():
            result = self.analyze(dimension.code, data)
            if result:
                results[dimension.code] = result
        return results

    def clear_cache(self):
        """清除缓存"""
        self._results_cache.clear()

    def export_dimensions(self) -> list[dict[str, Any]]:
        """导出维度配置"""
        return [
            {
                "code": dim.code,
                "name": dim.name,
                "data_fields": dim.data_fields,
                "analysis_type": dim.analysis_type.value,
                "aggregator": dim.aggregator,
                "filters": dim.filters,
                "group_by": dim.group_by,
            }
            for dim in self._dimensions.values()
        ]


# 全局实例
analysis_engine = FlexibleAnalysisEngine()


# 便捷函数
def register_analysis_dimension(
    code: str, name: str, data_fields: list[str], analysis_type: str = "descriptive", **kwargs
) -> bool:
    """便捷的维度注册函数"""
    dim = DimensionDefinition(
        code=code, name=name, data_fields=data_fields, analysis_type=AnalysisType(analysis_type), **kwargs
    )
    return analysis_engine.register_dimension(dim)


def analyze_dimension(code: str, data: dict[str, Any]) -> AnalysisResult | None:
    """执行维度分析"""
    return analysis_engine.analyze(code, data)


def analyze_all_dimensions(data: dict[str, Any]) -> dict[str, AnalysisResult]:
    """分析所有维度"""
    return analysis_engine.analyze_all(data)
