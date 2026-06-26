"""
文件工具模块
"""

import json
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pandas as pd

from backend.utils.path_security import validate_path_in_allowed_dirs

logger = logging.getLogger(__name__)


def _atomic_write(path: str | Path, write_func: Callable[[Path], None]) -> None:
    """
    原子写入辅助函数。

    先写入同目录下的临时文件(.tmp 后缀),写入完成后用 os.replace 原子替换原文件,
    确保崩溃时原文件不被损坏。异常时清理临时文件。

    Args:
        path: 目标文件路径
        write_func: 接收临时文件路径并执行写入的回调
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.parent / (target.name + ".tmp")
    try:
        write_func(tmp_path)
        # os.replace 在同一文件系统内是原子操作
        os.replace(tmp_path, target)
    finally:
        # 异常时清理残留的临时文件(os.replace 成功后临时文件已不存在)
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


class FileUtils:
    """文件工具类"""

    @staticmethod
    def ensure_directory(path: str | Path) -> Path:
        """确保目录存在，不存在则创建"""
        dir_path = Path(path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    @staticmethod
    def save_json(data: Any, path: str | Path, indent: int = 2) -> None:
        """保存JSON文件（原子写入）"""
        validate_path_in_allowed_dirs(path)

        def _write(tmp: Path) -> None:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)

        _atomic_write(path, _write)
        logger.info(f"JSON文件已保存: {path}")

    @staticmethod
    def load_json(path: str | Path) -> Any:
        """加载JSON文件"""
        validate_path_in_allowed_dirs(path)
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def save_csv(df: pd.DataFrame, path: str | Path, **kwargs) -> None:
        """保存CSV文件（原子写入）"""
        validate_path_in_allowed_dirs(path)

        def _write(tmp: Path) -> None:
            df.to_csv(tmp, index=False, **kwargs)

        _atomic_write(path, _write)
        logger.info(f"CSV文件已保存: {path}")

    @staticmethod
    def load_csv(path: str | Path, **kwargs) -> pd.DataFrame:
        """加载CSV文件"""
        validate_path_in_allowed_dirs(path)
        return cast(pd.DataFrame, pd.read_csv(path, **kwargs))

    @staticmethod
    def save_excel(df: pd.DataFrame, path: str | Path, sheet_name: str = "Sheet1", **kwargs) -> None:
        """保存Excel文件（原子写入）"""
        validate_path_in_allowed_dirs(path)

        def _write(tmp: Path) -> None:
            df.to_excel(tmp, sheet_name=sheet_name, index=False, **kwargs)

        _atomic_write(path, _write)
        logger.info(f"Excel文件已保存: {path}")

    @staticmethod
    def load_excel(path: str | Path, sheet_name: str | int = 0, **kwargs) -> pd.DataFrame:
        """加载Excel文件"""
        validate_path_in_allowed_dirs(path)
        return pd.read_excel(path, sheet_name=sheet_name, **kwargs)

    @staticmethod
    def list_files(directory: str | Path, pattern: str = "*") -> list[Path]:
        """列出目录下的文件"""
        validate_path_in_allowed_dirs(directory)
        dir_path = Path(directory)
        if not dir_path.exists():
            return []
        return list(dir_path.glob(pattern))

    @staticmethod
    def file_exists(path: str | Path) -> bool:
        """检查文件是否存在"""
        return Path(path).exists()
