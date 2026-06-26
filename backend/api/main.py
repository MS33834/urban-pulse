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
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.routing import APIRoute
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.api.auth import get_current_user
from backend.api.compression import CompressionMiddleware
from backend.api.ratelimit import limiter
from backend.api.security_headers import SecurityHeadersMiddleware
from config import settings

logger = logging.getLogger(__name__)


# ── helper: seed city_manager from region registry ─────────────────────────
def _seed_city_manager() -> None:
    """Load all registered cities into city_manager for time-series & compare endpoints."""
    from backend.core.multi_city import CityConfig, CityData, city_manager
    from backend.regions import RegionLevel, get_registry

    registry = get_registry()
    if registry is None:
        logger.warning("Region registry not available -- city_manager remains unseeded")
        return

    loaded = 0
    for region in registry.list_all(RegionLevel.CITY):
        # Register city config (use full registry code as city_code)
        config = CityConfig(
            code=region.code,
            name=region.name,
            province=region.region or "",
            latitude=region.metadata.get("latitude", 0.0),
            longitude=region.metadata.get("longitude", 0.0),
            population=int(region.indicators.get("population", 0) or 0),
            gdp_rank=int(region.indicators.get("gdp_rank", 0) or 0),
            description=region.metadata.get("description", ""),
            tags=region.metadata.get("tags", []),
            metadata={"parent_code": region.parent_code, "region": region.region},
        )
        city_manager.register_city(config)

        # Add current-year snapshot
        if region.indicators:
            year = region.indicators.get("year", 2024)
            indicators = {
                k: v
                for k, v in region.indicators.items()
                if k not in ("name", "year", "region", "industry", "industry_code", "data_source", "data_quality")
            }
            cd = CityData(
                city_code=region.code,
                city_name=region.name,
                year=year,
                indicators=indicators,
                source=region.metadata.get("data_source", "nbs"),
            )
            city_manager.add_city_data(cd)
            loaded += 1

        # Add historical time-series
        for row in region.historical_data:
            year = row.get("year")
            if year is None:
                continue
            indicators = {k: v for k, v in row.items() if k != "year"}
            cd = CityData(
                city_code=region.code,
                city_name=region.name,
                year=year,
                indicators=indicators,
                source="nbs/historical",
            )
            city_manager.add_city_data(cd)
            loaded += 1

    logger.info("seeded city_manager: %d CityData records across %d cities", loaded, len(city_manager.city_data))


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
    description="中国城市经济数据 REST API：35 城、16 年指标、集成预测与企业/政府/产业分析。",
    license_info={
        "name": "GPL-3.0-or-later",
        "url": "https://www.gnu.org/licenses/gpl-3.0.html",
    },
    openapi_tags=[
        {"name": "区域", "description": "国家/省/市/区县多层级区域发现、时序与预测。"},
        {"name": "城市", "description": "城市列表、详情、历史数据、排名与对比。"},
        {"name": "企业端", "description": "企业选址、成本、供应链与政策环境分析。"},
        {"name": "政府端", "description": "财政杠杆、产业带动与产业链完整性分析。"},
        {"name": "产业端", "description": "产业注册、预测与因素调整。"},
        {"name": "预测", "description": "时序预测。"},
        {"name": "预测存档", "description": "预测快照存档、查询与真实值回填。"},
        {"name": "预测验证", "description": "预测准确率验证报告与 HTML 仪表板。"},
        {"name": "风险分析", "description": "波动率、VaR/CVaR、情景分析与蒙特卡洛模拟。"},
        {"name": "指数", "description": "竞争力指数计算与排名。"},
        {"name": "数据管理", "description": "数据集上传、查询、导入与导出。"},
        {"name": "系统", "description": "健康检查、元数据与静态资源。"},
        {"name": "页面", "description": "仪表盘与静态页面入口。"},
    ],
    lifespan=lifespan,
    # 生产环境关闭交互式文档,避免泄露 API 结构
    docs_url=None if settings.APP_ENV == "production" else "/docs",
    redoc_url=None if settings.APP_ENV == "production" else "/redoc",
    openapi_url=None if settings.APP_ENV == "production" else "/openapi.json",
)

# ----- Middleware -----
ENABLE_HSTS = os.getenv("ENABLE_HSTS", "false").lower() in {"1", "true", "yes"}

allow_credentials = "*" not in settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With", "X-API-Key"],
)

_trusted_hosts_env = os.getenv("TRUSTED_HOSTS")
if _trusted_hosts_env:
    _allowed_hosts = [h.strip() for h in _trusted_hosts_env.split(",") if h.strip()]
else:
    # 默认仅允许本地回环地址,移除 *.local/testserver/testclient 等宽松主机
    _allowed_hosts = ["localhost", "127.0.0.1"]
    # 测试/开发环境兼容 TestClient(Host: testserver),生产环境严格限制
    if settings.APP_ENV in {"test", "dev"}:
        _allowed_hosts.extend(["testserver", "testclient"])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)
app.add_middleware(SecurityHeadersMiddleware, hsts=ENABLE_HSTS)

# 速率限制中间件 — 必须在路由注册前将 limiter 挂载到 app.state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# 响应压缩 — 作为最外层中间件,在 SecurityHeadersMiddleware 之后压缩最终响应体
# 对 text/* / application/json / application/javascript 等大于 200B 的响应启用 gzip/br
app.add_middleware(CompressionMiddleware, minimum_size=200, compresslevel=6)

# ----- Routes -----
from backend.api.routes import (
    analysis_router,
    archive_router,
    cities_router,
    data_router,
    datasets_router,
    forecast_router,
    health_router,
    index_router,
    industries_router,
    models_router,
    regions_router,
    risk_router,
    static_router,
    validation_router,
    viz_router,
)

app.include_router(data_router, prefix=settings.API_V1_STR)
app.include_router(datasets_router, prefix=settings.API_V1_STR)
app.include_router(analysis_router, prefix=settings.API_V1_STR)
app.include_router(cities_router, prefix=settings.API_V1_STR)
app.include_router(regions_router, prefix=settings.API_V1_STR)
app.include_router(forecast_router, prefix=settings.API_V1_STR)
app.include_router(archive_router, prefix=settings.API_V1_STR)
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(risk_router, prefix=settings.API_V1_STR)
app.include_router(validation_router, prefix=settings.API_V1_STR)
app.include_router(index_router, prefix=settings.API_V1_STR)
app.include_router(industries_router, prefix=settings.API_V1_STR)
app.include_router(viz_router, prefix=settings.API_V1_STR)
app.include_router(models_router, prefix=settings.API_V1_STR)
app.include_router(static_router)


# ----- 对所有写操作端点(POST/PUT/DELETE)添加 API Key 认证依赖 -----
def _apply_auth_to_write_routes() -> None:
    """
    遍历 app 中已注册的路由,对 POST/PUT/DELETE 方法追加 ``Depends(get_current_user)``。

    - 通过 ``include_router`` 注册的路由:修改原始 router 中 APIRoute 的 ``dependencies``
    - 直接挂在 ``app`` 上的 APIRoute:直接追加到 ``dependant.dependencies`` 并重建 flat_dependant
    """
    from fastapi.dependencies.utils import get_dependant, get_flat_dependant

    try:
        from fastapi.routing import _IncludedRouter
    except ImportError:  # pragma: no cover - 兼容旧版 FastAPI
        _IncludedRouter = None  # type: ignore[assignment]

    write_methods = {"POST", "PUT", "DELETE"}
    auth_dep = Depends(get_current_user)

    for route in list(app.routes):
        # 通过 include_router 注册的路由(FastAPI 0.115+ 使用 _IncludedRouter 懒加载)
        if _IncludedRouter is not None and isinstance(route, _IncludedRouter):
            for orig_route in route.original_router.routes:
                if isinstance(orig_route, APIRoute) and orig_route.methods & write_methods:
                    orig_route.dependencies = list(orig_route.dependencies) + [auth_dep]
            continue

        # 直接挂在 app 上的 APIRoute
        if isinstance(route, APIRoute) and route.methods & write_methods:
            route.dependencies = list(route.dependencies) + [auth_dep]
            # 直接定义的路由 dependant 已构建,需要追加并重建 flat_dependant
            sub_dependant = get_dependant(path=route.path, call=get_current_user)
            route.dependant.dependencies.append(sub_dependant)
            route.flat_dependant = get_flat_dependant(route.dependant)


_apply_auth_to_write_routes()

frontend_index = Path(__file__).parent.parent.parent / "frontend" / "index.html"
frontend_dir = Path(__file__).parent.parent.parent / "frontend"


@app.get("/dashboard", tags=["页面"])
async def get_dashboard():
    if frontend_index.exists():
        return FileResponse(frontend_index, media_type="text/html")
    return {"error": "frontend not built", "hint": "frontend/index.html missing"}


@app.get("/viz-demo.html", tags=["页面"])
async def get_viz_demo():
    demo_path = frontend_dir / "viz-demo.html"
    if demo_path.exists():
        return FileResponse(demo_path, media_type="text/html")
    return {"error": "viz demo not built", "hint": "frontend/viz-demo.html missing"}


@app.get("/css/{path:path}", tags=["静态资源"], include_in_schema=False)
async def get_css(path: str):
    file_path = frontend_dir / "css" / path
    if file_path.exists() and file_path.is_file():
        # 静态资源已带 ?v= 哈希查询串做版本控制,可长期缓存
        return FileResponse(file_path, media_type="text/css", headers={"Cache-Control": "public, max-age=86400"})
    raise HTTPException(status_code=404, detail="CSS not found")


@app.get("/js/{path:path}", tags=["静态资源"], include_in_schema=False)
async def get_js(path: str):
    file_path = frontend_dir / "js" / path
    if file_path.exists() and file_path.is_file():
        # 静态资源已带 ?v= 哈希查询串做版本控制,可长期缓存
        return FileResponse(file_path, media_type="application/javascript", headers={"Cache-Control": "public, max-age=86400"})
    raise HTTPException(status_code=404, detail="JS not found")


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
    # 生产环境强制禁用 reload,避免文件监听带来的安全与稳定性风险
    if settings.APP_ENV == "production" and reload:
        logger.warning("APP_ENV=production 下强制禁用 reload,忽略 APP_RELOAD 设置")
        reload = False
    uvicorn.run(
        "backend.api.main:app",
        host=host,
        port=port,
        workers=workers if not reload else 1,
        reload=reload,
    )


if __name__ == "__main__":
    run()
