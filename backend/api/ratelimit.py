"""速率限制器单例。

从 ``backend.api.main`` 中拆出,避免路由文件与 main 之间的循环导入:
路由模块在顶层 ``from backend.api.ratelimit import limiter`` 即可,
不再需要 ``# noqa: E402`` 的延迟导入 hack。
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

__all__ = ["limiter"]
