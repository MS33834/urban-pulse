# Urban Pulse

> **City economic observatory — 10 Chinese cities, 16 years, infinite extensibility.**
>
> A long-running open-source project that automatically collects, forecasts, and
> publishes city economic data year after year.

[![CI](https://github.com/badhope/urban-pulse/actions/workflows/ci.yml/badge.svg)](https://github.com/badhope/urban-pulse/actions)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Pages](https://img.shields.io/badge/📊_Live_Dashboard-urban--pulse.pages.dev-blue)](https://badhope.github.io/urban-pulse)

---

## What This Is

Urban Pulse is an **open city economic data platform** that:

- **Collects** public data from 10 major Chinese cities (2010–2025, 12+ indicators)
- **Forecasts** GDP, population, fiscal revenue using ensemble time-series models
- **Publishes** everything as a free static dashboard on GitHub Pages
- **Self-updates** yearly via GitHub Actions when new data is released
- **Extends** via a plugin system — add new cities, countries, or indicators

**No servers to maintain. No API keys. Free forever.**

---

## Quick Start

```bash
# Interactive API
pip install -r requirements.txt
uvicorn backend.api.main:app --reload --port 8000
# → http://localhost:8000/dashboard
# → http://localhost:8000/docs

# Static site (no backend needed)
python scripts/build_site.py
cd _site && python -m http.server 8080
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  GitHub Actions (CI + Yearly Cron)                       │
│  ┌────────┐   ┌──────────┐   ┌────────────┐            │
│  │ Test   │──▶│ Build    │──▶│ Deploy to  │            │
│  │ suite  │   │ static   │   │ Pages      │            │
│  └────────┘   │ site     │   └────────────┘            │
│               └──────────┘                              │
├──────────────────────────────────────────────────────────┤
│  GitHub Pages (free hosting, zero cost)                  │
│  ├── index.html  (bilingual ECharts dashboard)          │
│  └── data/       (pre-computed forecasts as JSON)       │
├──────────────────────────────────────────────────────────┤
│  FastAPI (optional, for local dev)                       │
│  ├── 47 REST endpoints (cities, analysis, forecast)     │
│  ├── ARIMA + ETS + Ridge ensemble forecasting           │
│  ├── VaR / GARCH / Monte Carlo risk analysis            │
│  └── Plugin auto-discovery (extensible architecture)    │
├──────────────────────────────────────────────────────────┤
│  Data Pipeline                                           │
│  ├── akshare / NBS collectors                           │
│  ├── Yearly auto-update via Actions cron                │
│  ├── Forecast aging tracker (compare old vs actual)     │
│  └── Git-versioned data (every dataset has history)     │
└──────────────────────────────────────────────────────────┘
```

---

## Extensibility

Drop in a file → it works. No config changes needed.

```python
# backend/data_collection/world_bank.py
class WorldBankCollector(DataCollector):
    def collect(self) -> dict:
        # Pull World Bank API for global cities
        ...
```

**What you can extend:**
- **Data sources**: Add countries, cities, custom indicators
- **Analysis**: New economic models, composite scores
- **Forecasters**: Prophet, LSTM, Transformer — add your own
- **Visualizers**: New chart types, report formats

Full docs: [`docs/PLUGIN_ARCHITECTURE.md`](docs/PLUGIN_ARCHITECTURE.md)

---

## Data Pipeline

| Event | When | What happens |
|-------|------|-------------|
| Every push | CI runs | Tests + builds static site |
| Every Jan 15 | Yearly cron | Pulls latest city data, re-forecasts, deploys |
| Manual | `python scripts/build_site.py` | Rebuilds static site locally |

After 5 years, Urban Pulse becomes a **forecast accuracy archive** — you can see
exactly how well last year's model predicted this year's reality.

Full docs: [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md)

---

## Cities & Indicators

| City | Code | Indicators | Years |
|------|------|-----------|-------|
| Beijing | bj | GDP, Population, Fiscal Rev, … | 2010–2025 |
| Shanghai | sh | … | 2010–2025 |
| Shenzhen | sz | … | 2010–2025 |
| Guangzhou | gz | … | 2010–2025 |
| Chengdu | cd | … | 2010–2025 |
| Hangzhou | hz | … | 2010–2025 |
| Wuhan | wh | … | 2010–2025 |
| Nanjing | nj | … | 2010–2025 |
| Suzhou | su | … | 2010–2025 |
| Xi'an | xa | … | 2010–2025 |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Pydantic v2, Async) |
| Forecasting | statsforecast, statsmodels, arch |
| Data | pandas, numpy, scipy, pyyaml |
| Collection | akshare, requests, beautifulsoup4 |
| Frontend | ECharts 5 (CDN, zero-build) |
| CI/CD | GitHub Actions + Pages |
| Testing | pytest, hypothesis, httpx |
| Container | Docker |

---

## Project Structure

```
urban-pulse/
├── backend/           # FastAPI + core engine + data pipeline
│   ├── api/           # REST API (47 routes)
│   ├── core/          # Forecast engine, risk engine, plugin registry
│   ├── analysis/      # Domain analysis modules
│   ├── data_collection/  # Plugin-based data collectors
│   ├── data_processing/  # Validation, cleaning, transformation
│   └── data/          # Static datasets (YAML + CSV)
├── site/              # Static dashboard source
├── scripts/           # Build tools
├── docs/              # Architecture, pipeline, plugin docs
├── tests/             # Pytest suite
├── .github/workflows/ # CI + yearly cron
├── config/            # Application config
├── Dockerfile
└── pyproject.toml
```

---

## Contributing

- Add a new city's data → `backend/data_collection/`
- Add a new forecast model → `backend/core/` (implement `ForecastingPlugin`)
- Improve the dashboard → `site/index.html`
- Report forecast accuracy → Open an issue with data

---

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).

---

*Built from 10 Chinese cities × 16 years of real public economic data.
Started as a graduation project, built to last forever.*
