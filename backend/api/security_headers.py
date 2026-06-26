"""
安全响应头中间件 — 弥补 <meta> CSP 限制。

通过环境变量可配置:
  ENABLE_HSTS=1            强制启用 HSTS(生产环境 HTTPS 下自动启用)
  HSTS_PRELOAD=1           HSTS 头追加 preload,申请浏览器预加载列表
  CSP_REPORT_ONLY=1        仅返回 Content-Security-Policy-Report-Only,不阻塞资源
  CSP_REPORT_URI=<url>     CSP 违规上报地址
"""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# 完整的 CSP 策略 — 限制所有资源仅允许同源加载
_CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

# 写操作方法 — 对这些方法的响应添加 Cache-Control: no-store
_WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


def _truthy(value: str | None) -> bool:
    return value is not None and value.lower() in {"1", "true", "yes", "on"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    为所有响应附加安全头:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-DNS-Prefetch-Control: off
    - X-Download-Options: noopen (IE)
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: 禁用敏感 API
    - Strict-Transport-Security: 生产环境 HTTPS 自动启用,可选 preload
    - Content-Security-Policy: 完整 CSP 策略,可选 report-only 模式
    - Cross-Origin-Opener-Policy: same-origin
    - Cross-Origin-Resource-Policy: same-origin
    - Origin-Agent-Cluster: ?1
    - Cache-Control: no-store (对 POST/PUT/DELETE 响应)
    """

    def __init__(self, app: ASGIApp, *, hsts: bool = False, preload: bool = False):
        super().__init__(app)
        # 显式 HSTS 开关(向后兼容),为 None 时按生产环境 + HTTPS 自动判断
        self.hsts = hsts
        self.preload = preload

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        # 防止 MIME 嗅探
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # 防止 clickjacking
        response.headers.setdefault("X-Frame-Options", "DENY")
        # 禁止 DNS 预取,减少信息泄露
        response.headers.setdefault("X-DNS-Prefetch-Control", "off")
        # IE 旧版下载安全
        response.headers.setdefault("X-Download-Options", "noopen")
        # 控制 referrer 泄露
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # 禁用浏览器敏感 API(摄像头/麦克风/地理/支付)
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=(), usb=(), "
            "magnetometer=(), gyroscope=(), accelerometer=(), ambient-light-sensor=()",
        )
        # Cross-Origin 隔离 — 防止跨域窗口/资源访问
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        # 请求浏览器按同源分组进程,缓解 Spectre 类侧信道攻击
        response.headers.setdefault("Origin-Agent-Cluster", "?1")

        # HSTS:显式开启 或 生产环境 + HTTPS 请求时自动启用
        is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        app_env = os.getenv("APP_ENV", "dev")
        enable_hsts = self.hsts or (app_env == "production" and is_https)
        if enable_hsts:
            hsts_value = "max-age=31536000; includeSubDomains"
            if self.preload or _truthy(os.getenv("HSTS_PRELOAD")):
                hsts_value += "; preload"
            response.headers.setdefault("Strict-Transport-Security", hsts_value)

        # CSP 策略:完整策略 或 report-only 模式
        report_uri = os.getenv("CSP_REPORT_URI")
        csp_value = _CSP_POLICY
        if report_uri:
            csp_value += f"; report-uri {report_uri}"

        report_only = _truthy(os.getenv("CSP_REPORT_ONLY"))
        csp_header = "Content-Security-Policy-Report-Only" if report_only else "Content-Security-Policy"
        if csp_header not in response.headers:
            response.headers.setdefault(csp_header, csp_value)

        # 对写操作(POST/PUT/DELETE/PATCH)响应禁止缓存,避免敏感数据被中间代理/浏览器留存
        if request.method in _WRITE_METHODS:
            response.headers.setdefault("Cache-Control", "no-store")

        return response
