# Urban Pulse · 城市脉搏

毕业设计。但毕业后不想扔在那吃灰。

[![CI](https://github.com/badhope/urban-pulse/actions/workflows/ci.yml/badge.svg)](https://github.com/badhope/urban-pulse/actions)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)

---

**10 座中国城市 · 16 年数据 · 5 年预测**

一个长期维护的城市经济观测站。自动采集公开数据、跑预测、出报表。每年 1 月 15 号自动更新一次，重新跑一遍全量预测。长期跑着，年复一年。

---

## 怎么用

```bash
# Docker（推荐）
docker compose up
# → http://localhost:8000/dashboard
# → http://localhost:8000/docs

# Python 原生
pip install -r requirements.txt
uvicorn backend.api.main:app --reload
```

## 架构

```
数据采集 ──→ 预测引擎 ──→ FastAPI ──→ ECharts 仪表盘
                    ↓
              GitHub Actions
              （每年自动更新）
```

## 十个城市

北京 · 上海 · 深圳 · 广州 · 成都 · 武汉 · 杭州 · 南京 · 苏州 · 西安

五个指标：GDP / GDP 增速 / 常住人口 / 财政收入 / R&D 投入强度

数据放在 `data/cities/` 里，每个城市一个 JSON 文件，按年存。

## 技术栈

| 层 | 用的啥 |
|---|--------|
| 后端 | FastAPI |
| 预测 | statsforecast / statsmodels / arch |
| 数据处理 | pandas / numpy |
| 前端 | ECharts 5（单页 HTML，零构建） |
| CI/CD | GitHub Actions + Pages |
| 容器 | Docker |

## 项目结构

```
urban-pulse/
├── backend/           # FastAPI + 预测引擎
│   ├── api/           # REST API 路由
│   ├── core/          # 预测引擎、风险引擎
│   ├── analysis/      # 分析模块
│   └── data_collection/  # 数据采集
├── frontend/          # ECharts 仪表盘（本地运行）
├── site/              # GitHub Pages 展示页
├── docs/              # 文档
├── tests/             # 116 个测试
├── data/cities/       # 城市数据（JSON）
├── config/            # 应用配置
├── Dockerfile
└── pyproject.toml
```

## TODO

- [ ] Jupyter Notebooks —— 答辩用
- [ ] Dockerfile 完整验证
- [ ] 截图放进 README
- [ ] 加到 15-20 个城市
- [ ] 前几年预测 vs 实际数据的准确率追踪

## License

GPL-3.0-or-later

---

*Built by [@badhope](https://github.com/badhope). Started as a graduation project, built to last forever.*
