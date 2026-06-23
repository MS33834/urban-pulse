"""
社区验证仪表板（Phase 5 — Community validation dashboard）

将 ForecastValidator 的验证报告渲染为可嵌入 GitHub Pages 的静态 HTML。
"""

from __future__ import annotations

import html
from typing import Any

from backend.core.forecast_validation import ForecastValidator
from backend.utils.html_table_visualizer import HtmlTableVisualizer


class ValidationDashboard:
    """预测准确率验证仪表板。"""

    def __init__(self, validator: ForecastValidator | None = None) -> None:
        self.validator = validator or ForecastValidator()

    def render(self) -> str:
        """渲染完整 HTML 仪表板。"""
        report = self.validator.report()
        summary = report["summary"]
        table_visualizer = HtmlTableVisualizer()

        summary_html = table_visualizer.render(
            {
                "title": "总体指标",
                "records": [
                    {"指标": "已验证样本数", "数值": summary["count"]},
                    {"指标": "MAE", "数值": summary["mae"]},
                    {"指标": "MAPE (%)", "数值": summary["mape"]},
                    {"指标": "RMSE", "数值": summary["rmse"]},
                    {"指标": "Bias", "数值": summary["bias"]},
                ],
            }
        )

        by_model_html = self._metrics_table("按模型", report["by_model"])
        by_city_html = self._metrics_table("按城市", report["by_city"])
        by_indicator_html = self._metrics_table("按指标", report["by_indicator"])

        hit_rate_html = self._hit_rate_table(report["hit_rate_by_model"])

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Urban Pulse 预测准确率验证仪表板</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 2rem; color: #333; }}
h1, h2 {{ color: #1a73e8; }}
h1 {{ border-bottom: 2px solid #1a73e8; padding-bottom: .5rem; }}
.up-html-table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
.up-html-table th, .up-html-table td {{ border: 1px solid #ddd; padding: .5rem; text-align: left; }}
.up-html-table th {{ background: #f1f3f4; }}
.up-visualization {{ margin-bottom: 2rem; }}
</style>
</head>
<body>
<h1>Urban Pulse 预测准确率验证仪表板</h1>
<p>生成时间: {html.escape(str(report["generated_at"]))}</p>
{summary_html}
{by_model_html}
{by_city_html}
{by_indicator_html}
{hit_rate_html}
</body>
</html>"""

    def _metrics_table(self, title: str, data: dict[str, Any]) -> str:
        if not data:
            return f'<div class="up-visualization"><h2>{html.escape(title)}</h2><p>暂无数据</p></div>'
        records = [
            {
                "维度": key,
                "样本数": metrics["count"],
                "MAE": metrics["mae"],
                "MAPE": metrics["mape"],
                "RMSE": metrics["rmse"],
                "Bias": metrics["bias"],
            }
            for key, metrics in data.items()
        ]
        return HtmlTableVisualizer().render({"title": title, "records": records})

    def _hit_rate_table(self, data: dict[str, float]) -> str:
        if not data:
            return '<div class="up-visualization"><h2>置信区间命中率（按模型）</h2><p>暂无数据</p></div>'
        records = [{"模型": model, "命中率": rate} for model, rate in data.items()]
        return HtmlTableVisualizer().render({"title": "置信区间命中率（按模型）", "records": records})


def generate_validation_dashboard(output_path: str | None = None) -> str:
    """
    一键生成验证仪表板 HTML。

    Args:
        output_path: 可选，输出文件路径

    Returns:
        HTML 字符串
    """
    html_content = ValidationDashboard().render()
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    return html_content
