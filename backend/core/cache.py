"""计算结果 TTL 缓存 — 避免对确定性预测/风险计算重复求值。

进程内字典 + 时间戳实现,无第三方依赖。适用于单 worker 部署;
多 worker 下每个 worker 维护独立缓存(语义正确,仅命中率下降)。

缓存对象为只读 dict,调用方不应就地修改返回值。
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Callable

_LOCK = threading.Lock()

# 全局注册表:记录所有 @cached 装饰的缓存,供 clear_compute_cache() 统一失效。
_ALL_CACHES: list[TTLCache] = []


def _to_hashable(obj: Any) -> Any:
    """递归把 list/tuple/dict/set 转为可哈希的元组表示。"""
    if isinstance(obj, list):
        return tuple(_to_hashable(x) for x in obj)
    if isinstance(obj, tuple):
        return tuple(_to_hashable(x) for x in obj)
    if isinstance(obj, dict):
        return tuple(sorted((k, _to_hashable(v)) for k, v in obj.items()))
    if isinstance(obj, (set, frozenset)):
        return tuple(sorted(_to_hashable(x) for x in obj))
    return obj


class TTLCache:
    """线程安全的 TTL + LRU 缓存。"""

    def __init__(self, maxsize: int = 256, ttl: float = 3600.0) -> None:
        self._store: OrderedDict[Any, tuple[float, Any]] = OrderedDict()
        self._maxsize = maxsize
        self._ttl = ttl

    def _key(self, args: tuple, kwargs: dict) -> Any:
        return (_to_hashable(args), _to_hashable(kwargs))

    def get(self, args: tuple, kwargs: dict) -> Any:
        key = self._key(args, kwargs)
        now = time.monotonic()
        with _LOCK:
            entry = self._store.get(key)
            if entry is None:
                return _MISS
            ts, value = entry
            if now - ts > self._ttl:
                self._store.pop(key, None)
                return _MISS
            self._store.move_to_end(key)
            return value

    def set(self, args: tuple, kwargs: dict, value: Any) -> None:
        key = self._key(args, kwargs)
        now = time.monotonic()
        with _LOCK:
            self._store[key] = (now, value)
            self._store.move_to_end(key)
            while len(self._store) > self._maxsize:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with _LOCK:
            self._store.clear()


_MISS = object()


def cached(maxsize: int = 256, ttl: float = 3600.0) -> Callable[[Callable], Callable]:
    """装饰器:为纯函数附加 TTL 缓存。

    仅缓存成功返回值(dict/list 返回浅拷贝,防止调用方污染缓存)。
    若被装饰函数抛出异常则不缓存。
    """

    cache = TTLCache(maxsize=maxsize, ttl=ttl)
    _ALL_CACHES.append(cache)

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            hit = cache.get(args, kwargs)
            if hit is not _MISS:
                return _copy(hit)
            value = func(*args, **kwargs)
            cache.set(args, kwargs, value)
            return value

        wrapper.cache_clear = cache.clear  # type: ignore[attr-defined]
        wrapper.__wrapped__ = func  # type: ignore[attr-defined]
        return wrapper

    return decorator


def clear_compute_cache() -> None:
    """失效所有 @cached 装饰的缓存(在底层数据刷新后调用)。"""
    for cache in _ALL_CACHES:
        cache.clear()


def _copy(value: Any) -> Any:
    """对可变容器做浅拷贝,避免缓存被调用方就地修改。"""
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    return value


__all__ = ["TTLCache", "cached", "clear_compute_cache"]
