"""
可观测性中间件

- RequestIdMiddleware: 为每个请求生成/透传 X-Request-ID,并注入响应头
- MetricsMiddleware: 记录请求耗时、状态码、方法、路径,支持 Prometheus 风格计数

可通过环境变量控制:
  REQUEST_ID_HEADER=X-Request-ID   请求 ID 头名称(默认)
  ENABLE_METRICS=1                 是否记录每个请求的性能指标(默认开启)
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from collections import Counter

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

_REQUEST_ID_HEADER = os.getenv("REQUEST_ID_HEADER", "X-Request-ID")
_ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() in {"1", "true", "yes", "on"}

# 内存中的简单计数器(适合单进程/少量 worker 场景)
_request_counts: Counter[str] = Counter()
_request_durations: Counter[str] = Counter()


def get_request_metrics() -> dict[str, dict[str, int | float]]:
    """返回当前进程收集的基础指标快照。"""
    return {
        "counts": dict(_request_counts),
        "durations_ms": {k: round(v, 3) for k, v in _request_durations.items()},
    }


class RequestIdMiddleware:
    """
    ASGI 请求 ID 中间件。

    - 如果请求头包含 X-Request-ID,直接透传
    - 否则生成 UUID4 作为请求 ID
    - 将请求 ID 写入响应头,便于全链路追踪
    """

    def __init__(self, app: ASGIApp, *, header_name: str = _REQUEST_ID_HEADER):
        self.app = app
        self.header_name = header_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        request_id = request.headers.get(self.header_name)
        if not request_id:
            request_id = str(uuid.uuid4())

        async def wrapped_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((self.header_name.encode("latin-1"), request_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, wrapped_send)


class MetricsMiddleware:
    """
    ASGI 性能指标中间件。

    记录:
      - 请求耗时(毫秒)
      - 按状态码和方法分类的计数
      - 慢请求警告(>1s)
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        enabled: bool = _ENABLE_METRICS,
        slow_request_ms: float = 1000.0,
        skip_paths: set[str] | None = None,
    ):
        self.app = app
        self.enabled = enabled
        self.slow_request_ms = slow_request_ms
        self.skip_paths = skip_paths or {"/health", "/favicon.ico"}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        path = request.url.path
        method = request.method
        start = time.perf_counter()

        status_code = 200

        async def wrapped_send(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)

        await self.app(scope, receive, wrapped_send)

        if path in self.skip_paths:
            return

        duration_ms = (time.perf_counter() - start) * 1000
        key = f"{method} {path} {status_code}"
        _request_counts[key] += 1
        _request_durations[key] += duration_ms

        log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 3),
        }

        if duration_ms > self.slow_request_ms:
            logger.warning("慢请求: %s %s 耗时 %.2fms", method, path, duration_ms, extra=log_data)
        else:
            logger.info("%s %s %d %.2fms", method, path, status_code, duration_ms, extra=log_data)
