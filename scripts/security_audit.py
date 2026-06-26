"""
安全审计脚本

用法:
    python scripts/security_audit.py

依赖:
    pip install pip-audit  # 可选,未安装时脚本会提示

功能:
    1. 使用 pip-audit 扫描已安装依赖的已知 CVE
    2. 检查常见敏感文件/目录权限
    3. 输出可操作的修复建议
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()


def _run_pip_audit() -> tuple[bool, str]:
    """运行 pip-audit 扫描,返回 (是否成功, 输出文本)。"""
    try:
        result = subprocess.run(
            ["pip-audit", "--format=json"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, "未找到 pip-audit,请运行: pip install pip-audit"

    if result.returncode == 0:
        return True, "未发现已知漏洞"

    try:
        findings = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False, result.stdout or result.stderr

    messages = []
    for item in findings.get("dependencies", []):
        name = item.get("name", "unknown")
        version = item.get("version", "unknown")
        vulns = item.get("vulns", [])
        for vuln in vulns:
            messages.append(
                f"{name}=={version}: {vuln.get('id')} {vuln.get('fix_versions')} "
                f"{vuln.get('description', '')[:120]}"
            )
    return False, "\n".join(messages) if messages else (result.stdout or result.stderr)


def _check_file_permissions() -> list[str]:
    """检查敏感文件/目录权限,返回问题列表。"""
    issues: list[str] = []
    sensitive_files = [
        PROJECT_ROOT / ".env",
        Path.home() / ".git-credentials",
    ]
    for path in sensitive_files:
        if path.exists():
            mode = path.stat().st_mode & 0o777
            if mode & 0o077:
                issues.append(f"{path} 权限过宽: {oct(mode)},建议 chmod 600")
    return issues


def main() -> int:
    print("=" * 60)
    print("Urban Pulse 安全审计")
    print("=" * 60)

    print("\n[1/2] 依赖漏洞扫描 (pip-audit)")
    ok, message = _run_pip_audit()
    print(message)

    print("\n[2/2] 敏感文件权限检查")
    issues = _check_file_permissions()
    if issues:
        for issue in issues:
            print(f"  ! {issue}")
    else:
        print("  未发现权限问题")

    print("\n" + "=" * 60)
    if ok and not issues:
        print("审计通过,未发现问题")
        return 0
    print("审计发现潜在问题,请查看上方建议")
    return 1


if __name__ == "__main__":
    sys.exit(main())
