"""
Urban Pulse — FastAPI backend for city economic intelligence.

REST API + ECharts dashboard. One process, no frontend build step.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, Response

from config import settings

logger = logging.getLogger(__name__)

# ── helper: seed city_manager from backend.data.city_data ──────────────────
def _seed_city_manager() -> None:
    """Load CITY_DATA + HISTORICAL_DATA into city_manager for time-series & compare endpoints."""
    from backend.core.multi_city import CityData, city_manager

    name_to_code = {
        "深圳": "sz", "上海": "sh", "北京": "bj", "广州": "gz",
        "杭州": "hz", "武汉": "wh", "成都": "cd", "南京": "nj",
    }
    try:
        from backend.data.city_data import CITY_DATA, HISTORICAL_DATA
    except ImportError:
        logger.warning("backend.data.city_data not available -- city_manager remains unseeded")
        return

    loaded = 0
    # 1) Current-year snapshot from CITY_DATA
    for city_name, fields in CITY_DATA.items():
        code = name_to_code.get(city_name)
        if code is None or city_manager.get_city(code) is None:
            continue
        year = fields.get("year", 2025)
        indicators = {k: v for k, v in fields.items()
                       if k not in ("name", "year", "region", "industry",
                                    "industry_code", "data_source", "data_quality")}
        cd = CityData(city_code=code, city_name=city_name,
                      year=year, indicators=indicators,
                      source=fields.get("data_source", "nbs"))
        city_manager.add_city_data(cd)
        loaded += 1

    # 2) Historical time-series from HISTORICAL_DATA
    for city_name, rows in HISTORICAL_DATA.items():
        code = name_to_code.get(city_name)
        if code is None or city_manager.get_city(code) is None:
            continue
        for row in rows:
            year = row.get("year")
            if year is None:
                continue
            indicators = {k: v for k, v in row.items() if k != "year"}
            cd = CityData(city_code=code, city_name=city_name,
                          year=year, indicators=indicators,
                          source="nbs/historical")
            city_manager.add_city_data(cd)
            loaded += 1

    logger.info("seeded city_manager: %d CityData records across %d cities",
                loaded, len(city_manager.city_data))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting %s v%s", settings.PROJECT_NAME, settings.VERSION)
    logger.info("loaded %d cities", len(getattr(settings, "CITY_NAMES", [])))

    # Init SQLite storage + seed 10-city dataset
    from backend.core.storage import init_db
    init_db()
    from backend.seed_data import seed_if_missing
    seed_if_missing()

    _seed_city_manager()
    yield
    logger.info("shutting down")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="REST API — 10 Chinese cities, 16 years of data, ensemble forecasting. Built because I wanted to watch how cities grow.",
    license_info={
        "name": "GPL-3.0-or-later",
        "url": "https://www.gnu.org/licenses/gpl-3.0.html",
    },
    openapi_tags=[
        {"name": "区域", "description": "国家/省/市/区县多层级区域发现、时序与预测。"},
    {"name": "城市数据", "description": "Multi-city economic data endpoints."},
    {"name": "分析预测", "description": "Forecasting, risk, and scenario analysis."},
    {"name": "对比分析", "description": "Side-by-side city comparison."},
    {"name": "数据管理", "description": "Data import / export."},
    {"name": "系统", "description": "Health, metadata, and static assets."},
],
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ----- Middleware -----
ENABLE_HSTS = os.getenv("ENABLE_HSTS", "false").lower() in {"1", "true", "yes"}

allow_credentials = "*" not in settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

_trusted_hosts_env = os.getenv("TRUSTED_HOSTS")
if _trusted_hosts_env:
    _allowed_hosts = [h.strip() for h in _trusted_hosts_env.split(",") if h.strip()]
else:
    _allowed_hosts = ["localhost", "127.0.0.1", "*.local", "testserver", "testclient"]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)

# ----- Routes -----
from backend.api.routes import (
    analysis_router,
    analysis_v3_router,
    cities_router,
    cities_v2_router,
    data_router,
    datasets_router,
    forecast_router,
    index_router,
    industries_router,
    regions_router,
    static_router,
)

app.include_router(data_router, prefix=settings.API_V1_STR)
app.include_router(datasets_router, prefix=settings.API_V1_STR)
app.include_router(analysis_router, prefix=settings.API_V1_STR)
app.include_router(analysis_v3_router, prefix=settings.API_V1_STR)
app.include_router(cities_router, prefix=settings.API_V1_STR)
app.include_router(cities_v2_router, prefix=settings.API_V1_STR)
app.include_router(regions_router, prefix=settings.API_V1_STR)
app.include_router(forecast_router, prefix=settings.API_V1_STR)
app.include_router(index_router, prefix=settings.API_V1_STR)
app.include_router(industries_router, prefix=settings.API_V1_STR)
app.include_router(static_router)

frontend_index = Path(__file__).parent.parent.parent / "frontend" / "index.html"


@app.get("/dashboard", tags=["页面"])
async def get_dashboard():
    if frontend_index.exists():
        return FileResponse(frontend_index, media_type="text/html")
    return {"error": "frontend not built", "hint": "frontend/index.html missing"}


@app.get("/", tags=["根路径"])
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "status": "running",
    }


@app.get("/health", tags=["系统"])
def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "timestamp": datetime.now().isoformat(),
    }


# ----- Favicon -----
FAVICON_PATH = Path(__file__).parent.parent.parent / "frontend" / "favicon.ico"
FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    '<rect width="100" height="100" rx="20" fill="#2563eb"/>'
    '<text x="50" y="65" font-size="52" text-anchor="middle" fill="white" '
    'font-family="Arial" font-weight="bold">U</text>'
    "</svg>"
)


@app.get("/favicon.ico", tags=["静态资源"], include_in_schema=False)
def favicon():
    if FAVICON_PATH.exists():
        return FileResponse(FAVICON_PATH, media_type="image/x-icon")
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")


def run() -> None:
    """Console-script entry point."""
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    workers = int(os.getenv("WORKERS", "1"))
    reload = os.getenv("APP_RELOAD", "false").lower() in {"1", "true", "yes"}
    uvicorn.run(
        "backend.api.main:app",
        host=host,
        port=port,
        workers=workers if not reload else 1,
        reload=reload,
    )


if __name__ == "__main__":
    run()

