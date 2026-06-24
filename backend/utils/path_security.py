"""路径安全工具 — 防止路径遍历攻击"""
import tempfile
from pathlib import Path

# 参考: backend.api.routes.static.safe_chart_path 已有的优秀实现
# （此处不直接导入，避免与 backend.api 包形成循环依赖）

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]
# 允许的数据目录
ALLOWED_DATA_DIRS = [
    PROJECT_ROOT / "data",
    PROJECT_ROOT / "data" / "forecasts",
    PROJECT_ROOT / "data" / "cities",
    PROJECT_ROOT / "output",
    PROJECT_ROOT / "reports",
    # 系统临时目录：用于测试与临时文件，仍受路径遍历校验保护
    Path(tempfile.gettempdir()),
]

def safe_join_path(base_dir: Path, user_path: str) -> Path:
    """
    安全地拼接路径，防止路径遍历。
    - 拒绝 .. 和绝对路径
    - 确保结果在 base_dir 内
    - 返回 resolve 后的路径
    """
    if not user_path:
        raise ValueError("路径不能为空")
    if ".." in user_path or user_path.startswith("/"):
        raise ValueError("路径包含非法字符")
    target = (base_dir / user_path).resolve()
    if not target.is_relative_to(base_dir.resolve()):
        raise ValueError(f"路径越界: {user_path}")
    return target

def validate_path_in_allowed_dirs(path: str | Path) -> Path:
    """
    验证路径在允许的目录内。
    """
    target = Path(path).resolve()
    for allowed_dir in ALLOWED_DATA_DIRS:
        allowed_resolved = allowed_dir.resolve()
        # 创建目录如果不存在
        allowed_resolved.mkdir(parents=True, exist_ok=True)
        if target.is_relative_to(allowed_resolved):
            return target
    raise ValueError(f"路径不在允许的目录内: {path}")
