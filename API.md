# Urban Pulse — REST API Reference

> Complete reference for the **~50 REST endpoints** exposed by the FastAPI backend.
>
> Base URL: `http://localhost:8000/api/v1` (development) · Interactive: `http://localhost:8000/docs`

---

## Quick Start

```bash
uvicorn backend.api.main:app --reload --port 8000
# → http://localhost:8000/docs   (Swagger UI)
# → http://localhost:8000/redoc  (ReDoc)
```

---

## City Data (`/api/v1/cities/…`)

### List all cities with metadata
```
GET /api/v1/cities
```
Returns 10 supported cities with codes and available indicator count.

### Get economic data for one city
```
GET /api/v1/cities/{city_name}/economy
GET /api/v1/cities/{city_code}/economy
```
Returns 16 years (2010–2025) of GDP, population, fiscal revenue, industry structure, etc.

### Compare multiple cities
```
GET /api/v1/cities/compare?cities=sz,sh,bj&indicators=gdp,population
```

### Get city industry indicators
```
GET /api/v1/cities/{code}/industries
```

### Get city macro covariates
```
GET /api/v1/cities/{code}/macro
```

---

## Analysis (`/api/v1/analysis/…`)

### Enterprise analysis
```
POST /api/v1/analysis/enterprise
```
Analyze a company's fit within a given city's economic profile.  
Request body: `{ "enterprise": "str", "city": "str", "industry": "str" }`

### Government policy analysis
```
POST /api/v1/analysis/government
```
Evaluate policy impact analysis for a city-industry pair.

### Industry completeness
```
POST /api/v1/analysis/industry_completeness
```
Score an industry's development across all 10 cities.  
Response includes completeness scores, gap analysis, and recommendations.

### Multi-city analysis (v3)
```
GET /api/v1/analysis/v3/compare
```
Advanced multi-dimensional comparison with configurable weights.

---

## Forecast (`/api/v1/forecast/…`)

### Time-series forecast
```
GET /api/v1/forecast/{city}/{indicator}?steps=5&interval=True
```
ARIMA + ETS ensemble forecast with confidence bands.

### Monte Carlo simulation
```
POST /api/v1/forecast/monte_carlo
```
N-path simulation for GDP / population / revenue scenarios.  
Request: `{ "city": "sz", "indicator": "gdp", "paths": 5000, "horizon": 5 }`

### Risk analysis
```
POST /api/v1/forecast/risk
```
VaR, CVaR, GARCH(1,1) volatility persistence, downside risk.  
Request: `{ "city": "sz", "indicator": "gdp" }`

### Scenario analysis
```
POST /api/v1/forecast/scenario
```
What-if analysis: optimistic / baseline / pessimistic.  
Request: `{ "city": "sz", "indicator": "gdp", "scenario": "pessimistic" }`

### Backtest
```
POST /api/v1/forecast/backtest
```
Rolling window backtest with 5 evaluation metrics (MAPE, RMSE, MASE, sMAPE, Coverage).

### Diagnostics
```
POST /api/v1/forecast/diagnostics
```
5 residual tests: ADF, KPSS, Ljung-Box, Jarque-Bera, Breusch-Pagan.

### Data provenance
```
GET /api/v1/forecast/data_provenance/{city}/{indicator}
```
Trace a forecast back to its raw data source.

---

## Data Management (`/api/v1/data/…`)

### Upload / integrate new data
```
POST /api/v1/data/upload
```
Accept CSV/YAML files for custom city data (validated against schema).

### List available data sources
```
GET /api/v1/data/sources
```

### Get raw time-series values
```
GET /api/v1/data/timeseries/{city}/{indicator}
```

---

## Response Format

All endpoints return JSON. Errors follow this convention:

```json
{
  "detail": "Human-readable error message",
  "error_code": "CITY_NOT_FOUND"
}
```

Success responses vary by endpoint. Common fields include `status`, `data`, `metadata`.

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 404 | City, indicator, or resource not found |
| 422 | Validation error (check request body) |
| 500 | Internal server error |

---

## Rate Limiting

No built-in rate limit in development. For production, deploy behind a reverse proxy (nginx / Caddy) with rate limiting.
