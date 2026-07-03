"""Application configuration."""

import os
from typing import Optional


class Config:
    """Application configuration class."""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./test.db"
    )

    # API Keys
    # Support both ALPHAVANTAGE_* and ALPHA_VANTAGE_* spellings because
    # different generated modules currently use different names.
    ALPHAVANTAGE_API_KEY: Optional[str] = os.getenv(
        "ALPHAVANTAGE_API_KEY",
        os.getenv("ALPHA_VANTAGE_API_KEY", "")
    )
    ALPHA_VANTAGE_API_KEY: Optional[str] = ALPHAVANTAGE_API_KEY

    ALPHAVANTAGE_RATE_LIMIT_CALLS_PER_MINUTE: int = int(
        os.getenv("ALPHAVANTAGE_RATE_LIMIT_CALLS_PER_MINUTE", "5")
    )
    ALPHAVANTAGE_CACHE_TTL_SECONDS: int = int(
        os.getenv("ALPHAVANTAGE_CACHE_TTL_SECONDS", "300")
    )

    FINNHUB_API_KEY: Optional[str] = os.getenv("FINNHUB_API_KEY", "")
    POLYGON_API_KEY: Optional[str] = os.getenv("POLYGON_API_KEY", "")
    NEWS_API_KEY: Optional[str] = os.getenv("NEWS_API_KEY", "")
    DATA_PROVIDER: str = os.getenv("DATA_PROVIDER", "mock")
    YFINANCE_ENABLED: bool = os.getenv("YFINANCE_ENABLED", "true").lower() == "true"

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Celery
    CELERY_BROKER_URL: str = os.getenv(
        "CELERY_BROKER_URL",
        "redis://localhost:6379/0"
    )
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND",
        "redis://localhost:6379/0"
    )

    # Testing
    TESTING: bool = os.getenv("TESTING", "false").lower() == "true"

    @classmethod
    def is_test(cls) -> bool:
        """Check if running in test mode.
        
        Returns:
            bool: True if TESTING environment variable is set to true.
        """
        return cls.TESTING

    def get_database_url(self) -> str:
        """Return the configured database URL."""
        return self.DATABASE_URL

    def is_development(self) -> bool:
        """Return True when the app is running in development mode."""
        return self.ENVIRONMENT.lower() in {"dev", "development", "local"}

# Shared application configuration singleton
config = Config()

def get_config() -> Config:
    """Return the shared application configuration."""
    return config

# ---------------------------------------------------------------------------
# Compatibility shims for generated import/API drift.
# TODO: replace with one canonical config API after tests collect.
# ---------------------------------------------------------------------------
try:
    Environment
except NameError:
    from enum import Enum as _Enum

    class Environment(str, _Enum):
        DEVELOPMENT = "development"
        DEV = "dev"
        TEST = "test"
        TESTING = "testing"
        PRODUCTION = "production"
        PROD = "prod"


try:
    config
except NameError:
    config = Config()


try:
    get_config
except NameError:
    def get_config() -> Config:
        return config


if "Config" in globals() and not hasattr(Config, "is_test"):
    def _config_is_test(self) -> bool:
        import os
        env = getattr(
            self,
            "ENVIRONMENT",
            getattr(self, "environment", os.getenv("ENVIRONMENT", "development")),
        )
        if hasattr(env, "value"):
            env = env.value
        return str(env).lower() in {"test", "testing"}

    Config.is_test = _config_is_test


if "Config" in globals() and not hasattr(Config, "is_development"):
    def _config_is_development(self) -> bool:
        import os
        env = getattr(
            self,
            "ENVIRONMENT",
            getattr(self, "environment", os.getenv("ENVIRONMENT", "development")),
        )
        if hasattr(env, "value"):
            env = env.value
        return str(env).lower() in {"dev", "development", "local"}

    Config.is_development = _config_is_development

