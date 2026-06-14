# Data Pipeline — Year-Round Automated City Economic Data

> **How Urban Pulse automatically ingests, validates, forecasts, and publishes
> city economic data — year after year, with no human intervention.**

---

## The Problem

Chinese city economic data is:
- Published **yearly** (usually Jan–April for the previous year)
- Spread across **30+ city bureau websites**
- In **different formats** per city
- Not available as a unified API (except via akshare)

Every year, the same data is published again. Most projects either:
1. Manually update data once and abandon the project
2. Rely on a third-party API that may disappear
3. Never get updated after the initial release

---

## The Solution: Automated Yearly Pipeline

```
┌────────────────────────────────────────────────────────────────┐
│  GitHub Actions (cron: yearly on Jan 15)                       │
│                                                                │
│  ┌──────────────┐   ┌────────────┐   ┌────────────────────┐   │
│  │ 1. Collect   │──▶│ 2. Validate│──▶│ 3. Generate        │   │
│  │   akshare    │   │  auto-fix  │   │  forecasts + stats │   │
│  │   NBS API    │   │  flag gaps │   │  all cities/all    │   │
│  │   web scrape │   │            │   │  indicators        │   │
│  └──────────────┘   └────────────┘   └─────────┬──────────┘   │
│                                                 │              │
│  ┌──────────────────┐   ┌──────────────┐       │              │
│  │ 6. Commit data   │◀──│ 5. Build     │◀──────┘              │
│  │    to git repo   │   │    static    │                      │
│  │    (versioned)   │   │    site      │                      │
│  └────────┬─────────┘   └──────────────┘                      │
│           │                                                    │
│           ▼                                                    │
│    PR created with new data                                    │
│    → reviewed → merged → Pages auto-deploys                   │
└────────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Pipeline

### Step 1: Data Collection (Jan 15 each year)

The cron triggers `backend/data_collection/` which runs all registered collectors:

```bash
# Manual trigger:
python -m backend.data_collection.run_all --year 2025
```

**What gets collected:**
| Source | Data | Update cadence |
|--------|------|----------------|
| akshare | GDP, population, fiscal data | Yearly (Jan) |
| City statistical bulletins | Industry structure, R&D | Yearly (Jan–Apr) |
| NBS API | National macro covariates | Quarterly |

### Step 2: Validation & Cleaning

```yaml
# Example: validation report
date: 2026-01-15
new_data_year: 2025
results:
  cities_validated: 10/10
  indicators_updated: 12/12
  gaps_found: 2
    - beijing: industry_high_tech_ratio → estimated from NBS national data
    - xian: rd_subsidy → marked as missing, used interpolation
  breaking_changes: 0
```

The validator:
- Checks for missing values
- Flags outliers (>3σ from historical trend)
- Auto-fills via linear interpolation for small gaps
- Creates a human-readable report

### Step 3: Forecast Generation

All 10 cities × 12 indicators × 5-year horizon forecasts are regenerated:
- ARIMA + ETS + Ridge ensemble
- Residual diagnostics (5 tests)
- Confidence intervals
- All exported to JSON for the static site

### Step 4: Forecast Archive

Previous forecasts are compared to actual data:

```json
{
  "city": "shenzhen",
  "indicator": "gdp",
  "forecast_made": "2025-01-15",
  "predicted_2025": 38500,
  "actual_2025": 37800,
  "error_pct": -1.82,
  "inside_95ci": true
}
```

This creates a **forecast accuracy track record** — the longer the project runs,
the more valuable this dataset becomes.

### Step 5: Static Site Build

`python scripts/build_site.py` generates the static GitHub Pages site with
all pre-computed data.

### Step 6: Commit & PR

A GitHub Action auto-commits the new data and opens a PR:

```
[bot] 📊 Urban Pulse data update — 2025 data added
  - 10 cities × 12 indicators updated
  - 2 gaps auto-filled, 0 breaking changes
  - Forecast archive updated with new accuracy data
  - Site rebuilt and deployed
```

The user (or any maintainer) reviews and merges → Pages auto-deploys.

---

## Local Data Update

```bash
# Pull latest data
python -c "from backend.data_collection.nbs_collector import nbs_collector; nbs_collector.collect_all()"

# Validate
python -c "from backend.data_processing.validator import validate_city_data; print(validate_city_data())"

# Regenerate site
python scripts/build_site.py

# Serve locally
cd _site && python -m http.server 8080
```

---

## Data Versioning Strategy

| What | How | Why |
|------|-----|-----|
| Raw data | YAML + CSV in `backend/data/` | Human-readable, diff-able |
| Processed | Git-tracked JSON in `_site/data/` | Static site loads directly |
| Forecasts | Timestamped JSON in `data/forecasts/` | Track accuracy over time |
| Reports | Markdown in `data/reports/` | Readable on GitHub |

**Git LFS** is recommended if the dataset grows beyond 50MB.

---

## Adding a New Data Source

1. Create collector: `backend/data_collection/my_source.py`
2. Implement `DataCollector` interface (see `PLUGIN_ARCHITECTURE.md`)
3. Register in `backend/data_collection/__init__.py`
4. Run `python scripts/build_site.py` — it auto-discovers and uses the new source

---

## Pipeline Reliability

| Risk | Mitigation |
|------|-----------|
| API changes (akshare) | Version-pin akshare; cron catches failures |
| NBS site down | Retry 3x with exponential backoff |
| Missing data point | Linear interpolation + flagging |
| Breaking schema change | Validation fails CI, PR not merged |
| Collector fails completely | Last year's data persists, no update |
