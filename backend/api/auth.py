"""
API Key 认证模块。

- 基于 ``X-API-Key`` 请求头进行认证
- 当 ``settings.API_KEYS`` 为空时,认证可选(dev 模式),返回匿名用户标识
- 当 ``settings.API_KEYS`` 非空时,强制认证,无效 key 返回 401
- 返回简单用户标识(API key 的前 8 位),便于日志追踪
"""

from __future__ import annotations

import logging
import secrets

from fastapi import Header, HTTPException, status

from config import settings

logger = logging.getLogger(__name__)

# 匿名用户标识(dev 模式下使用)
_ANONYMOUS_USER = "anonymous"


def get_current_user(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    """
    校验请求头 ``X-API-Key`` 并返回用户标识。

    - ``settings.API_KEYS`` 为空:认证可选(dev 模式),返回 ``anonymous``
    - ``settings.API_KEYS`` 非空:必须提供有效 key,否则 401

    返回值:API key 的前 8 位作为用户标识(便于日志追踪)。
    """
    # dev 模式:未配置 API_KEYS,认证可选
    if not settings.API_KEYS:
        return _ANONYMOUS_USER

    # 强制认证模式:必须提供 API key
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 API Key,请在请求头中提供 X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # 使用 secrets.compare_digest 防止时序攻击
    matched = any(secrets.compare_digest(x_api_key, valid) for valid in settings.API_KEYS)
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # 返回 API key 的前 8 位作为用户标识
    return x_api_key[:8]
