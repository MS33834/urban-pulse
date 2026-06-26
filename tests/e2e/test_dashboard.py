"""
仪表盘 E2E 测试 — 验证前端页面可渲染且核心 API 可被页面调用。

标记: e2e
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def _navigate(page: Page, path: str) -> None:
    base_url = page._base_url  # type: ignore[attr-defined]
    page.goto(f"{base_url}{path}")


def test_dashboard_loads(page: Page):
    """仪表盘页面加载成功并包含项目标题。"""
    _navigate(page, "/dashboard")
    expect(page).to_have_title("Urban Pulse")
    # 页面主标题应包含项目名或城市脉搏字样
    body = page.locator("body")
    expect(body).to_contain_text("Urban Pulse")


def test_dashboard_api_status_is_healthy(page: Page):
    """页面加载后可通过 /health 检查服务状态。"""
    _navigate(page, "/dashboard")
    response = page.request.get(f"{page._base_url}/health")  # type: ignore[attr-defined]
    assert response.status == 200
    body = response.json()
    assert body["status"] == "healthy"


def test_dashboard_static_assets_load(page: Page):
    """CSS 与 JS 静态资源可访问且返回 200。"""
    base_url = page._base_url  # type: ignore[attr-defined]
    css_resp = page.request.get(f"{base_url}/css/main.css")
    js_resp = page.request.get(f"{base_url}/js/api-client.js")
    assert css_resp.status == 200
    assert js_resp.status == 200
    assert "text/css" in css_resp.headers.get("content-type", "")
    assert "javascript" in js_resp.headers.get("content-type", "")


def test_viz_demo_page_loads(page: Page):
    """viz-demo 页面可访问。"""
    _navigate(page, "/viz-demo.html")
    expect(page.locator("body")).to_be_visible()


def test_dashboard_has_navigation_or_cards(page: Page):
    """仪表盘至少包含一个可交互元素(导航、卡片或按钮)。"""
    _navigate(page, "/dashboard")
    # 通用选择器: nav / button / .card / section
    selectors = ["nav", "button", ".card", "section", "main"]
    found = False
    for selector in selectors:
        if page.locator(selector).count() > 0:
            found = True
            break
    assert found, "仪表盘未找到任何导航/卡片/区块元素"
