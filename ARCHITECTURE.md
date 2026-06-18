# Architecture

> **Version**: 1.0.0 (2026-06-14) · **Stack**: Python 3.11+ / FastAPI / Pydantic v2 / ECharts 5

This document describes the high-level architecture of **Urban Pulse** — a
lightweight city economic intelligence platform focusing on time-series
forecasting, multi-city comparison, and scenario analysis.

---

## 1 · High-level Diagram

```
┌──────────────────────────────────────────────────────────────┐
│  FastAPI (single process, uvicorn, port 8000)                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Layer (backend/api/)                            │   │
│  │  ┌────────┐ ┌──────────┐ ┌───────────┐ ┌─────────┐  │   │
│  │  │ cities │ │ analysis │ │ forecast  │ │ data    │  │   │
│  │  │ routes │ │ routes   │ │ routes    │ │ routes  │  │   │
│  │  └────────┘ └──────────┘ └───────────┘ └─────────┘  │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │  Core Engine (backend/core/)                         │   │
│  │  ┌────────────────┐ ┌─────────────┐ ┌────────────┐  │   │
│  │  │ forecast_engine │ │ risk_engine │ │engine_stack│  │   │
│  │  │ ARIMA+ETS+Ridge│ │ VaR/GARCH   │ │fallback    │  │   │
│  │  └────────────────┘ └─────────────┘ └────────────┘  │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │   │
│  │  │ multi_city   │ │ data_manager │ │ validators │  │   │
│  │  └──────────────┘ └──────────────┘ └────────────┘  │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │  Data Layer                                          │   │
│  │  ┌────────────────┐ ┌─────────────────────────────┐  │   │
│  │  │ data_collection│ │ data_processing             │  │   │
│  │  │ akshare / NBS  │ │ cleaner / validator /merge  │  │   │
│  │  └────────────────┘ └─────────────────────────────┘  │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ backend/data/  (YAML + CSV — static dataset)   │  │   │
│  │  │ 10 cities × 12 indicators × 16 years           │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Frontend (frontend/)                                │   │
│  │  index.html — ECharts 5 Dashboard (zero-build SPA)  │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## 2 · Key Design Decisions

### 2.1 Single Process, No Database

The platform loads pre-compiled static city data (YAML + CSV) into memory at
startup. No PostgreSQL / SQLite dependency. This makes deployment trivial
(`pip install && uvicorn run`).

**Trade-off**: No write persistence across restarts unless the user pushes new
data to the data files.

### 2.2 Ensemble Forecasting

Three-model ensemble (AutoARIMA + ETS + Ridge) with AIC-weighted averaging.
Statsforecast's `AutoARIMA` is primary; statsmodels `SARIMAX` serves as
fallback for edge cases.

**Residual diagnostics**: 5 tests (ADF, KPSS, Ljung-Box, Jarque-Bera,
Breusch-Pagan) run on every forecast to validate model quality.

### 2.3 Graceful Degradation

The `engine_stack` module implements a fallback chain:
1. Try statsforecast AutoARIMA (fast, C-optimized)
2. Fall back to statsmodels SARIMAX (compatible, slower)
3. If that also fails, return informative error with diagnostic hints

### 2.4 Zero-Build Frontend

Single `index.html` with ECharts 5 loaded from CDN. No npm, no bundler, no
build step. All chart logic is vanilla JavaScript with async fetch to the
backed API.

---

## 3 · Module Map

```
urban-pulse/
├── backend/
│   ├── api/                # FastAPI application
│   │   ├── main.py         # App factory, middleware, route registration
│   │   └── routes/         # Endpoint handlers by domain
│   │       ├── cities.py
│   │       ├── analysis.py
│   │       ├── forecast.py
│   │       ├── data.py
│   │       └── static.py   # Static file serving
│   ├── core/               # Business logic
│   │   ├── forecast_engine.py   # ARIMA+ETS ensemble
│   │   ├── risk_engine.py       # VaR / GARCH
│   │   ├── engine_stack.py      # Fallback chain
│   │   ├── multi_city.py        # City registry + data loader
│   │   ├── data_manager.py      # Data ingestion / validation
│   │   └── validators.py        # Input validation
│   ├── analysis/           # Domain-specific analysis
│   ├── data/               # Static dataset (YAML + CSV)
│   ├── data_collection/    # Data collectors (akshare, NBS)
│   ├── data_processing/    # Data cleaning / transformation
│   ├── models/             # Pydantic schemas
│   └── utils/              # Helpers (logging, IO)
├── config/
│   ├── settings.py         # App settings (Pydantic Settings)
│   └── loader.py           # Config loading
├── frontend/
│   └── index.html          # ECharts dashboard
├── docs/
│   ├── METHODOLOGY.md      # Forecasting methodology
│   ├── API.md              # API reference
│   └── ARCHITECTURE.md     # This file
├── tests/                  # Pytest suite
├── notebooks/              # Jupyter notebooks
├── data/                   # Root-level static data
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

---

## 4 · Data Flow

```
┌──────────┐   ┌────────────┐   ┌───────────┐   ┌──────────┐
│ akshare  │──▶│ data/      │──▶│ multi_    │──▶│ API      │
│ NBS      │   │ (YAML/CSV) │   │ city.py   │   │ routes   │
└──────────┘   └────────────┘   │ (registry)│   └────┬─────┘
                                └─────┬─────┘        │
                                      │               ▼
                                      │         ┌──────────┐
                                      └────────▶│ forecast │
                                                │ engine   │
                                                └──────────┘
```

1. **Collect**: `data_collection/` pulls from akshare / NBS APIs
2. **Store**: Processed data saved as clean YAML + CSV in `backend/data/`
3. **Load**: `multi_city.py` registers all cities at app startup
4. **Serve**: API routes use registered city data for forecasts and analysis
5. **Render**: `index.html` fetches from API and renders ECharts

---

## 5 · Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Framework | FastAPI (Pydantic v2) | REST API with auto-docs |
| Server | uvicorn | ASGI server |
| Forecasting | statsforecast, statsmodels, arch | Time-series models |
| Data | pandas, numpy, scipy, pyyaml | Data manipulation |
| Collection | akshare, requests, beautifulsoup4 | Web data |
| Frontend | ECharts 5 (CDN) | Charts & dashboard |
| Testing | pytest, hypothesis, httpx | Quality assurance |
| Container | Docker | Deployment |

---

## 6 · Future Considerations

- **Database**: Add SQLite / PostgreSQL when write-back is needed
- **Async forecasting**: Offload long forecasts to background tasks (Celery / ARQ)
- **Caching**: In-memory LRU for repeated forecast queries
- **Auth**: JWT middleware for multi-user deployment
- **CI/CD**: GitHub Actions for test + deploy
