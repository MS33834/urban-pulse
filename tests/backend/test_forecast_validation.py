"""
预测存档与准确率验证测试（Phase 5）
"""

from __future__ import annotations

import pytest

from backend.core.forecast_archive import ForecastArchive, ForecastSnapshot
from backend.core.forecast_validation import ForecastValidator, ValidationMetrics
from backend.core.validation_dashboard import ValidationDashboard, generate_validation_dashboard


@pytest.fixture
def archive(tmp_path):
    archive = ForecastArchive(archive_dir=tmp_path)
    yield archive
    archive.clear()


class TestForecastArchive:
    def test_save_and_find(self, archive):
        snapshot = ForecastSnapshot(
            model="linear_trend",
            city_code="shanghai",
            indicator="gdp",
            forecast_date="2024-01-01",
            target_year=2025,
            predicted_value=800.0,
            confidence_interval=(750.0, 850.0),
        )
        fid = archive.save(snapshot)
        found = archive.find_by_id(fid)
        assert found is not None
        assert found.predicted_value == pytest.approx(800.0)

    def test_find_pending(self, archive):
        archive.save(
            ForecastSnapshot(
                model="linear_trend",
                city_code="shanghai",
                indicator="gdp",
                forecast_date="2024-01-01",
                target_year=2025,
                predicted_value=800.0,
            )
        )
        pending = archive.find_pending()
        assert len(pending) == 1

    def test_update_actual(self, archive):
        snapshot = ForecastSnapshot(
            model="linear_trend",
            city_code="shanghai",
            indicator="gdp",
            forecast_date="2024-01-01",
            target_year=2025,
            predicted_value=800.0,
        )
        fid = archive.save(snapshot)
        assert archive.update_actual(fid, 820.0) is True
        updated = archive.find_by_id(fid)
        assert updated.actual_value == pytest.approx(820.0)

    def test_update_actual_by_match(self, archive):
        archive.save(
            ForecastSnapshot(
                model="linear_trend",
                city_code="shanghai",
                indicator="gdp",
                forecast_date="2024-01-01",
                target_year=2025,
                predicted_value=800.0,
            )
        )
        count = archive.update_actual_by_match("linear_trend", "shanghai", "gdp", 2025, 820.0)
        assert count == 1


class TestForecastValidator:
    def test_compute_metrics(self):
        metrics = ForecastValidator.compute_metrics([100.0, 110.0, 120.0], [102.0, 108.0, 125.0])
        assert isinstance(metrics, ValidationMetrics)
        assert metrics.count == 3
        assert metrics.mae is not None
        assert metrics.mae > 0

    def test_summary_and_by_model(self, archive):
        archive.save(
            ForecastSnapshot(
                model="linear_trend",
                city_code="shanghai",
                indicator="gdp",
                forecast_date="2024-01-01",
                target_year=2025,
                predicted_value=100.0,
                actual_value=102.0,
            )
        )
        archive.save(
            ForecastSnapshot(
                model="linear_trend",
                city_code="beijing",
                indicator="gdp",
                forecast_date="2024-01-01",
                target_year=2025,
                predicted_value=200.0,
                actual_value=205.0,
            )
        )
        validator = ForecastValidator(archive=archive)
        summary = validator.summary()
        assert summary.count == 2
        assert summary.mae is not None

        by_model = validator.by_model()
        assert "linear_trend" in by_model

    def test_hit_rate(self, archive):
        archive.save(
            ForecastSnapshot(
                model="linear_trend",
                city_code="shanghai",
                indicator="gdp",
                forecast_date="2024-01-01",
                target_year=2025,
                predicted_value=100.0,
                confidence_interval=(95.0, 105.0),
                actual_value=102.0,
            )
        )
        validator = ForecastValidator(archive=archive)
        hit_rate = validator.hit_rate()
        assert hit_rate.get("linear_trend") == 1.0

    def test_report_formats(self, archive):
        archive.save(
            ForecastSnapshot(
                model="linear_trend",
                city_code="shanghai",
                indicator="gdp",
                forecast_date="2024-01-01",
                target_year=2025,
                predicted_value=100.0,
                actual_value=102.0,
            )
        )
        validator = ForecastValidator(archive=archive)
        report = validator.report()
        assert "summary" in report
        assert "by_model" in report
        assert "linear_trend" in validator.to_markdown()


class TestValidationDashboard:
    def test_render_html(self, archive):
        archive.save(
            ForecastSnapshot(
                model="linear_trend",
                city_code="shanghai",
                indicator="gdp",
                forecast_date="2024-01-01",
                target_year=2025,
                predicted_value=100.0,
                actual_value=102.0,
            )
        )
        validator = ForecastValidator(archive=archive)
        html = ValidationDashboard(validator=validator).render()
        assert "Urban Pulse 预测准确率验证仪表板" in html
        assert "linear_trend" in html

    def test_generate_dashboard_to_file(self, archive, tmp_path):
        archive.save(
            ForecastSnapshot(
                model="linear_trend",
                city_code="shanghai",
                indicator="gdp",
                forecast_date="2024-01-01",
                target_year=2025,
                predicted_value=100.0,
                actual_value=102.0,
            )
        )
        output = tmp_path / "dashboard.html"
        html = generate_validation_dashboard(output_path=str(output))
        assert output.exists()
        assert "Urban Pulse 预测准确率验证仪表板" in html
