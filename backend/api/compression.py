"""
响应压缩中间件

- 优先使用 Brotli(若安装),回退到 gzip(Python 标准库)
- 仅压缩 text/* / application/json / application/javascript 等可压缩类型
- 跳过已经 tiny(<200B) 的响应,避免压缩反而增加体积
- 与 SecurityHeadersMiddleware 配合:SecurityHeadersMiddleware 会先添加头,
  本中间件再压缩响应体,两者顺序无关
"""

from __future__ import annotations

import gzip
import io
import logging
from typing import Any

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

# 可压缩的 MIME 类型前缀
_COMPRESSIBLE_TYPES = {
    "text/",
    "application/json",
    "application/javascript",
    "application/xml",
    "application/rss+xml",
    "application/atom+xml",
    "image/svg+xml",
}

# 不压缩的最小阈值(字节)——太小的响应压缩后反而更大
_MIN_SIZE = 200


def _compressible(media_type: str | None) -> bool:
    if not media_type:
        return False
    return any(media_type.startswith(prefix) for prefix in _COMPRESSIBLE_TYPES)


class CompressionMiddleware:
    """
    ASGI 压缩中间件。

    参数:
        minimum_size: 触发压缩的最小响应体字节数
        compresslevel: gzip 压缩级别(1-9),默认 6
    """

    def __init__(self, app: ASGIApp, *, minimum_size: int = _MIN_SIZE, compresslevel: int = 6):
        self.app = app
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel
        # 运行时检测 brotli
        self._brotli = self._load_brotli()

    @staticmethod
    def _load_brotli() -> Any | None:
        try:
            import brotli  # type: ignore[import-not-found]
            return brotli
        except ImportError:  # pragma: no cover - 可选依赖
            return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        accepted = request.headers.get("accept-encoding", "")

        # 按优先级决定编码
        encoding: str | None = None
        if self._brotli and "br" in accepted:
            encoding = "br"
        elif "gzip" in accepted:
            encoding = "gzip"

        if encoding is None:
            await self.app(scope, receive, send)
            return

        response = _BufferedResponse(self.app, encoding, self.minimum_size, self.compresslevel)
        await response(scope, receive, send)


class _BufferedResponse:
    def __init__(
        self,
        app: ASGIApp,
        encoding: str,
        minimum_size: int,
        compresslevel: int,
    ):
        self.app = app
        self.encoding = encoding
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel
        self._brotli = CompressionMiddleware._load_brotli()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        body = io.BytesIO()
        start_message: Message | None = None

        async def wrapped_send(message: Message) -> None:
            nonlocal start_message
            if message["type"] == "http.response.start":
                start_message = message
                # 暂不发送 start,等 body 收集完再决定是否压缩
                return
            if message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                if chunk:
                    body.write(chunk)
                if message.get("more_body", False):
                    return

                # 全部 body 已收集
                raw_body = body.getvalue()
                assert start_message is not None
                status_code = start_message.get("status", 200)
                # 用大小写不敏感的字典收集响应头
                headers: dict[str, str] = {}
                for name, value in start_message.get("headers", []):
                    headers[name.decode("latin-1").lower()] = value.decode("latin-1")

                media_type = headers.get("content-type", "").split(";")[0].strip()

                if (
                    200 <= status_code < 300
                    and len(raw_body) >= self.minimum_size
                    and _compressible(media_type)
                    and "content-encoding" not in headers
                ):
                    compressed = self._compress(raw_body)
                    if len(compressed) < len(raw_body):
                        raw_body = compressed
                        headers["content-encoding"] = self.encoding
                        headers["content-length"] = str(len(raw_body))
                        headers["vary"] = "accept-encoding"

                raw_headers = [(k.encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()]
                await send({
                    "type": "http.response.start",
                    "status": status_code,
                    "headers": raw_headers,
                })
                await send({"type": "http.response.body", "body": raw_body})

        await self.app(scope, receive, wrapped_send)

    def _compress(self, data: bytes) -> bytes:
        if self.encoding == "br" and self._brotli is not None:
            return self._brotli.compress(data)
        # gzip 回退
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=self.compresslevel) as f:
            f.write(data)
        return buf.getvalue()
