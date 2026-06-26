"""
E2E 测试共享夹具 — 提供 Playwright page 与本地后端服务。

依赖:
  - playwright 已安装且浏览器已下载
  - 可通过 `python -m backend.api.main` 启动服务
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from collections.abc import Generator
from pathlib import Path

import pytest

# Playwright 是可选依赖;未安装时整体跳过 e2e 标记测试
try:
    from playwright.sync_api import Page, sync_playwright
except Exception as exc:  # pragma: no cover
    pytest.skip(f"playwright 未安装或浏览器未就绪: {exc}", allow_module_level=True)


project_root = Path(__file__).parent.parent.parent


def _find_free_port() -> int:
    """获取一个可用的本地端口。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_for_server(url: str, timeout: float = 30.0) -> bool:
    """轮询等待服务就绪。"""
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                return resp.status == 200
        except Exception:
            time.sleep(0.2)
    return False


@pytest.fixture(scope="session")
def base_url() -> str:
    """启动后端服务并返回访问地址。"""
    port = _find_free_port()
    env = {
        **dict(__import__("os").environ),
        "APP_HOST": "127.0.0.1",
        "APP_PORT": str(port),
        "APP_ENV": "dev",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "backend.api.main"],
        cwd=str(project_root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    url = f"http://127.0.0.1:{port}"
    if not _wait_for_server(f"{url}/health", timeout=30.0):
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
        raise RuntimeError(f"后端服务在 {url} 启动失败")

    yield url

    proc.terminate()
    try:
        proc.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="function")
def page(base_url: str) -> Generator[Page, None, None]:
    """创建新浏览器页面并在测试结束后关闭。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        pg = context.new_page()
        pg._base_url = base_url  # type: ignore[attr-defined]
        yield pg
        context.close()
        browser.close()
