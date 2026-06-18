"""社会实践/调查数据采集与集成测试"""

from __future__ import annotations

import textwrap

import pandas as pd
import pytest

from backend.data_collection.survey_collector import SurveyCollector
from backend.regions import Region, RegionLevel, RegionRegistry
from backend.regions.survey_integration import attach_survey_records, get_survey_indicators


class TestSurveyCollector:
    def test_load_csv(self, tmp_path):
        csv_path = tmp_path / "survey.csv"
        csv_path.write_text(
            textwrap.dedent(
                """\
                region_code,year,indicator,value,source,survey_type
                CN-GD-SZ,2023,social_satisfaction,78.5,深圳市统计局,社会调查
                CN-GD-SZ,2023,environment_satisfaction,82.1,深圳市统计局,社会调查
                CN-BJ,2023,social_satisfaction,75.0,北京市统计局,社会调查
                """
            ),
            encoding="utf-8",
        )

        collector = SurveyCollector()
        records = collector.load_file(csv_path)

        assert len(records) == 3
        assert records[0]["region_code"] == "CN-GD-SZ"
        assert records[0]["indicator"] == "social_satisfaction"
        assert records[0]["value"] == 78.5
        assert collector.list_indicators() == ["environment_satisfaction", "social_satisfaction"]

    def test_load_dataframe_with_invalid_rows(self):
        df = pd.DataFrame(
            {
                "region_code": ["CN-GD-SZ", "", "CN-BJ"],
                "year": [2023, 2023, "invalid"],
                "indicator": ["social_satisfaction", "social_satisfaction", "social_satisfaction"],
                "value": [78.5, 75.0, "bad"],
            }
        )
        collector = SurveyCollector()
        records = collector.load_dataframe(df)
        assert len(records) == 1
        assert records[0]["region_code"] == "CN-GD-SZ"

    def test_missing_required_columns(self):
        df = pd.DataFrame({"region_code": ["CN-GD-SZ"], "year": [2023]})
        collector = SurveyCollector()
        with pytest.raises(ValueError, match="缺少必要列"):
            collector.load_dataframe(df)

    def test_fetch_all_grouping(self):
        collector = SurveyCollector()
        collector.load_dataframe(
            pd.DataFrame(
                {
                    "region_code": ["CN-GD-SZ", "CN-GD-SZ", "CN-BJ"],
                    "year": [2023, 2023, 2023],
                    "indicator": ["social_satisfaction", "environment_satisfaction", "social_satisfaction"],
                    "value": [78.5, 82.1, 75.0],
                }
            )
        )
        grouped = collector.fetch_all(indicators=["social_satisfaction"])
        assert set(grouped.keys()) == {"social_satisfaction"}
        assert len(grouped["social_satisfaction"]) == 2


class TestSurveyIntegration:
    def test_attach_survey_records(self):
        registry = RegionRegistry()
        registry.register(Region(code="CN-GD-SZ", name="深圳", level=RegionLevel.CITY))

        records = [
            {"region_code": "CN-GD-SZ", "year": 2023, "indicator": "social_satisfaction", "value": 78.5},
            {"region_code": "CN-GD-SZ", "year": 2023, "indicator": "environment_satisfaction", "value": 82.1},
            {"region_code": "CN-GD-SZ", "year": 2022, "indicator": "social_satisfaction", "value": 76.0},
        ]

        stats = attach_survey_records(registry, records)
        assert stats == {"attached": 3, "skipped": 0, "unknown_regions": 0}

        region = registry.get("CN-GD-SZ")
        ts = region.get_time_series("social_satisfaction")
        assert ts == [76.0, 78.5]
        assert get_survey_indicators(region) == ["environment_satisfaction", "social_satisfaction"]

    def test_skip_unknown_region(self):
        registry = RegionRegistry()
        registry.register(Region(code="CN-GD-SZ", name="深圳", level=RegionLevel.CITY))

        records = [
            {"region_code": "CN-UNKNOWN", "year": 2023, "indicator": "social_satisfaction", "value": 78.5},
            {"region_code": "CN-GD-SZ", "year": 2023, "indicator": "social_satisfaction", "value": 78.5},
        ]

        stats = attach_survey_records(registry, records)
        assert stats["attached"] == 1
        assert stats["unknown_regions"] == 1

    def test_no_overwrite_by_default(self):
        registry = RegionRegistry()
        registry.register(
            Region(
                code="CN-GD-SZ",
                name="深圳",
                level=RegionLevel.CITY,
                historical_data=[{"year": 2023, "social_satisfaction": 80.0}],
            )
        )

        records = [
            {"region_code": "CN-GD-SZ", "year": 2023, "indicator": "social_satisfaction", "value": 78.5},
        ]

        stats = attach_survey_records(registry, records)
        assert stats["skipped"] == 1
        assert registry.get("CN-GD-SZ").get_time_series("social_satisfaction") == [80.0]
