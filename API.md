# Urban Pulse — REST API Reference

Base URL: `http://localhost:8000/api/v1` · Interactive docs: `http://localhost:8000/docs`

---

## Quick Start

```bash
uvicorn backend.api.main:app --reload --port 8000
# → http://localhost:8000/docs
# → http://localhost:8000/redoc
```

---

## City Data (`/api/v1/cities/…`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/cities/list` | 城市列表 |
| GET | `/cities/{city_name}` | 城市详情 |
| GET | `/cities/{city_name}/historical` | 历史时序数据 |
| GET | `/cities/benchmarks/scores` | 评分基准与权重 |
| GET | `/cities/quality/report` | 数据质量报告 |
| POST | `/cities/aggregate` | 数据聚合分析 |
| POST | `/cities/compare` | 城市对比分析 |
| POST | `/cities/time-series` | 时间序列分析 |
| POST | `/cities/regional` | 区域分析 |
| POST | `/cities/correlation` | 指标相关性分析 |
| GET | `/cities/rankings` | 城市排名 |
| GET | `/cities/dashboard` | 城市仪表盘 |

---

## Analysis (`/api/v1/analysis/…`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/analysis/enterprise` | 企业端综合分析 |
| GET | `/analysis/enterprise/sample` | 企业端示例数据 |
| GET | `/analysis/enterprise/location/{city_name}` | 企业选址分析 |
| POST | `/analysis/enterprise/compare` | 多城市企业选址对比 |
| GET | `/analysis/enterprise/case/semiconductor` | 半导体企业选址案例 |
| GET | `/analysis/config` | 分析默认配置 |
| POST | `/analysis/government` | 政府端产业分析 |

---

## Forecast (`/api/v1/forecast/…`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/forecast/indicators` | 支持的预测指标 |
| GET | `/forecast/provinces` | 支持预测的省份 |
| GET | `/forecast/gdp/{city_name}` | GDP 预测 |
| GET | `/forecast/indicator/{city_name}` | 任意指标预测 |

---

## Competitiveness Index (`/api/v1/index/…`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/index/compute` | 计算竞争力指数 |

---

## Datasets (`/api/v1/datasets/…`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/datasets` | 数据集列表 |
| POST | `/datasets/upload` | 上传 CSV/JSON |
| GET | `/datasets/{id}` | 数据集详情 |
| DELETE | `/datasets/{id}` | 删除数据集 |
| GET | `/datasets/{id}/data` | 原始数据 |
| GET | `/datasets/{id}/pivot` | 透视数据 |

---

## Regions (`/api/v1/regions/…`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/regions` | 区域列表 |
| GET | `/regions/{code}` | 区域详情 |
| POST | `/regions/survey/upload` | 上传调查数据 |

---

## System

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | 根路径信息 |
| GET | `/health` | 健康检查 |
| GET | `/dashboard` | 前端仪表盘页面 |

---

## Response Format

All endpoints return JSON. Errors follow FastAPI's default format:

```json
{
  "detail": "Human-readable error message"
}
```

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 404 | City, indicator, or resource not found |
| 422 | Validation error |
| 500 | Internal server error |
