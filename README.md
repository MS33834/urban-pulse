# Urban Pulse · 城市脉搏

[![Python](https://img.shields.io/badge/Python-3.11--3.13-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)

中国城市经济智能分析平台。基于公开统计数据，提供城市经济画像、多城市对比、产业选址分析、时序预测、竞争力指数与城市经济发展健康水平诊断。

- 35 座主要城市
- 2016–2024 年多指标历史数据
- ARIMA / ETS / 线性回归集成预测
- 熵权法竞争力指数
- 城市经济发展健康水平指数（CEHI）：6 大维度 30 项指标，支持健康诊断、短板归因、城市对标与改进建议
- 企业端 / 政府端 / 产业端多维度分析

---

## 产品定位

### 愿景
让每个关注中国城市经济发展的人，都能用数据读懂城市脉搏。

### 使命
基于公开、透明、可审计的统计数据，构建中国城市经济的开箱即用分析基础设施，为研究者、决策者、开发者和公众提供可信的城市经济洞察。

### 产品定位
Urban Pulse（城市脉搏）不是通用 BI 或低代码可视化工具，而是**专注中国城市经济的垂直智能分析平台**。它将宏观经济、城市指标、产业动态和时序预测能力封装成可访问的 REST API 与零构建的可视化界面，支持从“数据查询”到“决策建议”的完整链路。

### 目标用户

| 角色 | 典型场景 |
|------|---------|
| 经济研究人员 / 智库 | 城市经济画像、长期趋势研究、论文数据支撑 |
| 政府规划 / 招商 / 统计部门 | 区域对标、产业规划、健康诊断 |
| 企业战略 / 投资 / 选址团队 | 城市进入评估、成本与政策环境比较 |
| 金融 / 地产 / 咨询分析师 | 宏观预测、行业景气度、风险评估 |
| 开发者 / 数据工程师 | 嵌入业务系统、二次开发、插件扩展 |
| 公众与媒体 | 直观了解城市经济变化 |

### 核心价值

- **开箱即用**：预置 35 座主要城市、16 年指标数据，无需自建数据管道即可开始分析。
- **可解释预测**：集成 ARIMA + ETS + 线性回归，带残差诊断、置信区间与滚动回测，拒绝“黑盒”。
- **多维健康诊断**：CEHI 城市经济发展健康水平指数覆盖 6 大维度 30 项指标，支持短板归因与改进建议。
- **开放可扩展**：插件化采集器、CSV/Excel 调查数据上传、开放 REST API，支持用户补充私有数据。
- **可信透明**：数据来源公开标注，指标定义可审计，预测局限性与不确定性明确呈现。

### 差异化优势

- **中国城市经济专属**：指标、维度、模型都围绕中国城市经济设计，而非套用通用时序分析模板。
- **投资决策级预测流水线**：不是简单画一条趋势线，而是包含平稳性检验、模型选择、结构突变检测、滚动 CV 与情景分析的完整流程。
- **政企产三端分析**：企业选址、政府产业评估、产业预测三位一体，覆盖不同决策视角。
- **极简部署**：单进程 FastAPI + 零构建前端，一条 `docker compose up` 即可运行。
- **开源可审计**：GPL-3.0 协议，数据、模型、代码全部可审查。

### 使用场景

- **城市经济体检**：通过 CEHI 诊断城市强项、短板与改进路径。
- **城市竞争力对标**：多城市、多指标横向对比，找出差距与追赶方向。
- **产业选址与投资评估**：综合成本、供应链、政策环境给出选址评分。
- **宏观经济与产业预测**：GDP、人口、财政收入等指标的未来 5 年预测及情景分析。
- **政策效果模拟**：调整政策、技术、需求、供应链等因子，观察对产业或城市指标的潜在影响。

### 产品理念

- **数据透明**：来源可溯、假设可见、局限明说。
- **模型可解释**：每个结果都附带方法论、诊断指标与不确定性。
- **部署极简**：降低使用门槛，让分析能力快速落地。
- **渐进增强**：核心功能不依赖可选重型库，高级能力通过 extras 按需加载。

### 数据理念

- 以国家统计局、各省市统计公报与年鉴等公开数据为基石。
- 商业成本、政策环境等模型估算值明确标注，不伪装成官方数据。
- 数据缺口通过透明的方法论填补，并在输出中提示置信度。
- 欢迎用户上传自有调查数据，与公开数据共同构建更完整的区域画像。

---

## 快速开始

```bash
# Docker
docker compose up
# → http://localhost:8000/dashboard
# → http://localhost:8000/docs

# 本地 Python
pip install -r requirements.txt
uvicorn backend.api.main:app --reload
```

> **环境要求**：推荐使用 Python 3.11–3.13。Python 3.14 目前尚未完全支持，因为 `statsforecast`、`pmdarima` 等可选依赖在 3.14 上缺少预编译 wheel，会导致预测引擎回退到 `statsmodels`。

## 功能

- **城市经济数据** — 35 城 GDP、人口、财政收入、研发强度等指标与历史时序
- **时间序列预测** — AutoARIMA + ETS + 线性回归集成，带置信区间
- **城市对比** — 多城市、多指标横向对比
- **企业选址分析** — 成本、供应链、政策环境评分
- **政府端分析** — 财政杠杆、产业带动、产业链完整性评估
- **产业预测** — 基准时序 + 政策/技术/需求/供应链/社会情绪多因素调整
- **开放数据接入** — CSV/Excel 调查数据上传与区域挂载
- **竞争力指数** — 熵权法多维度评分与排名

## 技术栈

| 层 | 工具 |
|--|--|
| 后端 | FastAPI (Python 3.11+) |
| 预测 | statsforecast / statsmodels / arch / scikit-learn |
| 数据科学 | pandas / numpy / scipy |
| 前端 | ECharts 5 单页应用 |
| 容器 | Docker / docker compose |
| CI | GitHub Actions |

## 项目结构

```
urban-pulse/
├── backend/
│   ├── api/              # REST API 路由
│   ├── core/             # 预测引擎、风险引擎、聚合逻辑
│   ├── analysis/         # 企业、政府、经济模型分析
│   ├── analytics/        # 竞争力指数引擎
│   ├── data/             # 城市数据快照
│   ├── data_collection/  # 公开数据采集器
│   ├── data_processing/  # 清洗、转换、校验
│   ├── industries/       # 产业实体与预测
│   └── regions/          # 多级区域注册表
├── frontend/             # 仪表盘单页应用
├── site/                 # 静态展示站点
├── docs/                 # 架构与数据管道文档
├── config/               # 应用配置
├── tests/                # 测试套件
├── data/cities/          # 城市数据 (YAML)
├── scripts/              # 构建与数据生成脚本
├── Dockerfile
└── pyproject.toml
```

## 主要 API

| 端点 | 说明 |
|------|------|
| `GET /api/v1/cities/list` | 城市列表 |
| `GET /api/v1/cities/{city}` | 城市详情 |
| `GET /api/v1/forecast/gdp/{city}` | GDP 预测 |
| `GET /api/v1/forecast/indicator/{city}` | 任意指标预测 |
| `GET /api/v1/health/indicators` | CEHI 指标体系 |
| `GET /api/v1/health/demo` | CEHI 示例结果 |
| `POST /api/v1/health/calculate` | 城市 CEHI 健康诊断 |
| `POST /api/v1/health/benchmark` | 城市 CEHI 对标分析 |
| `POST /api/v1/analysis/enterprise` | 企业选址分析 |
| `POST /api/v1/analysis/government` | 政府端产业分析 |
| `POST /api/v1/industries` | 注册产业 |
| `POST /api/v1/industries/{region}/{industry}/forecast` | 产业预测 |
| `POST /api/v1/regions/survey/upload` | 上传调查数据 |
| `POST /api/v1/index/compute` | 竞争力指数计算 |

完整 API 文档在运行后访问 `/docs`。

## 数据说明

城市数据来自国家统计局、各省市统计公报与统计年鉴。商业成本、政策环境等字段为模型估算值，生产环境建议接入官方或调研数据源。

## 静态站点

```bash
python scripts/build_site.py
```

生成 `_site/` 目录，可部署到任意静态页面托管服务。

## License

GPL-3.0-or-later
