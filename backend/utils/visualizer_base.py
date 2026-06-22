"""
可视化插件基类

遵循 docs/PLUGIN_ARCHITECTURE.md 的 VisualizerPlugin 接口，
允许社区通过继承此类并 drop-in 文件的方式扩展新的图表类型。
"""

from abc import ABC, abstractmethod


class VisualizerPlugin(ABC):
    """可视化插件基类。"""

    @abstractmethod
    def name(self) -> str:
        """可视化名称，例如 'time_series'、'radar'、'choropleth'。"""
        ...

    @abstractmethod
    def render(self, data: dict) -> str:
        """
        渲染可视化并返回 HTML/JS 字符串。

        Args:
            data: 包含图表所需数据的字典，格式由具体插件约定

        Returns:
            HTML 或 JavaScript 代码片段，可直接嵌入页面
        """
        ...

    def supported_data_types(self) -> list[str]:
        """返回该可视化支持的数据类型列表（可选扩展）。"""
        return ["generic"]
