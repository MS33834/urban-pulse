# Urban Pulse Phase 2 路线图

> 创建时间：2026-06-25
> 目标：将 Urban Pulse 从「基础城市经济数据展示」升级为「灵活可视化 + 经济数学模型驱动」的城市经济智能平台。

## 当前进展

- [x] 通用可视化配置协议（VCP）与数据画像
- [x] 图表推荐器：折线、面积、柱状、散点、雷达、热力图、箱线图、仪表盘、地图、桑基图、赛跑图
- [x] 后端 ECharts 预渲染器：支持 line / bar / scatter / radar / heatmap / box / gauge / map / sankey / racing_bar
- [x] 可视化 API：`/viz/profile`、`/viz/recommend`、`/viz/render`、`/viz/auto`
- [x] 前端通用可视化引擎 `frontend/js/viz-engine.js`（含下钻回调）
- [x] 智能可视化模块整合进主仪表盘 `index.html`（第 9 个标签页）
- [x] 从真实城市数据自动画像并生成高级图表
- [x] 图表配置导出、下钻提示等高级交互
- [x] 数学模型库：VAR、XGBoost、TFP、区位商、DPSR 韧性模型
- [x] 数据库扩展：model_runs、forecasts、indicator_scores、viz_configs 表
- [ ] 智能报告与政策建议生成（待后续迭代）

---

## 一、背景与目标

当前项目已具备：
- 35 个中国城市的基础经济数据（2020–2024）
- FastAPI 后端 + ECharts 单页面前端
- 基础时序预测（ARIMA / OLS fallback）
- 城市竞争力指数（熵权-TOPSIS）
- 城市经济健康指数 CEHI
- SQLite 数据存储

用户新需求：
1. **可视化要灵活**：无论换什么数据都能自动渲染
2. **可视化要高级、可交互**：支持下钻、联动、缩放、动画、地图等
3. **引入数学模型/经济模型**：验证经济发展、判断健康度、生成政策建议
4. **参考学术论文与知名模型**：确保方法论先进、可信

---

## 二、总体方向

采用「**可视化引擎重构 + 数学模型库建设 + 模型结果持久化**」三线并进：

```
数据输入 → 数据画像 → 图表推荐 → 通用可视化配置 → 前端动态渲染
     ↓
模型分析：预测 / 健康度 / 韧性 / TFP / 产业定位 / 空间计量
     ↓
结果持久化 → 对比报告 → 政策建议生成
```

---

## 三、阶段一：通用可视化引擎（最高优先级）

### 3.1 核心设计

建立「数据无关」的可视化协议，让前端只关心如何渲染配置，后端决定渲染什么。

通用图表配置协议（JSON Schema 草案）：

```json
{
  "version": "1.0",
  "chart_type": "line|bar|scatter|radar|heatmap|map|sankey|box|racing_bar|gauge",
  "title": "图表标题",
  "subtitle": "副标题",
  "data_source": {
    "dataset_id": "ds_123456",
    "entity_field": "city",
    "time_field": "year",
    "value_fields": ["gdp", "fiscal_revenue"],
    "category_field": "region"
  },
  "encoding": {
    "x": "year",
    "y": "gdp",
    "color": "city",
    "size": "population",
    "facet": "region"
  },
  "interaction": {
    "zoom": true,
    "brush": true,
    "tooltip": true,
    "legend_toggle": true,
    "drilldown": true,
    "datazoom": true,
    "animation": true
  },
  "style": {
    "theme": "urban_pulse",
    "height": 480,
    "color_palette": ["#0E1F3F", "#B8714A", "#2D6A4F"]
  }
}
```

### 3.2 新增模块

| 文件 | 职责 |
|------|------|
| `backend/viz/schema.py` | 通用图表配置协议 Pydantic 模型 |
| `backend/viz/profiler.py` | 数据集画像：字段类型、时间维度、实体维度、指标数量 |
| `backend/viz/recommender.py` | 根据画像推荐图表类型与编码方式 |
| `backend/viz/renderer.py` | 将协议转换为 ECharts option（后端预渲染） |
| `backend/api/routes/viz.py` | 可视化 API：推荐、渲染、导出配置 |
| `frontend/viz-engine.js` | 前端通用渲染引擎：接收配置 → 初始化 ECharts → 绑定交互 |
| `frontend/charts/*.js` | 各图表类型的渲染插件 |

### 3.3 新增图表类型

1. **动态折线/面积图**：时间序列 + 预测区间阴影
2. **可排序柱状图 + 赛跑图（Racing Bar）**：城市排名随时间变化
3. **雷达图矩阵**：多城市多维对比
4. **热力图 + 聚类树状图**：指标相关性 / 城市相似性
5. **地理散点地图**：城市空间分布，气泡映射指标
6. **桑基图**：产业结构 / 投入产出流向
7. **散点矩阵（Scatter Matrix）**：多指标关系探索
8. **箱线图/小提琴图**：指标分布与异常检测
9. **仪表盘/计分卡**：健康度/竞争力综合得分

### 3.4 前端重构

- 将 `frontend/index.html` 拆分为：
  - `frontend/index.html`：入口与布局
  - `frontend/css/main.css`：主题与组件样式
  - `frontend/js/app.js`：路由与页面状态
  - `frontend/js/viz-engine.js`：通用可视化引擎
  - `frontend/js/charts/*.js`：各图表类型插件
  - `frontend/js/api-client.js`：后端 API 调用封装

---

## 四、阶段二：数学模型库

### 4.1 预测模型增强

| 模型 | 用途 | 优先级 |
|------|------|--------|
| **VAR / 面板 VAR** | 多指标联动分析、政策冲击传导 | 高 |
| **XGBoost / LightGBM** | 多因素 GDP/增长率非线性预测 | 高 |
| **LSTM / Transformer** | 长周期复杂模式预测 | 中 |
| **混频动态因子模型 MF-DFM** | 利用月度高频数据实时预测季度 GDP | 低 |

实现位置：`backend/analytics/models/forecast/`

### 4.2 经济健康度与韧性

| 模型 | 用途 | 优先级 |
|------|------|--------|
| **DPSR + 适应性循环** | 经济韧性四维评估（抵抗/承压/恢复/创新） | 高 |
| **Martin 反事实韧性指数** | 冲击后实际产出 vs 反事实产出 | 中 |
| **PSR-TOPSIS + 障碍度模型** | 识别城市韧性关键短板 | 中 |
| **城市生命体征预警** | 基准-警戒-应急三级阈值 | 中 |

实现位置：`backend/analytics/models/resilience/`

### 4.3 发展质量与效益

| 模型 | 用途 | 优先级 |
|------|------|--------|
| **全要素生产率 TFP（DEA-Malmquist）** | 技术进步与资源配置效率 | 高 |
| **新发展理念综合指数** | 创新、协调、绿色、开放、共享 | 高 |
| **高质量发展六维指数** | 创新活力、产业结构、生态文明、开放互联、增收共促、服务共享 | 中 |

实现位置：`backend/analytics/models/quality/`

### 4.4 产业结构与政策建议

| 模型 | 用途 | 优先级 |
|------|------|--------|
| **区位商 LQ** | 主导产业识别、比较优势 | 高 |
| **赫芬达尔-赫希曼指数 HHI** | 产业集中度 | 中 |
| **EG 指数** | 产业空间集聚程度 | 中 |
| **投入产出分析 / 影响力系数 / 感应度系数** | 产业关联分析 | 中 |
| **空间计量模型 SAR/SEM/SDM** | 空间溢出效应 | 低 |
| **可计算一般均衡 CGE（简化版）** | 政策冲击模拟 | 低 |

实现位置：`backend/analytics/models/industry/`

---

## 五、阶段三：数据库扩展

### 5.1 新增表

```sql
-- 模型运行记录
CREATE TABLE model_runs (
    id TEXT PRIMARY KEY,
    model_type TEXT NOT NULL,      -- forecast / resilience / quality / industry
    model_name TEXT NOT NULL,      -- var / xgboost / dpsr / tfp / lq
    parameters TEXT,               -- JSON
    input_summary TEXT,            -- JSON
    output_summary TEXT,           -- JSON
    status TEXT DEFAULT 'success', -- success / error
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 预测结果
CREATE TABLE forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT REFERENCES model_runs(id),
    entity TEXT NOT NULL,          -- 城市/省份/区域编码
    indicator TEXT NOT NULL,
    year INTEGER NOT NULL,
    forecast_value REAL,
    lower_95 REAL,
    upper_95 REAL,
    method TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 指标得分（健康度/韧性/质量）
CREATE TABLE indicator_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT REFERENCES model_runs(id),
    entity TEXT NOT NULL,
    dimension TEXT,
    indicator TEXT,
    raw_value REAL,
    score REAL,
    weight REAL,
    status TEXT,
    year INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 可视化配置
CREATE TABLE viz_configs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    config_json TEXT NOT NULL,     -- 通用图表配置协议
    dataset_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.2 数据库升级策略

- 当前 SQLite 继续保留，作为默认数据库
- 通过 `init_db()` 自动检测表是否存在并创建新表
- 未来如数据量增大，可迁移至 PostgreSQL（迁移脚本预留接口）

---

## 六、阶段四：智能报告与建议生成

### 6.1 自动诊断报告

- 综合 CEHI、竞争力、韧性、TFP、LQ 等模型结果
- 生成 HTML / PDF 诊断报告
- 对标同类城市，识别优势与短板

### 6.2 政策建议生成

- 基于规则引擎：根据短板指标匹配政策库
- 基于 LLM（可选）：将模型结果输入大模型生成自然语言建议
- 情景分析：模拟不同政策/外部冲击下的经济走势

---

## 七、关键文件规划

```
urban-pulse/
├── backend/
│   ├── analytics/
│   │   └── models/
│   │       ├── forecast/
│   │       │   ├── var_model.py
│   │       │   ├── xgboost_model.py
│   │       │   └── lstm_model.py
│   │       ├── resilience/
│   │       │   ├── dpsr_model.py
│   │       │   └── martin_index.py
│   │       ├── quality/
│   │       │   ├── tfp_model.py
│   │       │   └── new_development_index.py
│   │       └── industry/
│   │           ├── location_quotient.py
│   │           ├── hhi_index.py
│   │           └── io_analysis.py
│   ├── viz/
│   │   ├── __init__.py
│   │   ├── schema.py
│   │   ├── profiler.py
│   │   ├── recommender.py
│   │   └── renderer.py
│   └── api/routes/
│       ├── viz.py
│       ├── models.py
│       └── reports.py
├── frontend/
│   ├── css/
│   │   └── main.css
│   └── js/
│       ├── app.js
│       ├── api-client.js
│       ├── viz-engine.js
│       └── charts/
│           ├── line-chart.js
│           ├── bar-chart.js
│           ├── radar-chart.js
│           ├── heatmap-chart.js
│           ├── map-chart.js
│           ├── sankey-chart.js
│           └── racing-bar-chart.js
└── docs/
    └── ROADMAP_2026_PHASE2.md
```

---

## 八、实施顺序

1. **Week 1**：可视化协议 + 数据画像 + 图表推荐器 + 后端 API
2. **Week 2**：前端可视化引擎 + 拆分 index.html + 6 种新图表
3. **Week 3**：VAR、XGBoost 预测模型 + TFP、区位商
4. **Week 4**：经济韧性模型 + 数据库扩展 + 模型结果持久化
5. **Week 5**：自动报告 + 政策建议生成 + 测试与文档

> 注：以上为大致规划，实际会根据每次迭代的反馈调整。

---

## 九、参考文献与模型来源

- 倪鹏飞弓弦箭模型：城市竞争力「硬竞争力 8 分力 + 软竞争力 5 分力」
- OECD Regional Competitiveness Index (RCI)
- UN-Habitat Global Urban Monitoring Framework (UMF) / 上海指数
- DPSR + 适应性循环：城市经济韧性测度
- Martin 反事实韧性指数
- 全要素生产率 TFP：DEA-Malmquist 方法
- 区位商 LQ、HHI、EG 指数：产业集聚与比较优势
- VAR / PVAR：多变量动态系统
- 新发展理念综合指数：创新、协调、绿色、开放、共享

详见上一轮的完整文献综述。
