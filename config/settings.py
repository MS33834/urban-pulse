"""
Regional Industrial Economic Analysis Platform - unified configuration.

All defaults can be overridden via environment variables or a `.env` file.
"""

import json
import logging
import os
import warnings
from pathlib import Path
from typing import Annotated, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode


class Settings(BaseSettings):
    """Application configuration."""

    # Basic metadata
    PROJECT_NAME: str = "Urban Pulse"
    PROJECT_NAME_ZH: str = "城市脉搏 — 城市经济智能分析"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Environment (dev / staging / production / test)
    APP_ENV: Literal["dev", "staging", "production", "test"] = "dev"

    # API service
    API_HOST: str = "0.0.0.0"  # nosec B104 - intentional bind for containerized service
    API_PORT: int = 8000
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    DATABASE_URL: str = "sqlite:///./data/urban_pulse.db"

    # CORS
    # 0.0.0.0 不应出现在白名单 — 它是绑定地址,不是 Origin 头合法值
    CORS_ORIGINS: list[str] = json.loads(
        os.getenv(
            "CORS_ORIGINS",
            '["http://localhost:5173","http://localhost:8000","http://localhost:8080","http://127.0.0.1:8000","http://127.0.0.1:8080"]',
        )
    )

    # API Key 认证 — 环境变量 API_KEYS 用逗号分隔,如 "key1,key2,key3"
    # 为空列表时认证可选(dev 模式);非空则强制认证
    API_KEYS: Annotated[list[str], NoDecode] = []

    @field_validator("API_KEYS", mode="before")
    @classmethod
    def _parse_api_keys_csv(cls, v):
        """支持逗号分隔的 API_KEYS 环境变量(避免 pydantic-settings 按 JSON 解析)。"""
        if isinstance(v, str):
            return [k.strip() for k in v.split(",") if k.strip()]
        if isinstance(v, (list, tuple)):
            return [str(k).strip() for k in v if str(k).strip()]
        return v

    # Scraper configuration
    SCRAPER_TIMEOUT: int = 30
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_DELAY: float = 1.0

    # Cache
    CACHE_TTL: int = 3600
    CACHE_DIR: str = "./data/cache"

    # Data directories
    DATA_DIR: str = "./data"
    EXPORT_DIR: str = "./data/exports"
    RAW_DATA_DIR: str = "./data/raw"
    PROCESSED_DATA_DIR: str = "./data/processed"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str | None = None

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"  # nosec B105 - dev default blocked in production by validator
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # 插件安全 - 允许加载的外部插件(entry point 名称)白名单。
    # 通过环境变量 ALLOWED_PLUGINS 配置,逗号分隔,例如 "my_collector,my_analyzer"。
    # 为空时禁用外部插件发现,避免自动加载任意 pip 包中声明的插件。
    ALLOWED_PLUGINS: Annotated[list[str], NoDecode] = []

    @field_validator("ALLOWED_PLUGINS", mode="before")
    @classmethod
    def _parse_allowed_plugins_csv(cls, v):
        """支持逗号分隔的 ALLOWED_PLUGINS 环境变量(避免 pydantic-settings 按 JSON 解析)。"""
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        if isinstance(v, (list, tuple)):
            return [str(s).strip() for s in v if str(s).strip()]
        return v

    # Analysis parameters
    DEFAULT_YEAR: int = 2025
    DEFAULT_REGION: str = "深圳"
    DEFAULT_INDUSTRY: str = "半导体"

    # Repository metadata
    REPO_URL: str = "https://gitcode.com/badhope/urban-pulse"
    LICENSE: str = "GPL-3.0-or-later"

    model_config = {"case_sensitive": True, "env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def _enforce_secret_key_in_production(self):
        """在 production 环境下强制要求显式 SECRET_KEY,避免使用开发默认值。"""
        if self.APP_ENV == "production" and self.SECRET_KEY == "dev-secret-key-change-in-production":  # nosec B105
            raise ValueError(
                "SECRET_KEY must be explicitly set in production. "
                "Export the SECRET_KEY environment variable to a strong random value."
            )
        return self

    @model_validator(mode="after")
    def _enforce_cors_whitelist_in_production(self):
        """production 环境禁止使用通配符 '*' 作为 CORS 源,避免任意站点跨域访问。"""
        if self.APP_ENV == "production" and "*" in self.CORS_ORIGINS:
            raise ValueError(
                "CORS_ORIGINS must not contain '*' in production. "
                "Explicitly list the allowed origins via the CORS_ORIGINS environment variable."
            )
        return self

    @model_validator(mode="after")
    def _warn_if_no_api_keys_in_production(self):
        """production 环境下若 API_KEYS 为空,发出警告(认证将退化为可选,存在安全风险)。"""
        if self.APP_ENV == "production" and not self.API_KEYS:
            warnings.warn(
                "API_KEYS is empty in production. API authentication is optional and "
                "all write endpoints are publicly accessible. Set the API_KEYS environment "
                "variable (comma-separated) to enforce authentication.",
                RuntimeWarning,
                stacklevel=2,
            )
        return self

    @model_validator(mode="after")
    def _forbid_debug_in_production(self):
        """production 环境禁止开启 DEBUG,避免泄露敏感堆栈与内部信息。"""
        if self.APP_ENV == "production" and self.DEBUG:
            raise ValueError(
                "DEBUG must be False in production. Unset DEBUG or set DEBUG=false "
                "when APP_ENV=production."
            )
        return self


class _JsonFormatter(logging.Formatter):
    """轻量级 JSON 日志格式化器(无第三方依赖)。"""

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # 合并 extra 字段
        for key, value in record.__dict__.items():
            if key not in payload and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(settings: Settings):
    """Configure the application-wide logging system."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if settings.LOG_FILE:
        handlers.append(logging.FileHandler(settings.LOG_FILE, encoding="utf-8"))

    if settings.LOG_FORMAT.lower() == "json":
        formatter: logging.Formatter = _JsonFormatter()
    else:
        formatter = logging.Formatter(settings.LOG_FORMAT)

    for handler in handlers:
        handler.setFormatter(formatter)

    logging.basicConfig(level=log_level, handlers=handlers)
    # 第三方库通常较吵,保持 WARNING 以上
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


settings = Settings()
setup_logging(settings)

if settings.ALGORITHM == "RS256" and not settings.SECRET_KEY.startswith("-----BEGIN"):
    import warnings

    warnings.warn(
        "SECRET_KEY does not appear to be an RSA private key. For RS256, a valid RSA key pair is required.",
        RuntimeWarning,
    )

Path("data").mkdir(parents=True, exist_ok=True)
