"""
Urban Pulse - REST API routes.
"""

from backend.api.routes.analysis import router as analysis_router
from backend.api.routes.cities import router as cities_router
from backend.api.routes.data import router as data_router
from backend.api.routes.datasets import router as datasets_router
from backend.api.routes.forecast import router as forecast_router
from backend.api.routes.forecast_archive import router as archive_router
from backend.api.routes.health import router as health_router
from backend.api.routes.index import router as index_router
from backend.api.routes.industries import router as industries_router
from backend.api.routes.regions import router as regions_router
from backend.api.routes.risk import router as risk_router
from backend.api.routes.static import router as static_router
from backend.api.routes.validation import router as validation_router
from backend.api.routes.viz import router as viz_router
from backend.api.routes.models import router as models_router

__all__ = [
    "analysis_router",
    "archive_router",
    "cities_router",
    "data_router",
    "datasets_router",
    "forecast_router",
    "health_router",
    "index_router",
    "industries_router",
    "regions_router",
    "risk_router",
    "static_router",
    "validation_router",
    "viz_router",
    "models_router",
]
