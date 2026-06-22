"""
分析模块测试
"""


class TestIndicatorRegistry:
    """指标注册系统测试"""

    def test_indicator_registry_init(self):
        """测试 IndicatorRegistry 初始化"""
        from backend.analysis.indicator_registry import IndicatorRegistry

        registry = IndicatorRegistry()
        assert registry is not None
        assert hasattr(registry, "register")
        assert hasattr(registry, "get")
        assert hasattr(registry, "get_all")

    def test_indicator_registry_register_indicator(self):
        """测试注册指标"""
        from backend.analysis.indicator_registry import IndicatorCategory, IndicatorDefinition, IndicatorRegistry

        registry = IndicatorRegistry()
        indicator = IndicatorDefinition(
            code="test_gdp", name="测试GDP", category=IndicatorCategory.MACRO, unit="亿元", description="测试指标描述"
        )
        registry.register(indicator)

        registered = registry.get("test_gdp")
        assert registered is not None
        assert registered.code == "test_gdp"

    def test_indicator_registry_list_indicators(self):
        """测试列出指标"""
        from backend.analysis.indicator_registry import IndicatorRegistry

        registry = IndicatorRegistry()
        indicators = registry.get_all()
        assert isinstance(indicators, list)
        assert len(indicators) > 0  # 应该有默认注册的指标


class TestCustomIndicators:
    """自定义指标计算引擎测试"""

    def test_custom_indicators_module_exists(self):
        """测试自定义指标模块存在"""
        from backend.analysis import custom_indicators

        assert custom_indicators is not None

    def test_builtin_formula_deficit_rate(self):
        """测试内置公式能自动提取依赖并计算。"""
        from backend.analysis.custom_indicators import calculate_indicator

        result = calculate_indicator("deficit_rate", {"revenue": 1000, "expenditure": 1200, "gdp": 30000})
        assert result.status.value == "success"
        assert abs(result.value - 0.6667) < 1e-4

    def test_list_dependency_hhi(self):
        """测试列表依赖的 Σ 求和（HHI 指数）。"""
        from backend.analysis.custom_indicators import calculate_indicator

        result = calculate_indicator("concentration_hhi", {"share": [0.2, 0.3, 0.5]})
        assert result.status.value == "success"
        assert abs(result.value - 0.38) < 1e-6

    def test_formula_insufficient_data(self):
        """测试缺少依赖时返回 INSUFFICIENT_DATA。"""
        from backend.analysis.custom_indicators import calculate_indicator

        result = calculate_indicator("deficit_rate", {"revenue": 1000})
        assert result.status.value == "insufficient_data"


class TestDimensionAnalysis:
    """维度分析框架测试"""

    def test_dimension_analysis_module_exists(self):
        """测试维度分析模块存在"""
        from backend.analysis import dimension_analysis

        assert dimension_analysis is not None

    def test_distribution_analyzer(self):
        """测试分布分析器。"""
        import pandas as pd

        from backend.analysis.dimension_analysis import (
            AnalysisType,
            DimensionAnalyzerFactory,
            DimensionDefinition,
        )

        dim = DimensionDefinition(
            code="test_distribution",
            name="测试分布",
            data_fields=["gdp"],
            analysis_type=AnalysisType.DISTRIBUTION,
        )
        analyzer = DimensionAnalyzerFactory.create(dim)
        df = pd.DataFrame({"gdp": [100, 200, 300, 400, 500]})
        result = analyzer.analyze(df)

        assert result is not None
        assert "gdp" in result.summary
        assert "skewness" in result.summary["gdp"]
        assert len(result.insights) > 0

    def test_breakdown_analyzer_time(self):
        """测试分解分析器（时间维度）。"""
        import pandas as pd

        from backend.analysis.dimension_analysis import (
            AnalysisType,
            DimensionAnalyzerFactory,
            DimensionDefinition,
        )

        dim = DimensionDefinition(
            code="test_breakdown",
            name="测试分解",
            data_fields=["gdp"],
            analysis_type=AnalysisType.BREAKDOWN,
            metadata={"time_col": "year"},
        )
        analyzer = DimensionAnalyzerFactory.create(dim)
        df = pd.DataFrame({"year": [2020, 2021, 2022, 2023], "gdp": [100, 110, 125, 140]})
        result = analyzer.analyze(df)

        assert result is not None
        assert "gdp" in result.summary
        assert result.summary["gdp"]["total_change"] == 40.0

    def test_forecast_analyzer(self):
        """测试预测分析器。"""
        import pandas as pd

        from backend.analysis.dimension_analysis import (
            AnalysisType,
            DimensionAnalyzerFactory,
            DimensionDefinition,
        )

        dim = DimensionDefinition(
            code="test_forecast",
            name="测试预测",
            data_fields=["gdp"],
            analysis_type=AnalysisType.FORECAST,
            metadata={"time_col": "year", "forecast_years": 3},
        )
        analyzer = DimensionAnalyzerFactory.create(dim)
        df = pd.DataFrame({"year": list(range(2016, 2025)), "gdp": [100 + i * 10 for i in range(9)]})
        result = analyzer.analyze(df)

        assert result is not None
        assert "gdp" in result.summary
        assert len(result.summary["gdp"]["forecast_values"]) == 3

    def test_benchmark_analyzer_with_target(self):
        """测试标杆分析器（目标值模式）。"""
        import pandas as pd

        from backend.analysis.dimension_analysis import (
            AnalysisType,
            DimensionAnalyzerFactory,
            DimensionDefinition,
        )

        dim = DimensionDefinition(
            code="test_benchmark",
            name="测试标杆",
            data_fields=["gdp"],
            analysis_type=AnalysisType.BENCHMARK,
            metadata={"benchmarks": {"gdp": 500}},
        )
        analyzer = DimensionAnalyzerFactory.create(dim)
        df = pd.DataFrame({"year": [2022, 2023, 2024], "gdp": [300, 400, 450]})
        result = analyzer.analyze(df)

        assert result is not None
        assert "gdp" in result.summary
        assert result.summary["gdp"]["achievement_pct"] == 90.0

    def test_custom_analyzer(self):
        """测试自定义分析器。"""
        import pandas as pd

        from backend.analysis.dimension_analysis import (
            AnalysisType,
            DimensionAnalyzerFactory,
            DimensionDefinition,
        )

        dim = DimensionDefinition(
            code="test_custom",
            name="测试自定义",
            data_fields=["gdp"],
            analysis_type=AnalysisType.CUSTOM,
            metadata={"aggregator": "sum"},
        )
        analyzer = DimensionAnalyzerFactory.create(dim)
        df = pd.DataFrame({"gdp": [100, 200, 300]})
        result = analyzer.analyze(df)

        assert result is not None
        assert result.summary["gdp"]["value"] == 600.0


class TestEnterpriseAnalyzer:
    """企业分析器测试"""

    def test_enterprise_analyzer_init(self):
        """测试 EnterpriseAnalyzer 初始化"""
        from backend.analysis.enterprise_analyzer_v3 import EnterpriseAnalyzer

        analyzer = EnterpriseAnalyzer()
        assert analyzer is not None

    def test_enterprise_analyzer_with_sample_data(self):
        from backend.analysis.enterprise_analyzer_v3 import EnterpriseAnalyzer

        analyzer = EnterpriseAnalyzer()
        sample_data = {
            "region": "深圳市",
            "industry": "半导体产业",
            "year": 2025,
            "land_price": 1000,
            "salary_level": 15000,
            "energy_cost": 1.2,
            "financing_cost": 5.0,
            "local_support_rate": 75,
            "avg_delivery_time": 4,
            "location_quotient": 2.0,
            "tax_reduction": 500,
            "tax_coverage": 80,
            "rd_subsidy": 200,
            "avg_approval_time": 7,
        }
        report = analyzer.generate_comprehensive_report(sample_data)

        assert report is not None
        assert isinstance(report, dict)
        assert "region" in report
        assert "industry" in report
        assert "business_costs" in report
        assert "supply_chain" in report
        assert "policy_benefits" in report


class TestGovernmentAnalyzer:
    """政府分析器测试"""

    def test_government_analyzer_init(self):
        """测试 GovernmentAnalyzer 初始化"""
        from backend.analysis.government_analyzer import GovernmentAnalyzer

        analyzer = GovernmentAnalyzer()
        assert analyzer is not None

    def test_government_analyzer_with_sample_data(self):
        from backend.analysis.government_analyzer import GovernmentAnalyzer

        analyzer = GovernmentAnalyzer()
        sample_data = {
            "region": "深圳市",
            "industry": "半导体产业",
            "year": 2025,
            "gdp": 30000,
            "revenue": 4500,
            "expenditure": 5400,
            "fund_utilization": 0.82,
            "employment_driven": 15000,
            "tax_contribution": 12.0,
            "influence_coefficient": 1.05,
            "sensitivity_coefficient": 0.95,
            "upstream_coverage": 55.0,
            "midstream_coverage": 65.0,
            "downstream_coverage": 60.0,
            "digitalization_level": 55.0,
        }
        report = analyzer.generate_comprehensive_report(sample_data)

        assert report is not None
        assert isinstance(report, dict)
        assert "region" in report
        assert "industry" in report
        assert "fiscal_leverage" in report
        assert "industry_driving" in report
        assert "industry_chain" in report


class TestEconomicModels:
    """经济模型测试"""

    def test_economic_models_module_exists(self):
        """测试经济模型模块存在"""
        from backend.analysis import economic_models

        assert economic_models is not None
