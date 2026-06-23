"""
backend.analysis 扩展测试：覆盖当前覆盖率较低的模块与分支。
"""

from unittest.mock import MagicMock

import pandas as pd
import pytest


class TestIndicatorRegistryExtended:
    """指标注册表扩展测试"""

    def test_registry_is_singleton(self):
        from backend.analysis.indicator_registry import IndicatorRegistry

        r1 = IndicatorRegistry()
        r2 = IndicatorRegistry()
        assert r1 is r2

    def test_get_by_category(self):
        from backend.analysis.indicator_registry import IndicatorCategory, indicator_registry

        macros = indicator_registry.get_by_category(IndicatorCategory.MACRO)
        codes = [m.code for m in macros]
        assert "gdp" in codes

    def test_get_by_tags(self):
        # 默认指标无标签，注册一个带标签的
        from backend.analysis.indicator_registry import IndicatorCategory, IndicatorDefinition, indicator_registry

        ind = IndicatorDefinition(
            code="tagged_test", name="测试", category=IndicatorCategory.CUSTOM, unit="", description="x", tags=["demo"]
        )
        indicator_registry.register(ind)
        assert any(i.code == "tagged_test" for i in indicator_registry.get_by_tags(["demo"]))

    def test_search(self):
        from backend.analysis.indicator_registry import indicator_registry

        results = indicator_registry.search("GDP")
        assert any("gdp" in r.code for r in results)

    def test_unregister_existing_and_missing(self):
        from backend.analysis.indicator_registry import IndicatorCategory, IndicatorDefinition, indicator_registry

        ind = IndicatorDefinition(
            code="to_remove", name="待删除", category=IndicatorCategory.CUSTOM, unit="", description="x"
        )
        indicator_registry.register(ind)
        assert indicator_registry.unregister("to_remove") is True
        assert indicator_registry.unregister("to_remove") is False

    def test_categories_and_codes(self):
        from backend.analysis.indicator_registry import indicator_registry

        assert len(indicator_registry.get_categories()) > 0
        assert "gdp" in indicator_registry.get_all_codes()

    def test_export_to_dict(self):
        from backend.analysis.indicator_registry import indicator_registry

        data = indicator_registry.export_to_dict()
        assert data["total_count"] > 0
        assert "indicators" in data
        assert "categories" in data

    def test_save_and_load_from_file(self, tmp_path):
        from backend.analysis.indicator_registry import IndicatorCategory, IndicatorDefinition, IndicatorRegistry

        # 临时替换单例，避免污染全局注册表
        original_instance = IndicatorRegistry._instance
        IndicatorRegistry._instance = None
        try:
            registry = IndicatorRegistry()
            registry.register(
                IndicatorDefinition(
                    code="file_test", name="文件测试", category=IndicatorCategory.CUSTOM, unit="%", description="x"
                )
            )

            filepath = tmp_path / "indicators.json"
            registry.save_to_file(str(filepath))
            assert filepath.exists()

            IndicatorRegistry._instance = None
            new_registry = IndicatorRegistry()
            new_registry.load_from_file(str(filepath))
            assert new_registry.get("file_test") is not None
        finally:
            IndicatorRegistry._instance = original_instance

    def test_register_indicator_convenience(self):
        from backend.analysis.indicator_registry import get_indicator, register_indicator

        register_indicator(code="conv_test", name="便捷测试", category="custom", unit="%", description="test")
        assert get_indicator("conv_test") is not None

    def test_list_and_search_helpers(self):
        from backend.analysis.indicator_registry import list_indicators_by_category, search_indicators

        assert any(i.code == "gdp" for i in list_indicators_by_category("macro"))
        assert any("gdp" in i.code for i in search_indicators("gdp"))


class TestCustomIndicatorsExtended:
    """自定义指标引擎扩展测试"""

    def test_built_in_formulas(self):
        from backend.analysis.custom_indicators import calculate_indicator

        cases = [
            ("growth_rate", {"current": 110, "previous": 100}, 10.0),
            ("cagr", {"end": 161.05, "start": 100, "years": 5}, 10.0),
            ("deficit", {"revenue": 1000, "expenditure": 1200}, 200.0),
            ("fiscal_self_sufficiency", {"revenue": 800, "expenditure": 1000}, 80.0),
            ("tax_burden", {"tax_revenue": 3000, "gdp": 30000}, 10.0),
            ("industry_ratio", {"industry_output": 8000, "total_output": 40000}, 20.0),
            ("location_quotient", {"local_share": 0.08, "total_share": 0.05}, 1.6),
            ("leverage_multiplier", {"social_capital": 5000, "government_investment": 1000}, 5.0),
            ("roi", {"output_value": 2000, "investment": 1000}, 2.0),
            ("labor_productivity", {"output": 10000, "labor": 500}, 20.0),
            ("capital_productivity", {"output": 10000, "capital": 2000}, 5.0),
            ("cost_per_unit", {"total_cost": 5000, "output": 1000}, 5.0),
            ("cost_ratio", {"cost": 400, "revenue": 2000}, 20.0),
            ("export_dependency", {"export": 5000, "gdp": 50000}, 10.0),
            ("import_dependency", {"import": 1000, "consumption": 5000}, 20.0),
            ("self_sufficiency", {"domestic_output": 8000, "total_consumption": 10000}, 80.0),
            ("pass_rate", {"qualified": 95, "total": 100}, 95.0),
            (
                "satisfaction",
                {"very_satisfied": 20, "satisfied": 50, "neutral": 20, "dissatisfied": 10, "total": 100},
                70.0,
            ),
        ]
        for code, data, expected in cases:
            result = calculate_indicator(code, data)
            assert result.status.value == "success", f"{code} failed: {result.message}"
            assert abs(result.value - expected) < 1e-4, f"{code} expected {expected}, got {result.value}"

    def test_comprehensive_productivity(self):
        from backend.analysis.custom_indicators import calculate_indicator

        result = calculate_indicator(
            "comprehensive_productivity",
            {"alpha": 0.3, "capital": 100, "labor": 200, "output": 1000},
        )
        assert result.status.value == "success"

    def test_unknown_indicator(self):
        from backend.analysis.custom_indicators import CalculationStatus, calculate_indicator

        result = calculate_indicator("not_exists", {"a": 1})
        assert result.status == CalculationStatus.FAILED
        assert "未知指标" in result.message

    def test_division_by_zero(self):
        from backend.analysis.custom_indicators import CalculationStatus, calculate_indicator

        result = calculate_indicator("growth_rate", {"current": 110, "previous": 0})
        assert result.status == CalculationStatus.FAILED

    def test_direct_data_access(self):
        from backend.analysis.custom_indicators import CalculationStatus, calculate_indicator

        result = calculate_indicator("custom_direct", {"custom_direct": 42})
        assert result.status == CalculationStatus.SUCCESS
        assert result.value == 42

    def test_nested_dict_provider(self):
        from backend.analysis.custom_indicators import DictDataProvider

        provider = DictDataProvider({"gdp": {"value": 100}})
        assert provider.get("gdp.value") == 100
        assert provider.get("gdp.missing") is None
        assert provider.get("missing") is None

    def test_dataframe_provider(self):
        from backend.analysis.custom_indicators import DataFrameDataProvider

        df = pd.DataFrame({"year": [2020, 2021, 2022], "gdp": [100, 110, 120]})
        provider = DataFrameDataProvider(df, id_col="year")
        assert provider.get("gdp") == 120
        assert provider.get_range(["gdp"]) == {"gdp": 120}

    def test_register_formula_and_function(self):
        from backend.analysis.custom_indicators import (
            register_custom_formula,
            register_custom_function,
        )

        register_custom_formula("my_double", "{x} * 2", dependencies=["x"])
        register_custom_function(
            "my_sum",
            lambda provider: provider.get("a", 0) + provider.get("b", 0),
            dependencies=["a", "b"],
        )

        from backend.analysis.custom_indicators import calculate_indicator

        assert calculate_indicator("my_double", {"x": 3}).value == 6
        assert calculate_indicator("my_sum", {"a": 1, "b": 2}).value == 3

    def test_calculate_batch_and_available(self):
        from backend.analysis.custom_indicators import DictDataProvider, custom_indicator_engine

        provider = DictDataProvider(
            {"revenue": 1000, "expenditure": 1200, "gdp": 30000, "current": 110, "previous": 100}
        )
        batch = custom_indicator_engine.calculate_batch(["deficit", "growth_rate"], provider)
        assert batch["deficit"].status.value == "success"
        assert batch["growth_rate"].status.value == "success"

        available = custom_indicator_engine.get_available_indicators()
        assert "deficit" in available

    def test_sum_with_scalar_and_list(self):
        from backend.analysis.custom_indicators import CustomIndicatorEngine, DictDataProvider

        engine = CustomIndicatorEngine()
        engine.register_formula("weighted_hhi", "Σ({share} ** 2) * {scale}", dependencies=["share", "scale"])
        provider = DictDataProvider({"share": [0.2, 0.3, 0.5], "scale": 2})
        result = engine.calculate("weighted_hhi", provider)
        assert result.status.value == "success"
        assert abs(result.value - 0.76) < 1e-6


class TestDimensionAnalysisExtended:
    """维度分析框架扩展测试"""

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame(
            {
                "year": [2020, 2021, 2022, 2023, 2024],
                "gdp": [100, 110, 125, 140, 160],
                "investment": [30, 32, 35, 38, 42],
                "employment": [500, 510, 525, 540, 560],
                "city": ["A", "A", "B", "B", "B"],
            }
        )

    def test_descriptive_analyzer_std_zero(self):
        from backend.analysis.dimension_analysis import AnalysisType, DimensionAnalyzerFactory, DimensionDefinition

        dim = DimensionDefinition(code="desc", name="描述", data_fields=["x"], analysis_type=AnalysisType.DESCRIPTIVE)
        analyzer = DimensionAnalyzerFactory.create(dim)
        result = analyzer.analyze(pd.DataFrame({"x": [5, 5, 5]}))
        assert result.summary["x"]["std"] == 0
        assert "保持稳定" in result.insights[0]

    def test_descriptive_analyzer_peak_outlier(self):
        from backend.analysis.dimension_analysis import AnalysisType, DimensionAnalyzerFactory, DimensionDefinition

        dim = DimensionDefinition(code="desc", name="描述", data_fields=["x"], analysis_type=AnalysisType.DESCRIPTIVE)
        analyzer = DimensionAnalyzerFactory.create(dim)
        result = analyzer.analyze(pd.DataFrame({"x": [10, 11, 50]}))
        assert any("峰值" in insight for insight in result.insights)

    def test_comparative_analyzer(self, sample_df):
        from backend.analysis.dimension_analysis import AnalysisType, DimensionAnalyzerFactory, DimensionDefinition

        dim = DimensionDefinition(
            code="comp",
            name="对比",
            data_fields=["gdp"],
            analysis_type=AnalysisType.COMPARATIVE,
            group_by=["city"],
        )
        result = DimensionAnalyzerFactory.create(dim).analyze(sample_df)
        assert "gdp" in result.summary
        assert len(result.insights) > 0

    def test_trend_analyzer(self, sample_df):
        from backend.analysis.dimension_analysis import AnalysisType, DimensionAnalyzerFactory, DimensionDefinition

        dim = DimensionDefinition(
            code="trend",
            name="趋势",
            data_fields=["gdp"],
            analysis_type=AnalysisType.TREND,
            metadata={"time_col": "year"},
        )
        result = DimensionAnalyzerFactory.create(dim).analyze(sample_df)
        assert result.summary["gdp"]["trend_direction"] == "up"

    def test_correlation_analyzer_strong(self, sample_df):
        from backend.analysis.dimension_analysis import AnalysisType, DimensionAnalyzerFactory, DimensionDefinition

        dim = DimensionDefinition(
            code="corr",
            name="相关",
            data_fields=["gdp", "investment", "employment"],
            analysis_type=AnalysisType.CORRELATION,
        )
        result = DimensionAnalyzerFactory.create(dim).analyze(sample_df)
        assert result.summary["total_pairs"] == 3
        assert len(result.summary["strong_correlations"]) > 0

    def test_distribution_analyzer_missing_and_empty(self):
        from backend.analysis.dimension_analysis import AnalysisType, DimensionAnalyzerFactory, DimensionDefinition

        dim = DimensionDefinition(
            code="dist", name="分布", data_fields=["gdp", "missing"], analysis_type=AnalysisType.DISTRIBUTION
        )
        result = DimensionAnalyzerFactory.create(dim).analyze(pd.DataFrame({"gdp": [1, 2, 3, 4, 100]}))
        assert "gdp" in result.summary
        assert "missing" not in result.summary
        assert any("右偏" in i for i in result.insights)

    def test_breakdown_analyzer_group_by(self):
        from backend.analysis.dimension_analysis import AnalysisType, DimensionAnalyzerFactory, DimensionDefinition

        dim = DimensionDefinition(
            code="break",
            name="分解",
            data_fields=["gdp"],
            analysis_type=AnalysisType.BREAKDOWN,
            group_by=["city"],
        )
        df = pd.DataFrame({"city": ["A", "A", "B"], "gdp": [100, 200, 300]})
        result = DimensionAnalyzerFactory.create(dim).analyze(df)
        assert "components" in result.summary["gdp"]
        assert any("占比最高" in i for i in result.insights)

    def test_breakdown_total_zero(self):
        from backend.analysis.dimension_analysis import AnalysisType, DimensionAnalyzerFactory, DimensionDefinition

        dim = DimensionDefinition(
            code="break", name="分解", data_fields=["gdp"], analysis_type=AnalysisType.BREAKDOWN, group_by=["city"]
        )
        df = pd.DataFrame({"city": ["A", "B"], "gdp": [0, 0]})
        result = DimensionAnalyzerFactory.create(dim).analyze(df)
        assert "gdp" not in result.summary

    def test_breakdown_time_growth_negative(self):
        from backend.analysis.dimension_analysis import AnalysisType, DimensionAnalyzerFactory, DimensionDefinition

        dim = DimensionDefinition(
            code="break",
            name="分解",
            data_fields=["gdp"],
            analysis_type=AnalysisType.BREAKDOWN,
            metadata={"time_col": "year"},
        )
        df = pd.DataFrame({"year": [2021, 2022, 2023], "gdp": [100, 80, 60]})
        result = DimensionAnalyzerFactory.create(dim).analyze(df)
        assert result.summary["gdp"]["total_change"] == -40
        assert any("下降" in i for i in result.insights)

    def test_forecast_analyzer_insufficient_data(self):
        from backend.analysis.dimension_analysis import AnalysisType, DimensionAnalyzerFactory, DimensionDefinition

        dim = DimensionDefinition(
            code="fc",
            name="预测",
            data_fields=["gdp"],
            analysis_type=AnalysisType.FORECAST,
            metadata={"time_col": "year"},
        )
        df = pd.DataFrame({"year": [2021, 2022], "gdp": [100, 110]})
        result = DimensionAnalyzerFactory.create(dim).analyze(df)
        assert "error" in result.summary["gdp"]

    def test_benchmark_analyzer_group_mode(self):
        from backend.analysis.dimension_analysis import AnalysisType, DimensionAnalyzerFactory, DimensionDefinition

        dim = DimensionDefinition(
            code="bench",
            name="标杆",
            data_fields=["gdp"],
            analysis_type=AnalysisType.BENCHMARK,
            group_by=["city"],
        )
        df = pd.DataFrame({"city": ["A", "A", "B", "B"], "gdp": [100, 110, 200, 210]})
        result = DimensionAnalyzerFactory.create(dim).analyze(df)
        assert "best_group" in result.summary["gdp"]
        assert result.summary["gdp"]["best_group"] == "B"

    def test_custom_analyzer_aggregators(self):
        from backend.analysis.dimension_analysis import AnalysisType, DimensionAnalyzerFactory, DimensionDefinition

        df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})
        for agg, expected in [("sum", 15), ("avg", 3), ("max", 5), ("min", 1), ("count", 5), ("desc", None)]:
            dim = DimensionDefinition(
                code=f"custom_{agg}",
                name="自定义",
                data_fields=["x"],
                analysis_type=AnalysisType.CUSTOM,
                metadata={"aggregator": agg},
            )
            result = DimensionAnalyzerFactory.create(dim).analyze(df)
            if agg == "desc":
                assert "mean" in result.summary["x"]["value"]
            else:
                assert result.summary["x"]["value"] == expected

    def test_analyze_engine_methods(self):
        from backend.analysis.dimension_analysis import (
            AnalysisType,
            DimensionDefinition,
            FlexibleAnalysisEngine,
        )

        engine = FlexibleAnalysisEngine()
        dim = DimensionDefinition(
            code="engine_test", name="引擎测试", data_fields=["x"], analysis_type=AnalysisType.DESCRIPTIVE
        )
        assert engine.register_dimension(dim) is True
        assert engine.get_dimension("engine_test") is not None
        assert any(d.code == "engine_test" for d in engine.list_dimensions())

        result = engine.analyze("engine_test", pd.DataFrame({"x": [1, 2, 3]}))
        assert result is not None

        cached = engine.analyze("engine_test", pd.DataFrame({"x": [1, 2, 3]}), use_cache=True)
        assert cached is not None

        batch = engine.analyze_batch(["engine_test"], pd.DataFrame({"x": [1, 2, 3]}))
        assert "engine_test" in batch

        all_results = engine.analyze_all(pd.DataFrame({"x": [1, 2, 3]}))
        assert "engine_test" in all_results

        assert engine.unregister_dimension("engine_test") is True
        assert engine.unregister_dimension("engine_test") is False
        assert engine.analyze("engine_test", pd.DataFrame({"x": [1, 2, 3]})) is None

        engine.clear_cache()
        assert len(engine.export_dimensions()) >= 0

    def test_register_and_analyze_dimension_helpers(self):
        from backend.analysis.dimension_analysis import (
            analyze_all_dimensions,
            analyze_dimension,
            register_analysis_dimension,
        )

        register_analysis_dimension("helper_test", "助手测试", ["x"], analysis_type="descriptive")
        result = analyze_dimension("helper_test", pd.DataFrame({"x": [1, 2, 3]}))
        assert result is not None
        results = analyze_all_dimensions(pd.DataFrame({"x": [1, 2, 3]}))
        assert "helper_test" in results

    def test_dimension_with_filters(self):
        from backend.analysis.dimension_analysis import AnalysisType, DimensionAnalyzerFactory, DimensionDefinition

        dim = DimensionDefinition(
            code="filtered",
            name="过滤",
            data_fields=["x"],
            analysis_type=AnalysisType.DESCRIPTIVE,
            filters={"city": "A"},
        )
        df = pd.DataFrame({"city": ["A", "A", "B"], "x": [1, 2, 100]})
        result = DimensionAnalyzerFactory.create(dim).analyze(df)
        assert result.summary["x"]["mean"] == 1.5


class TestEconomicModelsExtended:
    """经济模型扩展测试"""

    def test_inference_calculate_multiple_indicators(self):
        from backend.analysis.economic_models import inference_engine

        inputs = {
            "expenditure": 5400,
            "revenue": 4500,
            "gdp": 30000,
            "tax_revenue": 3000,
            "primary_industry": 1000,
            "secondary_industry": 12000,
            "tertiary_industry": 17000,
            "urban_income": 60000,
            "rural_income": 25000,
            "consumption": 15000,
            "disposable_income": 20000,
            "export": 5000,
            "import": 3000,
            "rd_expenditure": 900,
        }
        result = inference_engine.calculate("fiscal_deficit", inputs)
        assert result.value == 900.0
        result2 = inference_engine.calculate("deficit_rate", inputs)
        assert abs(result2.value - 3.0) < 1e-4

    def test_inference_unknown_target(self):
        from backend.analysis.economic_models import inference_engine

        with pytest.raises(ValueError, match="未知指标"):
            inference_engine.calculate("unknown", {"a": 1})

    def test_inference_missing_fields(self):
        from backend.analysis.economic_models import inference_engine

        with pytest.raises(ValueError, match="缺少必需字段"):
            inference_engine.calculate("deficit_rate", {"revenue": 1000})

    def test_monte_carlo_method(self):
        from backend.analysis.economic_models import inference_engine

        inputs = {"expenditure": 5400, "revenue": 4500, "gdp": 30000}
        result = inference_engine.calculate("deficit_rate", inputs, method="monte_carlo")
        assert result.method == "monte_carlo"
        assert result.confidence_interval[0] <= result.value <= result.confidence_interval[1]

    def test_infer_all(self):
        from backend.analysis.economic_models import inference_engine

        inputs = {
            "expenditure": 5400,
            "revenue": 4500,
            "gdp": 30000,
            "tax_revenue": 3000,
            "primary_industry": 1000,
            "secondary_industry": 12000,
            "tertiary_industry": 17000,
            "urban_income": 60000,
            "rural_income": 25000,
            "consumption": 15000,
            "disposable_income": 20000,
            "export": 5000,
            "import": 3000,
            "rd_expenditure": 900,
        }
        report = inference_engine.infer_all(inputs)
        assert report["output_count"] > 0
        assert "timestamp" in report

    def test_phillips_curve(self):
        from backend.analysis.economic_models import EconomicModels

        result = EconomicModels.phillips_curve(6.0)
        assert result["output"]["inflation"] == pytest.approx(1.5, rel=1e-3)

    def test_okun_law(self):
        from backend.analysis.economic_models import EconomicModels

        result = EconomicModels.okun_law(4.0)
        assert result["output"]["output_gap"] == -2.0

    def test_cobb_douglas(self):
        from backend.analysis.economic_models import EconomicModels

        result = EconomicModels.cobb_douglas(1000, 5000)
        assert result["output"]["output"] > 0
        assert result["output"]["returns_to_scale"] == "constant"

    def test_solow_growth_invalid_denom(self):
        from backend.analysis.economic_models import EconomicModels

        result = EconomicModels.solow_growth(0.2, -0.05, 0.05)
        assert "error" in result

    def test_solow_growth_valid(self):
        from backend.analysis.economic_models import EconomicModels

        result = EconomicModels.solow_growth(0.3, 0.01, 0.05)
        assert "steady_state_capital_per_worker" in result["output"]


class TestEnterpriseAnalyzerExtended:
    """企业分析器扩展测试"""

    @pytest.fixture
    def sample_enterprise_data(self):
        return {
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
            "supplier_count": 100,
        }

    def test_analyze_business_costs_partial(self):
        from backend.analysis.enterprise_analyzer_v3 import EnterpriseAnalyzer

        analyzer = EnterpriseAnalyzer()
        result = analyzer.analyze_business_costs({"land_price": 1000})
        assert result["total_cost_score"] > 0
        assert "land_cost" in result["components"]

    def test_analyze_supply_chain_partial(self):
        from backend.analysis.enterprise_analyzer_v3 import EnterpriseAnalyzer

        analyzer = EnterpriseAnalyzer()
        result = analyzer.analyze_supply_chain({"local_support_rate": 75})
        assert result["supply_chain_score"] > 0

    def test_analyze_policy_benefits_partial(self):
        from backend.analysis.enterprise_analyzer_v3 import EnterpriseAnalyzer

        analyzer = EnterpriseAnalyzer()
        result = analyzer.analyze_policy_benefits({"tax_reduction": 500})
        assert result["policy_benefit_score"] > 0

    def test_compare_multiple_cities_mocked(self, sample_enterprise_data, monkeypatch):
        from backend.analysis.enterprise_analyzer_v3 import EnterpriseAnalyzer

        def mock_get_city_data(city):
            return {**sample_enterprise_data, "name": city, "region": city}

        monkeypatch.setattr("backend.analysis.enterprise_analyzer_v3.get_city_data", mock_get_city_data)
        monkeypatch.setattr("backend.analysis.enterprise_analyzer_v3.get_data_source_info", lambda: {})

        analyzer = EnterpriseAnalyzer()
        df = analyzer.compare_multiple_cities(["深圳", "上海"])
        assert not df.empty
        assert "综合得分" in df.columns

    def test_analyze_city_and_compare_cities_mocked(self, sample_enterprise_data, monkeypatch):
        from backend.analysis.enterprise_analyzer_v3 import EnterpriseAnalyzer

        def mock_get_city_data(city):
            return {**sample_enterprise_data, "name": city, "region": city}

        monkeypatch.setattr("backend.analysis.enterprise_analyzer_v3.get_city_data", mock_get_city_data)
        monkeypatch.setattr("backend.analysis.enterprise_analyzer_v3.get_all_cities", lambda: ["深圳", "上海"])
        monkeypatch.setattr("backend.analysis.enterprise_analyzer_v3.get_data_source_info", lambda: {})

        analyzer = EnterpriseAnalyzer()
        report = analyzer.analyze_city("深圳")
        assert "business_costs" in report

        comparison = analyzer.compare_cities(["深圳", "上海"])
        assert len(comparison) == 2

    def test_run_full_analysis_and_predict(self, sample_enterprise_data, monkeypatch):
        from backend.analysis.enterprise_analyzer_v3 import EnterpriseAnalyzer

        def mock_get_city_data(city):
            return {**sample_enterprise_data, "name": city}

        monkeypatch.setattr("backend.analysis.enterprise_analyzer_v3.get_city_data", mock_get_city_data)
        monkeypatch.setattr("backend.analysis.enterprise_analyzer_v3.get_data_source_info", lambda: {})

        analyzer = EnterpriseAnalyzer()
        assert "overall_score" in analyzer.run_full_analysis("深圳")
        assert "overall_score" in analyzer.run_full_analysis(sample_enterprise_data)
        assert "overall_score" in analyzer.predict("深圳")

    def test_fab_location_recommendation_empty(self):
        from backend.analysis.enterprise_analyzer_v3 import _generate_fab_location_recommendation

        result = _generate_fab_location_recommendation({}, pd.DataFrame())
        assert result["recommended_city"] is None

    def test_semiconductor_fab_location_analysis_mocked(self, sample_enterprise_data, monkeypatch):
        from backend.analysis.enterprise_analyzer_v3 import run_semiconductor_fab_location_analysis

        def mock_get_city_data(city):
            return {**sample_enterprise_data, "name": city, "region": city}

        monkeypatch.setattr("backend.analysis.enterprise_analyzer_v3.get_city_data", mock_get_city_data)
        monkeypatch.setattr("backend.analysis.enterprise_analyzer_v3.get_data_source_info", lambda: {})
        monkeypatch.setattr(
            "backend.analysis.enterprise_analyzer_v3.generate_data_quality_report",
            lambda: {"total_cities": 2},
        )

        result = run_semiconductor_fab_location_analysis()
        assert result["case_title"] == "半导体制造企业选址分析"
        assert "comparison_table" in result


class TestGovernmentAnalyzerExtended:
    """政府分析器扩展测试"""

    @pytest.fixture
    def sample_gov_data(self):
        return {
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
            "bottlenecks": ["材料"],
        }

    def test_analyze_fiscal_leverage_partial(self):
        from backend.analysis.government_analyzer import GovernmentAnalyzer

        analyzer = GovernmentAnalyzer()
        result = analyzer.analyze_fiscal_leverage({"revenue": 4500, "expenditure": 5400})
        assert result["fiscal_self_sufficiency"] == pytest.approx(83.33, rel=1e-2)

    def test_analyze_industry_driving_partial(self):
        from backend.analysis.government_analyzer import GovernmentAnalyzer

        analyzer = GovernmentAnalyzer()
        result = analyzer.analyze_industry_driving({"employment_driven": 15000})
        assert result["driving_score"] > 0

    def test_analyze_industry_chain_partial(self):
        from backend.analysis.government_analyzer import GovernmentAnalyzer

        analyzer = GovernmentAnalyzer()
        result = analyzer.analyze_industry_chain({"upstream_coverage": 55, "midstream_coverage": 65})
        assert result["chain_completeness_score"] > 0

    def test_analyze_city_and_compare_mocked(self, sample_gov_data, monkeypatch):
        from backend.analysis.government_analyzer import GovernmentAnalyzer

        def mock_get_city_data(city):
            return {**sample_gov_data, "name": city}

        monkeypatch.setattr("backend.analysis.government_analyzer.get_city_data", mock_get_city_data)
        monkeypatch.setattr("backend.analysis.government_analyzer.get_all_cities", lambda: ["深圳", "上海"])
        monkeypatch.setattr("backend.analysis.government_analyzer.get_data_source_info", lambda: {})

        analyzer = GovernmentAnalyzer()
        report = analyzer.analyze_city("深圳")
        assert "fiscal_leverage" in report

        comparison = analyzer.compare_cities(["深圳", "上海"])
        assert len(comparison) == 2

    def test_enrich_from_indicators(self, monkeypatch):
        from backend.analysis.government_analyzer import GovernmentAnalyzer

        city_data = {"name": "深圳", "indicators": {"gdp": 30000}}
        monkeypatch.setattr("backend.analysis.government_analyzer.get_data_source_info", lambda: {})

        analyzer = GovernmentAnalyzer()
        enriched = analyzer._enrich_government_data(city_data)
        assert enriched["gdp"] == 30000
        assert "revenue" in enriched

    def test_run_full_analysis_and_predict(self, sample_gov_data, monkeypatch):
        from backend.analysis.government_analyzer import GovernmentAnalyzer

        def mock_get_city_data(city):
            return {**sample_gov_data, "name": city}

        monkeypatch.setattr("backend.analysis.government_analyzer.get_city_data", mock_get_city_data)
        monkeypatch.setattr("backend.analysis.government_analyzer.get_data_source_info", lambda: {})

        analyzer = GovernmentAnalyzer()
        assert "overall_score" in analyzer.run_full_analysis("深圳")
        assert "overall_score" in analyzer.run_full_analysis(sample_gov_data)
        assert "overall_score" in analyzer.predict(sample_gov_data)


class TestRealDataAnalysisExtended:
    """真实数据模块扩展测试（Mock 网络调用）"""

    @pytest.fixture
    def mock_akshare(self, monkeypatch):
        """Mock akshare 的宏观数据接口"""
        gdp_df = pd.DataFrame(
            {
                "季度": ["2020年4季度", "2021年4季度", "2022年4季度"],
                "国内生产总值-绝对值": [100000, 110000, 120000],
                "第一产业-绝对值": [7000, 7500, 8000],
                "第二产业-绝对值": [38000, 40000, 43000],
                "第三产业-绝对值": [55000, 62500, 69000],
            }
        )
        cpi_df = pd.DataFrame(
            {
                "日期": ["2020-12-31", "2021-12-31", "2022-12-31"],
                "今值": [2.5, 1.5, 2.0],
            }
        )
        pmi_df = pd.DataFrame(
            {
                "日期": ["2020-12-31", "2021-12-31", "2022-12-31"],
                "制造业-指数": [51.0, 50.2, 49.8],
            }
        )

        mock_ak = MagicMock()
        mock_ak.macro_china_gdp.return_value = gdp_df
        mock_ak.macro_china_cpi_yearly.return_value = cpi_df
        mock_ak.macro_china_pmi_yearly.return_value = pmi_df
        monkeypatch.setattr("backend.analysis.real_data_analysis.ak", mock_ak)
        return mock_ak

    def test_fetch_macro_data(self, mock_akshare):
        from backend.analysis.real_data_analysis import RealDataAnalyzer

        analyzer = RealDataAnalyzer()
        df = analyzer.fetch_macro_data()
        assert not df.empty
        assert "gdp" in df.columns
        assert "cpi_yoy" in df.columns

    def test_process_gdp_variants(self):
        from backend.analysis.real_data_analysis import RealDataAnalyzer

        analyzer = RealDataAnalyzer()
        # 测试 "1-4季度" 路径
        df = pd.DataFrame(
            {
                "季度": ["2022年1-4季度", "2023年1-4季度"],
                "国内生产总值-绝对值": [120000, 130000],
                "第一产业-绝对值": [8000, 8500],
                "第二产业-绝对值": [43000, 46000],
                "第三产业-绝对值": [69000, 75500],
            }
        )
        processed = analyzer._process_gdp(df)
        assert len(processed) == 2

    def test_process_cpi_empty(self):
        from backend.analysis.real_data_analysis import RealDataAnalyzer

        analyzer = RealDataAnalyzer()
        processed = analyzer._process_cpi(pd.DataFrame({"日期": [], "今值": []}))
        assert processed.empty

    def test_perform_eda(self):
        from backend.analysis.real_data_analysis import RealDataAnalyzer

        analyzer = RealDataAnalyzer()
        df = pd.DataFrame(
            {
                "year": [2020, 2021, 2022],
                "gdp": [100, 110, 120],
                "cpi_yoy": [2.0, 1.5, 2.1],
            }
        )
        eda = analyzer.perform_eda(df)
        assert "summary_stats" in eda
        assert "correlation_matrix" in eda
        assert "trend_analysis" in eda

    def test_generate_insights_gdp_up(self):
        from backend.analysis.real_data_analysis import RealDataAnalyzer

        analyzer = RealDataAnalyzer()
        eda = {
            "trend_analysis": {
                "gdp": {"trend_direction": "up", "cagr": 5.0},
                "cpi_yoy": {"latest_value": 0.5},
                "pmi_manufacturing": {"latest_value": 51.5},
            }
        }
        insights = analyzer.generate_insights(eda)
        assert any(i["indicator"] == "gdp" for i in insights)
        assert any(i["indicator"] == "cpi_yoy" for i in insights)
        assert any(i["indicator"] == "pmi_manufacturing" for i in insights)

    def test_generate_insights_gdp_down(self):
        from backend.analysis.real_data_analysis import RealDataAnalyzer

        analyzer = RealDataAnalyzer()
        eda = {
            "trend_analysis": {
                "gdp": {"trend_direction": "down"},
            }
        }
        insights = analyzer.generate_insights(eda)
        assert any("放缓" in i["title"] for i in insights)

    def test_visualization_data(self):
        from backend.analysis.real_data_analysis import RealDataAnalyzer

        analyzer = RealDataAnalyzer()
        df = pd.DataFrame(
            {
                "year": [2020, 2021, 2022],
                "gdp": [100, 110, 120],
                "gdp_primary": [10, 11, 12],
                "gdp_secondary": [40, 44, 48],
                "gdp_tertiary": [50, 55, 60],
                "cpi_yoy": [2.0, 1.5, 2.1],
                "pmi_manufacturing": [51, 50, 49],
            }
        )
        viz = analyzer.get_visualization_data(df)
        assert "gdp_trend" in viz
        assert "cpi_trend" in viz
        assert "pmi_trend" in viz
        assert "industry_structure" in viz

    def test_prepare_industry_structure_empty(self):
        from backend.analysis.real_data_analysis import RealDataAnalyzer

        analyzer = RealDataAnalyzer()
        result = analyzer._prepare_industry_structure_data(pd.DataFrame())
        assert result == {}

    def test_import_error_path(self, monkeypatch):
        from backend.analysis import real_data_analysis

        monkeypatch.setattr(real_data_analysis, "ak", None)
        analyzer = real_data_analysis.RealDataAnalyzer()
        with pytest.raises(ImportError):
            analyzer.fetch_macro_data()


class TestHousingAffordabilityExtended:
    """住房可负担性分析器扩展测试"""

    def test_metadata_and_name(self):
        from backend.analysis.housing_affordability_analyzer import HousingAffordabilityAnalyzer

        analyzer = HousingAffordabilityAnalyzer()
        assert analyzer.name() == "housing_affordability"
        assert "description" in analyzer.metadata()
        assert "median_house_price" in analyzer.required_indicators()

    def test_missing_indicators(self):
        from backend.analysis.housing_affordability_analyzer import HousingAffordabilityAnalyzer

        analyzer = HousingAffordabilityAnalyzer()
        result = analyzer.analyze({"median_house_price": 100})
        assert result["status"] == "insufficient_data"

    def test_invalid_data(self):
        from backend.analysis.housing_affordability_analyzer import HousingAffordabilityAnalyzer

        analyzer = HousingAffordabilityAnalyzer()
        result = analyzer.analyze({"median_house_price": 0, "median_household_income": 50000})
        assert result["status"] == "invalid_data"

    def test_stress_levels(self):
        from backend.analysis.housing_affordability_analyzer import HousingAffordabilityAnalyzer

        analyzer = HousingAffordabilityAnalyzer()
        cases = [
            (200000, 80000, "low"),
            (320000, 80000, "moderate"),
            (560000, 80000, "high"),
            (900000, 80000, "severe"),
        ]
        for price, income, expected_stress in cases:
            result = analyzer.analyze({"median_house_price": price, "median_household_income": income})
            assert result["status"] == "success"
            assert result["stress_level"] == expected_stress

    def test_zero_mortgage_rate(self):
        from backend.analysis.housing_affordability_analyzer import HousingAffordabilityAnalyzer

        analyzer = HousingAffordabilityAnalyzer()
        result = analyzer.analyze({"median_house_price": 240000, "median_household_income": 80000, "mortgage_rate": 0})
        assert result["status"] == "success"
        assert result["monthly_mortgage_pct_income"] > 0


class TestBaseAnalyzerExtended:
    """基础分析器扩展测试"""

    def test_summarize_data(self):
        from backend.analysis.base_analyzer import BaseAnalyzer

        class DummyAnalyzer(BaseAnalyzer):
            def run_full_analysis(self, data, save_results=True, output_dir="data/output", **kwargs):
                return {}

            def predict(self, data):
                return {}

        analyzer = DummyAnalyzer()
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        summary = analyzer.summarize_data(df)
        assert summary["shape"] == (3, 2)
        assert "numeric_summary" in summary

    def test_calculate_growth_rates(self):
        from backend.analysis.base_analyzer import BaseAnalyzer

        class DummyAnalyzer(BaseAnalyzer):
            def run_full_analysis(self, data, save_results=True, output_dir="data/output", **kwargs):
                return {}

            def predict(self, data):
                return {}

        analyzer = DummyAnalyzer()
        df = pd.DataFrame({"year": [2020, 2021, 2022], "gdp": [100, 110, 0]})
        result = analyzer.calculate_growth_rates(df, "gdp", "year")
        assert "gdp_growth" in result.columns

    def test_calculate_moving_average(self):
        from backend.analysis.base_analyzer import BaseAnalyzer

        class DummyAnalyzer(BaseAnalyzer):
            def run_full_analysis(self, data, save_results=True, output_dir="data/output", **kwargs):
                return {}

            def predict(self, data):
                return {}

        analyzer = DummyAnalyzer()
        df = pd.DataFrame({"gdp": [1, 2, 3, 4, 5]})
        result = analyzer.calculate_moving_average(df, "gdp", window=2)
        assert "gdp_ma2" in result.columns

    def test_calculate_correlation(self):
        from backend.analysis.base_analyzer import BaseAnalyzer

        class DummyAnalyzer(BaseAnalyzer):
            def run_full_analysis(self, data, save_results=True, output_dir="data/output", **kwargs):
                return {}

            def predict(self, data):
                return {}

        analyzer = DummyAnalyzer()
        df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [2, 4, 6, 8]})
        corr = analyzer.calculate_correlation(df)
        assert corr.loc["a", "b"] == pytest.approx(1.0, rel=1e-9)

    def test_detect_trend(self):
        from backend.analysis.base_analyzer import BaseAnalyzer

        class DummyAnalyzer(BaseAnalyzer):
            def run_full_analysis(self, data, save_results=True, output_dir="data/output", **kwargs):
                return {}

            def predict(self, data):
                return {}

        analyzer = DummyAnalyzer()
        df_up = pd.DataFrame({"year": [2020, 2021, 2022], "gdp": [100, 110, 120]})
        assert analyzer.detect_trend(df_up, "gdp", "year")["trend"] == "upward"

        df_down = pd.DataFrame({"year": [2020, 2021, 2022], "gdp": [120, 110, 100]})
        assert analyzer.detect_trend(df_down, "gdp", "year")["trend"] == "downward"

        df_flat = pd.DataFrame({"year": [2020, 2021], "gdp": [100, 100]})
        assert analyzer.detect_trend(df_flat, "gdp", "year")["trend"] == "flat"

        df_insufficient = pd.DataFrame({"year": [2020], "gdp": [100]})
        assert analyzer.detect_trend(df_insufficient, "gdp", "year")["trend"] == "insufficient_data"

    def test_data_quality_check(self):
        from backend.analysis.base_analyzer import BaseAnalyzer

        class DummyAnalyzer(BaseAnalyzer):
            def run_full_analysis(self, data, save_results=True, output_dir="data/output", **kwargs):
                return {}

            def predict(self, data):
                return {}

        analyzer = DummyAnalyzer()
        df = pd.DataFrame({"a": [1, 2, 3, 100], "b": [1, 1, 1, 1]})
        quality = analyzer.data_quality_check(df)
        assert quality["total_rows"] == 4
        assert "overall_quality" in quality

    def test_get_analysis_result(self):
        from backend.analysis.base_analyzer import BaseAnalyzer

        class DummyAnalyzer(BaseAnalyzer):
            def run_full_analysis(self, data, save_results=True, output_dir="data/output", **kwargs):
                return {}

            def predict(self, data):
                return {}

        analyzer = DummyAnalyzer()
        assert analyzer.get_analysis_result() is None
