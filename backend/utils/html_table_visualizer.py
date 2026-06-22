"""
HTML 表格可视化器（插件示例）

将字典或列表数据渲染为简单 HTML 表格，
作为 VisualizerPlugin 的入门示例，便于快速嵌入静态报告。
"""

import html
from typing import Any

from backend.utils.visualizer_base import VisualizerPlugin


class HtmlTableVisualizer(VisualizerPlugin):
    """HTML 表格可视化器插件。"""

    def metadata(self) -> dict[str, Any]:
        return {
            "description": "将字典或列表数据渲染为简单 HTML 表格，便于嵌入静态报告。",
            "version": "0.1.0",
            "author": "Urban Pulse Team",
            "tags": ["visualization", "html", "table"],
            "parameters": [],
            "example": {
                "title": "城市 GDP",
                "records": [
                    {"city": "深圳", "gdp": 3000},
                    {"city": "上海", "gdp": 4500},
                ],
            },
        }

    def name(self) -> str:
        return "html_table"

    def supported_data_types(self) -> list[str]:
        return ["table", "records", "dict"]

    def render(self, data: dict) -> str:
        """
        将数据渲染为 HTML 表格。

        Args:
            data: 支持以下格式
                - {"headers": [...], "rows": [[...], ...]}
                - {"records": [{"col": val, ...}, ...]}
                - {"title": "...", ...} 可选标题

        Returns:
            HTML 字符串
        """
        title = data.get("title", "")

        if "records" in data:
            records = data["records"]
            if not records:
                return self._wrap(title, "<p>无数据</p>")
            headers = list(records[0].keys())
            rows = [[record.get(h, "") for h in headers] for record in records]
        elif "headers" in data and "rows" in data:
            headers = list(data["headers"])
            rows = [list(row) for row in data["rows"]]
        else:
            return self._wrap(title, "<p>不支持的数据格式</p>")

        html_parts = ['<table class="up-html-table">']
        html_parts.append("<thead><tr>")
        for header in headers:
            html_parts.append(f"<th>{html.escape(str(header))}</th>")
        html_parts.append("</tr></thead>")

        html_parts.append("<tbody>")
        for row in rows:
            html_parts.append("<tr>")
            for cell in row:
                html_parts.append(f"<td>{html.escape(str(cell))}</td>")
            html_parts.append("</tr>")
        html_parts.append("</tbody></table>")

        return self._wrap(title, "\n".join(html_parts))

    def _wrap(self, title: str, content: str) -> str:
        parts = ['<div class="up-visualization">']
        if title:
            parts.append(f"<h4>{html.escape(str(title))}</h4>")
        parts.append(content)
        parts.append("</div>")
        return "\n".join(parts)
