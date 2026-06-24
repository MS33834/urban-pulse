"""
导出工具模块
"""

import html
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from backend.utils.file_utils import _atomic_write
from backend.utils.path_security import validate_path_in_allowed_dirs

logger = logging.getLogger(__name__)


class ExportUtils:
    """导出工具类"""

    @staticmethod
    def _sanitize_cell(value: Any) -> Any:
        """清洗单元格值，防止 CSV/Excel 公式注入"""
        if isinstance(value, str) and value:
            # 以公式触发字符开头的字符串，加单引号前缀
            if value[0] in ("=", "+", "-", "@", "\t", "\r"):
                return f"'{value}"
        return value

    @staticmethod
    def export_csv(df: pd.DataFrame, path: str, **kwargs) -> str:
        """导出为CSV（原子写入）"""
        validate_path_in_allowed_dirs(path)
        # 清洗单元格，防止公式注入
        sanitized_df = df.copy()
        for col in sanitized_df.columns:
            sanitized_df[col] = sanitized_df[col].apply(ExportUtils._sanitize_cell)

        def _write(tmp: Path) -> None:
            sanitized_df.to_csv(tmp, index=False, **kwargs)

        _atomic_write(path, _write)
        logger.info(f"CSV已导出: {path}")
        return path

    @staticmethod
    def export_excel(df: pd.DataFrame, path: str, sheet_name: str = "Sheet1", **kwargs) -> str:
        """导出为Excel（原子写入）"""
        validate_path_in_allowed_dirs(path)
        # 清洗单元格，防止公式注入
        sanitized_df = df.copy()
        for col in sanitized_df.columns:
            sanitized_df[col] = sanitized_df[col].apply(ExportUtils._sanitize_cell)

        def _write(tmp: Path) -> None:
            sanitized_df.to_excel(tmp, sheet_name=sheet_name, index=False, **kwargs)

        _atomic_write(path, _write)
        logger.info(f"Excel已导出: {path}")
        return path

    @staticmethod
    def export_json(data: Any, path: str, indent: int = 2, **kwargs) -> str:
        """导出为JSON（原子写入）"""
        validate_path_in_allowed_dirs(path)

        def _write(tmp: Path) -> None:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=indent, **kwargs)

        _atomic_write(path, _write)
        logger.info(f"JSON已导出: {path}")
        return path

    @staticmethod
    def export_html(df: pd.DataFrame, path: str, title: str = "数据报表", **kwargs) -> str:
        """导出为HTML（原子写入）"""
        validate_path_in_allowed_dirs(path)
        # 确保 to_html 转义单元格内容，防止 XSS
        kwargs.setdefault("escape", True)
        safe_title = html.escape(title)
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{safe_title}</title>
            <style>
                table {{ border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                h1 {{ color: #333; font-family: Arial, sans-serif; }}
            </style>
        </head>
        <body>
            <h1>{safe_title}</h1>
            {df.to_html(index=False, **kwargs)}
        </body>
        </html>
        """

        def _write(tmp: Path) -> None:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(html_template)

        _atomic_write(path, _write)
        logger.info(f"HTML已导出: {path}")
        return path

    @staticmethod
    def export_dict_to_csv(data: dict[str, list[Any]], path: str) -> str:
        """将字典导出为CSV"""
        df = pd.DataFrame(data)
        return ExportUtils.export_csv(df, path)

    @staticmethod
    def merge_dataframes(dfs: dict[str, pd.DataFrame], path: str) -> str:
        """合并多个DataFrame导出到同一个Excel文件的不同sheet"""
        validate_path_in_allowed_dirs(path)
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for sheet_name, df in dfs.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        logger.info(f"多Sheet Excel已导出: {path}")
        return path


export_utils = ExportUtils()

# 模块级便捷函数，便于直接导入使用
export_csv = ExportUtils.export_csv
