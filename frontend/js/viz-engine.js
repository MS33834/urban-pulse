/**
 * Urban Pulse 通用可视化引擎
 *
 * 接收后端返回的通用图表配置 + ECharts option，自动渲染并绑定交互。
 */

class VizEngine {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      throw new Error(`容器 #${containerId} 不存在`);
    }
    this.theme = options.theme || "urban_pulse";
    this.onDrillDown = options.onDrillDown || null;
    this.chart = null;
  }

  /**
   * 渲染图表
   * @param {object} payload 后端返回的图表对象，包含 echarts_option
   */
  render(payload) {
    if (this.chart) {
      this.chart.dispose();
    }
    this.chart = echarts.init(this.container, this.theme);

    const option = payload.echarts_option || payload;
    this._bindInteractions(option, payload);
    this.chart.setOption(option);

    window.addEventListener("resize", () => this.chart && this.chart.resize());
    return this.chart;
  }

  /**
   * 绑定高级交互
   */
  _bindInteractions(option, payload) {
    // 下钻事件
    if (this.onDrillDown && option.series && option.series.length > 0) {
      this.chart.off("click");
      this.chart.on("click", (params) => {
        if (params.componentType === "series") {
          this.onDrillDown(params, payload);
        }
      });
    }
  }

  /**
   * 清空容器
   */
  clear() {
    if (this.chart) {
      this.chart.dispose();
      this.chart = null;
    }
  }
}

/**
 * 简单的 Dashboard 组件，支持多图表自动布局
 */
class VizDashboard {
  constructor(containerSelector, api, options = {}) {
    this.container = document.querySelector(containerSelector);
    this.api = api;
    this.engines = [];
    this.options = options;
  }

  async autoRender(data, maxCharts = 4) {
    this.container.innerHTML = "";
    this.engines.forEach((e) => e.clear());
    this.engines = [];

    const result = await this.api.vizAuto(data, maxCharts);
    if (!result.success) {
      throw new Error("自动可视化失败");
    }

    const grid = document.createElement("div");
    grid.className = "viz-grid";

    result.charts.forEach((chart, idx) => {
      const card = document.createElement("div");
      card.className = "viz-card";
      card.innerHTML = `
        <div class="viz-card-header">
          <h3>${chart.title}</h3>
          <span class="viz-badge">${chart.chart_type}</span>
        </div>
        <div id="viz-chart-${idx}" class="viz-chart"></div>
        <p class="viz-reason">${chart.reason}</p>
      `;
      grid.appendChild(card);

      // 延迟初始化，确保 DOM 已插入
      setTimeout(() => {
        const engine = new VizEngine(`viz-chart-${idx}`, {
          onDrillDown: this.options.onDrillDown,
        });
        engine.render(chart);
        this.engines.push(engine);
      }, 0);
    });

    this.container.appendChild(grid);
    return result;
  }
}

window.VizEngine = VizEngine;
window.VizDashboard = VizDashboard;
