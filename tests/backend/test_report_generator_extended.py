"""补充 backend.utils.report_generator 的覆盖测试。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.utils import report_generator as rg_module
from backend.utils.report_generator import (
    BaseReportGenerator,
    FlexibleReportGenerator,
    HTMLReportGenerator,
    JSONReportGenerator,
    MarkdownReportGenerator,
    OutputFormat,
    ReportConfig,
    ReportGeneratorFactory,
    ReportSection,
    create_report_section,
    generate_report,
    quick_report,
)


class TestBaseReportGenerator:
    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            BaseReportGenerator(ReportConfig(title="x"))


class TestJSONReportGenerator:
    def test_generate_and_save(self, tmp_path):
        config = ReportConfig(title="JSON Report")
        gen = JSONReportGenerator(config)
        section = ReportSection(title="S1", content={"k": "v"}, order=1)
        content = gen.generate([section])
        parsed = json.loads(content)
        assert parsed["title"] == "JSON Report"
        assert len(parsed["sections"]) == 1

        path = str(tmp_path / "report.json")
        assert gen.save(content, path) is True
        assert Path(path).exists()

    def test_save_failure_returns_false(self, tmp_path):
        config = ReportConfig(title="JSON Report")
        gen = JSONReportGenerator(config)
        with patch("builtins.open", side_effect=OSError("disk full")):
            assert gen.save("content", str(tmp_path / "x.json")) is False


class TestMarkdownReportGenerator:
    def test_generate_with_all_options(self, tmp_path):
        config = ReportConfig(
            title="MD Report",
            subtitle="Subtitle",
            include_toc=True,
            include_metadata=True,
        )
        gen = MarkdownReportGenerator(config)
        sections = [
            ReportSection(title="First", content={"k": "v"}, order=0),
            ReportSection(title="Second", content=["a", "b"], order=1, visualization="bar"),
        ]
        content = gen.generate(sections)
        assert "# MD Report" in content
        assert "**Subtitle**" in content
        assert "## 目录" in content
        assert "*图表类型: bar*" in content

    def test_generate_without_toc(self):
        config = ReportConfig(title="MD Report", include_toc=False)
        gen = MarkdownReportGenerator(config)
        sections = [ReportSection(title="Only", content="text", order=0)]
        content = gen.generate(sections)
        assert "## 目录" not in content

    def test_format_content_various_types(self):
        config = ReportConfig(title="MD Report")
        gen = MarkdownReportGenerator(config)
        assert "v" in gen._format_content({"k": "v"})
        assert "- a" in gen._format_content(["a", "b"])
        assert gen._format_content("text") == "text"
        assert "42" in gen._format_content(42)

    def test_save_success_and_failure(self, tmp_path):
        config = ReportConfig(title="MD Report")
        gen = MarkdownReportGenerator(config)
        path = str(tmp_path / "report.md")
        assert gen.save("# Hello", path) is True
        assert Path(path).exists()

        with patch("builtins.open", side_effect=OSError("fail")):
            assert gen.save("x", path) is False


class TestHTMLReportGenerator:
    def test_generate(self):
        config = ReportConfig(title="HTML Report", subtitle="Sub")
        gen = HTMLReportGenerator(config)
        sections = [
            ReportSection(title="Dict", content={"k": "v"}, order=0),
            ReportSection(title="List", content=["a", "b"], order=1),
            ReportSection(title="Text", content="hello", order=2),
            ReportSection(title="Number", content=42, order=3),
        ]
        html = gen.generate(sections)
        assert "<html" in html
        assert "<table" in html
        assert "<ul>" in html
        assert "hello" in html
        assert "42" in html

    def test_format_empty_dict(self):
        config = ReportConfig(title="HTML Report")
        gen = HTMLReportGenerator(config)
        assert gen._format_content({}) == "<p>暂无数据</p>"

    def test_save_success_and_failure(self, tmp_path):
        config = ReportConfig(title="HTML Report")
        gen = HTMLReportGenerator(config)
        path = str(tmp_path / "report.html")
        assert gen.save("<html></html>", path) is True
        assert Path(path).exists()

        with patch("builtins.open", side_effect=OSError("fail")):
            assert gen.save("x", path) is False


class TestReportGeneratorFactory:
    def test_register_custom_generator(self):
        class CustomGenerator(BaseReportGenerator):
            def generate(self, sections):
                return "custom"

            def save(self, content, filepath):
                return True

        ReportGeneratorFactory.register(OutputFormat.PDF, CustomGenerator)
        config = ReportConfig(title="Custom", format=OutputFormat.PDF)
        gen = ReportGeneratorFactory.create(config)
        assert isinstance(gen, CustomGenerator)
        assert gen.generate([]) == "custom"

    def test_create_unknown_format_fallback(self):
        config = ReportConfig(title="Fallback", format=OutputFormat.CSV)
        gen = ReportGeneratorFactory.create(config)
        assert isinstance(gen, JSONReportGenerator)


class TestFlexibleReportGenerator:
    def test_create_section(self):
        gen = FlexibleReportGenerator()
        section = gen.create_section("S", {"x": 1}, visualization="line", order=2, tag="test")
        assert section.title == "S"
        assert section.visualization == "line"
        assert section.order == 2
        assert section.metadata == {"tag": "test"}

    def test_quick_report_markdown(self):
        gen = FlexibleReportGenerator()
        content = gen.quick_report("Quick", {"a": 1})
        assert "# Quick" in content

    def test_quick_report_html(self):
        gen = FlexibleReportGenerator()
        content = gen.quick_report("Quick HTML", {"a": 1}, format="html")
        assert "<html" in content

    def test_quick_report_json(self):
        gen = FlexibleReportGenerator()
        content = gen.quick_report("Quick JSON", {"a": 1}, format="json")
        parsed = json.loads(content)
        assert parsed["title"] == "Quick JSON"

    def test_quick_report_save(self, tmp_path):
        gen = FlexibleReportGenerator()
        path = str(tmp_path / "quick.md")
        content = gen.quick_report("Quick", {"a": 1}, output_path=path)
        assert Path(path).exists()
        assert "# Quick" in content


class TestModuleHelpers:
    def test_generate_report(self):
        sections = [ReportSection(title="S", content={"a": 1}, order=0)]
        config = ReportConfig(title="Helper", format=OutputFormat.MARKDOWN)
        content = generate_report(sections, config)
        assert "# Helper" in content

    def test_create_report_section(self):
        section = create_report_section("S", {"a": 1}, order=1)
        assert section.title == "S"
        assert section.order == 1

    def test_quick_report(self):
        content = quick_report("Quick", {"a": 1}, format="markdown")
        assert "# Quick" in content


class TestReportGeneratorInstance:
    def test_global_instance_exists(self):
        assert isinstance(rg_module.report_generator, FlexibleReportGenerator)
