# Urban Pulse · 城市脉搏

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)

中国城市经济智能分析平台。基于公开统计数据，提供城市经济画像、多城市对比、产业选址分析、时序预测与竞争力指数。

- 35 座主要城市
- 2016–2024 年多指标历史数据
- ARIMA / ETS / 线性回归集成预测
- 熵权法竞争力指数
- 企业端 / 政府端 / 产业端多维度分析

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
| `GET /api/v1/cities` | 城市列表 |
| `GET /api/v1/cities/{city}` | 城市详情 |
| `GET /api/v1/forecast/gdp/{city}` | GDP 预测 |
| `GET /api/v1/forecast/indicator/{city}` | 任意指标预测 |
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
