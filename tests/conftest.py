"""
Pytest configuration for the Regional Economic Analysis Platform.

Ensures the project root is on sys.path so ``import backend.api`` works
regardless of where pytest is invoked from.
"""

import os
import sys
from pathlib import Path

# Project root is the parent of the tests/ directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure default settings
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
# 测试环境允许加载 demo 外部插件
os.environ.setdefault("ALLOWED_PLUGINS", "demo")


# --------------------------------------------------------------------------- #
# Pytest CLI 选项
# --------------------------------------------------------------------------- #


def pytest_addoption(parser):
    """注册 --e2e 选项;未指定时默认跳过 e2e 浏览器测试。"""
    parser.addoption(
        "--e2e",
        action="store_true",
        default=False,
        help="运行 E2E 浏览器测试(需要 playwright 与浏览器已安装)",
    )


def pytest_collection_modifyitems(config, items):
    """未传 --e2e 时自动跳过标记为 e2e 的测试。"""
    if config.getoption("--e2e"):
        return
    skip_e2e = __import__("pytest").mark.skip(
        reason="跳过 E2E 浏览器测试;使用 pytest --e2e 显式启用"
    )
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_e2e)
