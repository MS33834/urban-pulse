"""
导出 FastAPI OpenAPI 规范到 openapi.json / openapi.yaml。

用法:
    python scripts/export_openapi.py

输出:
    - openapi.json
    - openapi.yaml
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

project_root = Path(__file__).resolve().parent.parent


def main() -> None:
    """加载 FastAPI app 并导出 OpenAPI 文档。"""
    import os

    # 避免 production 校验干扰导出
    os.environ.setdefault("APP_ENV", "dev")
    os.environ.setdefault("SECRET_KEY", "export-secret-key-not-for-production")

    from backend.api.main import app

    openapi = app.openapi()

    json_path = project_root / "openapi.json"
    json_path.write_text(
        json.dumps(openapi, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Exported {json_path}")

    yaml_path = project_root / "openapi.yaml"
    yaml_path.write_text(
        yaml.safe_dump(openapi, sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"Exported {yaml_path}")


if __name__ == "__main__":
    main()
