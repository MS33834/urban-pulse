# Urban Pulse · 城市脉搏

[![CI](https://github.com/badhope/urban-pulse/actions/workflows/ci.yml/badge.svg)](https://github.com/badhope/urban-pulse/actions)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)

**10 Chinese cities · 16 years of data · 5-year forecasts · Real public data**

An open-source urban economic observatory. Auto-collects public data, runs forecasts, generates reports. Updates annually on January 15th — for as long as the internet exists.

Started as a graduation project. Built to last forever.

---

## Quick Start

```bash
# Docker (recommended)
docker compose up
# → http://localhost:8000/dashboard
# → http://localhost:8000/docs

# Native Python
pip install -r requirements.txt
uvicorn backend.api.main:app --reload
```

## Features

- **Competitiveness Index** — Entropy-weighted scoring across 9 dimensions (capital, technology, institutions, etc.) with radar charts and heatmaps
- **Time-Series Forecasting** — ARIMA / GARCH / Theta forecasts with confidence intervals
- **City Comparison** — Side-by-side analysis across 19+ economic indicators
- **Enterprise Analysis** — Cost, supply chain, and policy environment scoring
- **Dynamic Dashboard** — Full ECharts SPA, zero build step

## Architecture

```
Data Collection ──→ Forecast Engine ──→ FastAPI ──→ ECharts Dashboard
                         │
                    GitHub Actions
                  (annual auto-update)
```

## 10 Cities

Beijing · Shanghai · Shenzhen · Guangzhou · Chengdu · Wuhan · Hangzhou · Nanjing · Suzhou · Xi'an

Core indicators: GDP / GDP growth / Population / Fiscal revenue / R&D intensity

City data stored in `data/cities/` as JSON files, organized by year.

## Tech Stack

| Layer | Tools |
|-------|-------|
| Backend | FastAPI (Python 3.11+) |
| Forecasting | statsforecast / statsmodels / arch |
| Data Science | pandas / numpy / scikit-learn |
| Frontend | ECharts 5 (vanilla JS SPA, zero build) |
| CI/CD | GitHub Actions + Pages |
| Container | Docker / docker compose |

## Project Structure

```
urban-pulse/
├── backend/
│   ├── api/              # REST API routes
│   ├── core/             # Forecast engine, risk engine, multi-city
│   ├── analysis/         # Enterprise, government, economic analysis
│   ├── analytics/        # Competitiveness index engine
│   ├── data/             # Hardcoded city data snapshots
│   ├── data_collection/  # Public data scrapers
│   └── data_processing/  # Cleaner, transformer, validator
├── frontend/             # ECharts dashboard (standalone SPA)
├── site/                 # GitHub Pages showcase page
├── docs/                 # Architecture, data pipeline, plugin docs
├── config/               # Application config, per-city/industry profiles
├── tests/                # 116+ tests
├── data/cities/          # City data (JSON)
├── scripts/              # Build & utility scripts
├── Dockerfile
└── pyproject.toml
```

## API

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/index/compute` | Compute competitiveness index (entropy weighting) |
| `GET /api/v1/index/rankings` | Get rankings by dimension |
| `POST /api/v1/index/report/{city}` | City competitiveness report |
| `POST /api/v1/cities/time-series` | Multi-city time-series comparison |
| `POST /api/v1/forecast/gdp/{city}` | GDP forecast with confidence intervals |

Full API docs at `/docs` when running.

## Roadmap

- [ ] Expand to 15-20 cities
- [ ] Auto-scrapers for education, environment, infrastructure data
- [ ] Multi-city VAR forecasting (economic ripple effects)
- [ ] Forecast accuracy tracking vs actuals
- [ ] Dataset snapshots for reproducible research

## License

GPL-3.0-or-later

---

<details>
<summary><b>🇨🇳 中文版说明</b></summary>

# Urban Pulse · 城市脉搏

**10 座中国城市 · 16 年数据 · 5 年预测 · 真实公开数据**

一个开源的城市经济观测站。自动采集公开数据、跑预测、出报表。每年 1 月 15 号自动更新一次，重新跑一遍全量预测。长期跑着，年复一年。

### 快速开始

```bash
docker compose up
# → http://localhost:8000/dashboard
# → http://localhost:8000/docs
```

### 竞争力指数

基于熵权法的城市竞争力评价，覆盖成本力、资本力、产业链力、制度力、科技力、规模力、聚集力、区位力、生命健康力 9 个维度，28 个二级指标。

### API 端点

| 端点 | 说明 |
|------|------|
| `POST /api/v1/index/compute` | 计算竞争力指数（熵权法） |
| `GET /api/v1/index/rankings` | 按维度查看排名 |
| `POST /api/v1/index/report/{city}` | 单城市分析报告 |
| `POST /api/v1/cities/time-series` | 多城市时间序列对比 |
| `POST /api/v1/forecast/gdp/{city}` | GDP 预测（含置信区间） |

### 技术栈

FastAPI + ECharts 5 + Docker + GitHub Actions

### License

GPL-3.0-or-later

</details>

---

*Built by [@badhope](https://github.com/badhope). Started as a graduation project, built to last forever.*
