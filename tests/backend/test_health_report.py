"""CEHI PDF 诊断报告生成测试。

覆盖：
- generate_cehi_pdf 能正常返回非空 PDF 字节
- PDF 报告接口能正确返回 application/pdf 响应
"""

from __future__ import annotations

import pytest

from backend.core.health_index import CEHIEngine, CEHIResult, get_demo_values
from backend.core.health_report import generate_cehi_pdf


@pytest.fixture
def sample_result() -> CEHIResult:
    """使用演示数据生成 CEHI 结果。"""
    engine = CEHIEngine()
    return engine.calculate("测试市", 2024, get_demo_values())


def test_generate_cehi_pdf_returns_non_empty_bytes(sample_result: CEHIResult):
    """generate_cehi_pdf 返回非空 PDF 字节。"""
    pdf_bytes = generate_cehi_pdf(sample_result)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"


def test_generate_cehi_pdf_with_empty_data():
    """空数据时 generate_cehi_pdf 仍能返回合法 PDF。"""
    engine = CEHIEngine()
    result = engine.calculate("空数据市", 2024, {})
    pdf_bytes = generate_cehi_pdf(result)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"


@pytest.mark.integration
def test_export_cehi_pdf_endpoint(api_client):
    """POST /api/v1/health/report/pdf 返回 PDF 附件。"""
    response = api_client.post(
        "/api/v1/health/report/pdf",
        json={"city_name": "接口测试市", "year": 2024},
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert "attachment" in response.headers["Content-Disposition"]
    assert len(response.content) > 0
    assert response.content[:4] == b"%PDF"
