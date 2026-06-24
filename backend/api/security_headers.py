"""
安全响应头中间件 — 弥补 <meta> CSP 限制。
"""

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# 完整的 CSP 策略 — 限制所有资源仅允许同源加载
CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)

# 写操作方法 — 对这些方法的响应添加 Cache-Control: no-store
_WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    为所有响应附加安全头:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: 禁用敏感 API
    - Strict-Transport-Security: 生产环境 HTTPS 自动启用
    - Content-Security-Policy: 完整 CSP 策略
    - Cross-Origin-Opener-Policy: same-origin
    - Cross-Origin-Resource-Policy: same-origin
    - Cache-Control: no-store (对 POST/PUT/DELETE 响应)
    """

    def __init__(self, app: ASGIApp, *, hsts: bool = False):
        super().__init__(app)
        # 显式 HSTS 开关(向后兼容),为 None 时按生产环境 + HTTPS 自动判断
        self.hsts = hsts

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        # 防止 MIME 嗅探
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # 防止 clickjacking
        response.headers.setdefault("X-Frame-Options", "DENY")
        # 控制 referrer 泄露
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # 禁用浏览器敏感 API(摄像头/麦克风/地理/支付)
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()",
        )
        # Cross-Origin 隔离 — 防止跨域窗口/资源访问
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")

        # HSTS:显式开启 或 生产环境 + HTTPS 请求时自动启用
        is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        app_env = os.getenv("APP_ENV", "dev")
        enable_hsts = self.hsts or (app_env == "production" and is_https)
        if enable_hsts:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        # 完整 CSP 策略(frame-ancestors 必须走 header,meta 标签不生效)
        if "Content-Security-Policy" not in response.headers:
            response.headers.setdefault("Content-Security-Policy", CSP_POLICY)

        # 对写操作(POST/PUT/DELETE/PATCH)响应禁止缓存,避免敏感数据被中间代理/浏览器留存
        if request.method in _WRITE_METHODS:
            response.headers.setdefault("Cache-Control", "no-store")

        return response
