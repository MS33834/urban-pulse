# Plugin Architecture — Making Urban Pulse Infinitely Extensible

> **Vision**: A community-maintained open data observatory for global city economics.
> Anyone can add a new data source, a new analysis method, or a new visualization.

---

## Overview

Urban Pulse is designed as a **pluggable framework**:

```
┌──────────────────────────────────────────────────────┐
│                   Urban Pulse Core                     │
│  (data loading, forecasting engine, API framework)     │
└──┬──────────┬──────────────┬──────────────┬───────────┘
   │          │              │              │
   ▼          ▼              ▼              ▼
┌────────┐ ┌────────┐ ┌───────────┐ ┌──────────────┐
│Collector│ │Analyzer│ │Forecaster │ │ Visualizer   │
│Plugins  │ │Plugins │ │Plugins    │ │ Plugins      │
└────────┘ └────────┘ └───────────┘ └──────────────┘
```

Each plugin type has a **base class** + **auto-discovery** — just drop a file in
the right directory and it works.

---

## 1. Collector Plugins — Add New Data Sources

```python
# backend/data_collection/base_collector.py

from abc import ABC, abstractmethod
from typing import Any
import pandas as pd


class DataCollector(ABC):
    """Base class for all data source collectors."""

    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name: 'AKShare', 'World Bank', etc."""
        ...

    @abstractmethod
    def collect(self, **kwargs) -> dict[str, pd.DataFrame]:
        """Return {city_code: DataFrame} for all collected cities."""
        ...

    @abstractmethod
    def supported_cities(self) -> list[str]:
        """Return list of city codes this collector can handle."""
        ...
```

**Built-in collectors:**
- `backend/data_collection/nbs_collector.py` — China National Bureau of Statistics
- `backend/data_collection/finance_collector.py` — Financial data APIs
- `backend/data_collection/industry_collector.py` — Industry-specific data

**Community contributors can add:**
- World Bank API collector (global cities)
- Eurostat collector (European cities)
- US Census Bureau collector (American cities)
- Local government open data portals

Just create `backend/data_collection/world_bank.py` implementing `DataCollector` →
auto-registered on next startup.

---

## 2. Analyzer Plugins — Add New Analysis Methods

```python
# backend/analysis/base_analyzer.py

class AnalysisPlugin(ABC):
    """Base class for analysis modules."""

    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def analyze(self, city_data: dict, **params) -> dict:
        """Run analysis and return results."""
        ...

    @abstractmethod
    def required_indicators(self) -> list[str]:
        """Which indicators this analysis needs."""
        ...
```

**Examples of community-contributed analyzers:**
- Housing affordability index
- Air quality / environmental impact
- Transportation infrastructure score
- Innovation index (patents, startups, VC funding)
- Quality of life composite score

---

## 3. Forecaster Plugins — Add New Prediction Models

```python
# backend/core/forecast_base.py

class ForecastingPlugin(ABC):
    """Base class for forecast models."""

    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def forecast(self, data: pd.Series, steps: int) -> tuple[np.ndarray, np.ndarray]:
        """Return (mean_forecast, confidence_intervals)."""
        ...

    @abstractmethod
    def min_data_points(self) -> int:
        """Minimum data points required."""
        ...
```

**Built-in models:** ARIMA, ETS, Ridge ensemble
**Community models:** Prophet, LSTM, Transformer, LightGBM, Gaussian Process

---

## 4. Visualizer Plugins — Add New Charts

```python
# backend/utils/visualizer_base.py

class VisualizerPlugin(ABC):
    @abstractmethod
    def name(self) -> str: ...
    @abstractmethod
    def render(self, data: dict) -> str:
        """Return HTML/JS for the visualization."""
        ...
```

The static site builder (`scripts/build_site.py`) auto-discovers and runs all
registered visualizers, embedding their output into the generated HTML.

---

## Auto-Discovery

```python
# Plugin registry in backend/core/plugin_registry.py

import importlib
import pkgutil
from pathlib import Path


class PluginRegistry:
    _collectors: dict[str, type] = {}
    _analyzers: dict[str, type] = {}
    _forecasters: dict[str, type] = {}
    _visualizers: dict[str, type] = {}

    @classmethod
    def discover(cls, package: str, base_class: type, registry: dict):
        """Scan a package for subclasses of base_class and register them."""
        package_path = Path(__file__).parent.parent / package.replace(".", "/")
        if not package_path.exists():
            return
        for finder, name, ispkg in pkgutil.iter_modules([str(package_path)]):
            module = importlib.import_module(f"{package}.{name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and issubclass(attr, base_class)
                        and attr is not base_class):
                    instance = attr()
                    registry[instance.name()] = instance
```

Drop in a file → auto-detected. No config changes needed.

---

## Phase 3 — External Plugin Packages (`pip install`)

除了内置目录扫描，Urban Pulse 还支持通过 **Python entry points** 发现独立 pip 包中的插件：

```python
# my_package/my_collector.py
from backend.data_collection.base_collector import DataCollector

class MyCollector(DataCollector):
    def name(self) -> str: return "my_collector"
    def supported_cities(self) -> list[str]: return ["my_city"]
    def fetch_data(self, **kwargs) -> list[dict]: return []
```

在第三方包的 `pyproject.toml` 中声明 entry point：

```toml
[project.entry-points."urban_pulse.collectors"]
my_collector = "my_package.my_collector:MyCollector"
```

支持的 entry point groups：

| Group | 插件类型 |
|-------|----------|
| `urban_pulse.collectors` | Collector |
| `urban_pulse.analyzers` | Analyzer |
| `urban_pulse.forecasters` | Forecaster |
| `urban_pulse.visualizers` | Visualizer |

安装后，调用 `PluginRegistry.discover_all()` 会自动加载这些外部插件，无需修改 Urban Pulse 主仓库。

示例包见 [`plugins/urban-pulse-demo/`](plugins/urban-pulse-demo/)。

---

## Roadmap for Extensibility

| Phase | Feature | What it enables |
|-------|---------|-----------------|
| **Now** | Core framework + 3 built-in collectors | 10 Chinese cities |
| **Phase 1** | Plugin auto-discovery + docs | Community contributions |
| **Phase 2** | Global city schema | Any city, any country |
| **Phase 3** | Plugin registry marketplace | `pip install urban-pulse-worldbank` |
| **Phase 4** | Auto-generated API docs per plugin | Developers can explore |
| **Phase 5** | Community validation dashboard | Forecast accuracy tracking |

---

## Long-Term Vision

Urban Pulse evolves from a **single project** into a **platform**:

```
                    ┌─────────────────────┐
                    │  urban-pulse.org     │  ← GitHub Pages
                    │  (static dashboard)  │
                    └──────┬──────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                  │
         ▼                 ▼                  ▼
   ┌──────────┐     ┌──────────┐      ┌──────────┐
   │ China    │     │ Global   │      │ Forecast │
   │ Cities   │     │ Cities   │      │ Archive  │
   └──────────┘     └──────────┘      └──────────┘
         │                 │                  │
   community         community           auto-updated
   curated           contributed          every year
```

**Key differentiators from existing projects:**
1. **Versioned data** — every dataset is committed to git (Git LFS for large files)
2. **Aged forecasts** — last year's predictions compared to this year's reality
3. **Zero operational cost** — GitCode Pages 静态托管，无额外运维成本
4. **Open science** — all data sources documented, all methods reproducible
