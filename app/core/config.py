"""Application configuration management."""
import os
from enum import Enum
from typing import Optional


class Environment(str, Enum):
    """Application environment."""

    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class Config:
    """Application configuration."""

    # Environment
    ENVIRONMENT: Environment = Environment(os.getenv("ENVIRONMENT", "dev"))
    DEBUG: bool = ENVIRONMENT == Environment.DEV

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RELOAD: bool = DEBUG

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://user:password@localhost:5432/stock_options"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True

    # Job scheduling intervals (in seconds)
    DATA_REFRESH_INTERVAL: int = int(os.getenv("DATA_REFRESH_INTERVAL", "300"))  # 5 minutes
    SIGNAL_GENERATION_INTERVAL: int = int(
        os.getenv("SIGNAL_GENERATION_INTERVAL", "600")
    )  # 10 minutes
    TRADE_MONITORING_INTERVAL: int = int(
        os.getenv("TRADE_MONITORING_INTERVAL", "60")
    )  # 1 minute

    # Data providers
    ALPHA_VANTAGE_API_KEY: Optional[str] = os.getenv("ALPHA_VANTAGE_API_KEY")
    FINNHUB_API_KEY: Optional[str] = os.getenv("FINNHUB_API_KEY")
    YFINANCE_ENABLED: bool = os.getenv("YFINANCE_ENABLED", "true").lower() == "true"

    # Frontend configuration
    FRONTEND_API_BASE_URL: str = os.getenv(
        "FRONTEND_API_BASE_URL", "http://localhost:8000"
    )
    FRONTEND_DASHBOARD_PREFIX: str = os.getenv(
        "FRONTEND_DASHBOARD_PREFIX", "/api/api/dashboard"
    )
    DEMO_USER_ID: str = os.getenv("DEMO_USER_ID", "1")

    # CORS
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"
    ).split(",")


# Create a singleton config instance
config = Config()
