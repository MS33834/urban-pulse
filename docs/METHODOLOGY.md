# Forecasting Methodology — Investment-Grade Time-Series Prediction

> **Platform**: Urban Pulse — City Economic Intelligence
> **Version**: 1.0 (Investment-Grade)
> **Last updated**: 2026-06-04
> **Data scope**: 10 cities × 12 indicators × 16 years (2010–2025) + 4 macro covariates

---

## 1 · Data Sources & Limitations

### 1.1 City Indicators (10 cities × 12 indicators × 16 years = 1920 data points)

| Dimension | Details |
|-----------|---------|
| **Cities** | Shenzhen / Shanghai / Beijing / Guangzhou / Chengdu / Hangzhou / Wuhan / Nanjing / Suzhou / Xi'an |
| **Indicators** | gdp, population, fiscal_revenue, supplier_count, land_price (5 absolute)<br>rd_intensity, industry_high_tech_ratio, gdp_growth, local_support_rate, policy_coverage, rd_subsidy, tax_reduction (7 ratios) |
| **Years** | 2010–2025 (16 years) |
| **Sources** | City bureau of statistics annual bulletins (URLs in `backend/data/historical_extended.py:SOURCE_URLS`) |
| **Completeness** | 100% — every cell has real or publicly available data |

### 1.2 Macro Covariates (4 series × 16 years)

| Covariate | Source | Notes |
|-----------|--------|-------|
| National GDP | National Bureau of Statistics | Annual, base year adjusted |
| M2 Money Supply | People's Bank of China | Year-end balance |
| Real Estate Climate Index | NBS | Index value |
| Consumer Confidence Index | NBS | Index value |

### 1.3 Known Limitations

- **16 data points per indicator** is short for ARIMA (typically need ≥30 for
  pure seasonal models). Ensemble methods mitigate but cannot eliminate this.
- **No 2026 data** at the time of writing. Forecasts beyond 2025 have widening
  confidence intervals.
- **City-level data revisions**: Chinese cities occasionally revise historical
  figures; data may diverge from current NBS releases by 1–2%.

---

## 2 · Model Architecture

### 2.1 Three-Model Ensemble

```
┌─────────────────────────────────────────────────────────┐
│                    Ensemble Forecast                      │
├─────────────────────────────────────────────────────────┤
│   w₁ × ARIMA  +  w₂ × ETS  +  w₃ × Ridge Regression    │
│   ───────────────────────────────────────────────       │
│   where wᵢ ∝ exp(-½ × AICᵢ)                             │
│   (AIC-weighted average)                                │
└─────────────────────────────────────────────────────────┘
```

#### ARIMA (AutoRegressive Integrated Moving Average)

Primary implementation via **statsforecast's `AutoARIMA`** — a C-optimized
engine that automatically selects (p,d,q) order using AIC/AICc.

**Fallback**: If statsforecast fails (e.g., missing optional dependency), the
system falls back to **statsmodels `SARIMAX`** with grid search over
p ∈ [0,3], d ∈ [0,2], q ∈ [0,3].

**Stationarity check**: ADF test before differencing; KPSS test for
confirmation.

#### ETS (Error Trend Seasonal)

Implemented via statsmodels' `ExponentialSmoothing`. Models additive or
multiplicative trend with no seasonal component (annual data).

#### Ridge Regression

Scikit-learn RidgeCV with 5-fold cross-validation. Uses lagged values
(t-1, t-2, t-3) and macro covariates as features. Acts as a regularized
linear baseline.

### 2.2 Model Selection Logic

```python
if data_length >= 8:
    try:
        model = AutoARIMA(season_length=1)
    except (ImportError, Exception):
        model = SARIMAX(...)  # fallback
else:
    model = SimpleExpSmoothing(...)  # too short for ARIMA
```

The threshold (≥8 years) ensures at least minimal information for
auto-regression. Below 8 points, the system refuses to forecast and returns
an error message.

### 2.3 Confidence Intervals

Generated via: `forecast ± z × σᵣₑₛᵢₙₒₐₗ × √(t)`

Where `z` comes from the normal distribution (1.96 for 95% CI),
`σᵣₑₛᵢₙₒₐₗ` is the residual standard deviation, and `√(t)` models
increasing uncertainty with horizon.

---

## 3 · Residual Diagnostics

Every forecast produces a diagnostic report:

| Test | What it checks | Target |
|------|---------------|--------|
| **ADF** | Stationarity (unit root) | p < 0.05 |
| **KPSS** | Trend stationarity | p > 0.05 |
| **Ljung-Box** | Autocorrelation in residuals | p > 0.05 |
| **Jarque-Bera** | Normality of residuals | p > 0.05 |
| **Breusch-Pagan** | Homoscedasticity | p > 0.05 |

**Interpretation**:
- 5/5 passed → forecast is reliable
- 3-4/5 passed → usable with caution
- <3 passed → forecast may be unreliable; inspect stationarity

---

## 4 · Backtest Metrics

Rolling window backtest uses 5-fold expanding window:

| Metric | Formula | Ideal |
|--------|---------|-------|
| **MAPE** | (1/n)Σ|y−ŷ|/|y| | < 10% |
| **RMSE** | √((1/n)Σ(y−ŷ)²) | Smaller |
| **MASE** | MAE / MAE_naive | < 1.0 |
| **sMAPE** | (1/n)Σ2|y−ŷ|/(|y|+|ŷ|) | < 10% |
| **Coverage** | % of actuals within 95% CI | ~95% |

---

## 5 · Risk & Scenario Analysis

### 5.1 Value at Risk (VaR) & CVaR

- **Method**: Historical simulation + parametric normal
- **Confidence levels**: 95%, 97.5%, 99%
- **CVaR**: Expected shortfall beyond VaR threshold

### 5.2 GARCH(1,1) Volatility Modeling

- `σ²(t) = ω + α·ε²(t-1) + β·σ²(t-1)`
- Scaled to forecast horizon via root-time scaling
- Volatility persistence = α + β (close to 1 = very persistent)

### 5.3 Monte Carlo Simulation

- **N paths**: 5,000 (default)
- **Distribution**: Student's t with estimated degrees of freedom
- **Output**: Path means, percentiles (5/25/50/75/95), fan chart data

### 5.4 Scenario Analysis

Three scenarios overlay the baseline forecast:

| Scenario | Macro Multiplier | Volatility Factor |
|----------|-----------------|-------------------|
| Optimistic | 1.15× | 0.7× (lower vol) |
| Baseline | 1.0× | 1.0× |
| Pessimistic | 0.85× | 1.5× (higher vol) |

---

## 6 · References

1. Hyndman, R.J. & Athanasopoulos, G. (2021) *Forecasting: Principles and Practice*, 3rd ed. OTexts.
2. Newey, W.K. & West, K.D. (1987) A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica* 55(3):703–708.
3. Bollerslev, T. (1986) Generalized autoregressive conditional heteroskedasticity. *Journal of Econometrics* 31(3):307–327.
4. Makridakis, S., Spiliotis, E. & Assimakopoulos, V. (2018) The M4 Competition: Results, findings, conclusion and way forward. *International Journal of Forecasting* 34(4):802–808.
5. NBS Data: [https://data.stats.gov.cn](https://data.stats.gov.cn)
6. Akshare: [https://akshare.akfamily.xyz](https://akshare.akfamily.xyz)
