"""Configuration management for the parser Flask service."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict


@dataclass
class BrowserUseSettings:
    """Runtime settings for the browser-use client."""

    headless: bool = True
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: str | None = None
    profile_id: str | None = None
    use_cloud_browser: bool = False
    start_url: str | None = None
    extra_env: Dict[str, str] = field(default_factory=dict)


@dataclass
class QueueSettings:
    """Settings for Celery/Redis integration."""

    broker_url: str
    result_backend: str
    redis_url: str


@dataclass
class AppSettings:
    """Structured application settings."""

    env: str
    openai_api_key: str | None
    google_api_key: str | None
    default_llm_provider: str
    browser_use: BrowserUseSettings
    queue: QueueSettings


def _str_to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _browser_use_env() -> Dict[str, str]:
    prefix = "BROWSER_USE_ENV_"
    return {
        key[len(prefix) :]: value
        for key, value in os.environ.items()
        if key.startswith(prefix)
    }


@lru_cache(maxsize=1)
def load_settings() -> AppSettings:
    env = os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "development"
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    broker_url = os.getenv("CELERY_BROKER_URL", redis_url)
    result_backend = os.getenv("CELERY_RESULT_BACKEND", redis_url)

    return AppSettings(
        env=env,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        default_llm_provider=os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
        browser_use=BrowserUseSettings(
            headless=_str_to_bool(os.getenv("BROWSER_USE_HEADLESS"), True),
            viewport_width=int(os.getenv("BROWSER_USE_VIEWPORT_WIDTH", "1280")),
            viewport_height=int(os.getenv("BROWSER_USE_VIEWPORT_HEIGHT", "720")),
            user_agent=os.getenv("BROWSER_USE_USER_AGENT"),
            profile_id=os.getenv("BROWSER_USE_PROFILE_ID"),
            use_cloud_browser=_str_to_bool(
                os.getenv("BROWSER_USE_USE_CLOUD_BROWSER"), False
            ),
            start_url=os.getenv("BROWSER_USE_START_URL"),
            extra_env=_browser_use_env(),
        ),
        queue=QueueSettings(
            broker_url=broker_url,
            result_backend=result_backend,
            redis_url=redis_url,
        ),
    )


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "parser-dev-secret")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DEBUG = False
    TESTING = False
    SETTINGS = load_settings()


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    pass


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = True


def get_config(name: str | None = None) -> type[BaseConfig]:
    """Return the configuration class for the provided environment name."""

    config_name = (name or os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "development").lower()
    mapping: Dict[str, type[BaseConfig]] = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }
    return mapping.get(config_name, DevelopmentConfig)


__all__ = [
    "AppSettings",
    "BrowserUseSettings",
    "QueueSettings",
    "get_config",
    "load_settings",
]
