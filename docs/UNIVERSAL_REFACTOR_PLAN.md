# Urban Pulse 通用化重构计划

> 把城市经济观测站升级为通用经济数据分析平台。
> 任何 CSV/JSON 数据导入后自动分析。

## 总体架构

```
┌─────────────────────────────────────────────┐
│             Frontend (Vue 3 + Vite)          │
│  Pinia状态管理 · Vue Router · Tailwind CSS   │
│  ECharts · 数据驱动的动态渲染                  │
├─────────────────────────────────────────────┤
│              API Layer (FastAPI)              │
│  /api/v1/datasets/*   /api/v1/analysis/*     │
├─────────────────────────────────────────────┤
│           Analysis Engine (通用分析)           │
│  统计摘要 · 相关性 · 聚类 · 熵权法 · 时间序列   │
├─────────────────────────────────────────────┤
│            Data Layer (SQLite)               │
│  datasets · columns · records (宽表)         │
│  自动列检测(entity/time/indicator)           │
│  CSV/JSON 导入 + 种子数据集(10城)            │
└─────────────────────────────────────────────┘
```

## 实施状态

### ✅ 阶段 1 完成 (2026-06-16)

| 模块 | 文件 | 状态 |
|------|------|------|
| SQLite 存储层 | `backend/core/storage/__init__.py` | ✅ |
| 数据集 CRUD | `backend/core/storage/dataset_store.py` | ✅ |
| 宽表记录存取 | `backend/core/storage/record_store.py` | ✅ |
| CSV/JSON 解析 + 自动列检测 | `backend/core/importer.py` | ✅ |
| 种子数据导入 | `backend/seed_data.py` | ✅ 452条记录, 10城 × 19指标 |
| 数据集 API | `backend/api/routes/datasets.py` | ✅ 上传/列表/详情/删除/分页查询/透视表 |
| 路由注册 | `backend/api/main.py` | ✅ lifespan 启动时自动初始化 |

### 🔲 阶段 2 — 通用分析引擎 (待开始)

- 统计摘要 / 相关性矩阵 / K-means 聚类
- 通用熵权法排名 / 时间序列预测
- 通用分析 API

### 🔲 阶段 3 — Vue 前端 (待开始)

### 🔲 阶段 4 — 整合与混入 (待开始)

## API 设计

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/v1/datasets/upload` | 上传 CSV/JSON (auto-detect) |
| GET | `/api/v1/datasets` | 数据集列表 |
| GET | `/api/v1/datasets/{id}` | 数据集详情(含列角色/实体/指标) |
| PUT | `/api/v1/datasets/{id}` | 更新元信息 |
| DELETE | `/api/v1/datasets/{id}` | 删除数据集 |
| GET | `/api/v1/datasets/{id}/data` | 原始数据(分页+筛选) |
| GET | `/api/v1/datasets/{id}/pivot` | 透视数据 |
| GET | `/api/v1/datasets/{id}/entities` | 实体列表 |
| GET | `/api/v1/datasets/{id}/indicators` | 指标列表 |
