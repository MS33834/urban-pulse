# Notebooks — Data Exploration & Analysis

This directory contains Jupyter notebooks and Python scripts for exploratory
data analysis (EDA) and model prototyping.

## Notebooks

| File | Description |
|------|-------------|
| `01_data_collection_analysis.py` | Data collection pipeline analysis |
| `01_EDA_AND_INSIGHTS.py` | Exploratory analysis + insights |
| `02_COST_PREDICTION.py` | Cost prediction modeling |
| `03_CAUSAL_INFERENCE.py` | Causal inference experiments |
| `eda_real_data.py` | Full EDA with real macro data from AKShare |

## Running

```bash
# Run any script directly (uses backend data)
python notebooks/eda_real_data.py
```

## Convert to .ipynb

```bash
pip install jupytext
jupytext --to notebook notebooks/eda_real_data.py
```

## Suggested Analyses

1. **Time-series forecasting** — ARIMA / Prophet on GDP and CPI
2. **Cross-city comparison** — Economic indicators across all 10 cities
3. **Industry deep-dive** — Semiconductor supply chain analysis
4. **Geo-visualization** — GeoPandas economic heatmap
