"""Application configuration management.

Supports dev/test/prod environments via environment variables.
Configuration is loaded once at startup and made available throughout the app.
"""

from enum import Enum
from typing import Optional
import os
from functools import lru_cache


class Environment(str, Enum):
    """Application environment."""
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class Config:
    """Application configuration.
    
    Loads configuration from environment variables with sensible defaults.
    Supports dev/test/prod environments.
    """

    def __init__(self):
        """Initialize configuration from environment variables."""
        # Environment
        self.environment = Environment(
            os.getenv("APP_ENV", "dev")
        )
        self.debug = self.environment == Environment.DEV

        # Server
        self.host = os.getenv("APP_HOST", "0.0.0.0")
        self.port = int(os.getenv("APP_PORT", "8000"))
        self.reload = self.debug

        # Database
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://user:password@localhost:5432/stock_options"
        )

        # Redis
        self.redis_url = os.getenv(
            "REDIS_URL",
            "redis://localhost:6379/0"
        )

        # Celery
        self.celery_broker_url = os.getenv(
            "CELERY_BROKER_URL",
            self.redis_url
        )
        self.celery_result_backend = os.getenv(
            "CELERY_RESULT_BACKEND",
            self.redis_url
        )
        self.celery_task_serializer = "json"
        self.celery_accept_content = ["json"]
        self.celery_result_serializer = "json"
        self.celery_timezone = "UTC"
        self.celery_enable_utc = True

        # Job scheduling intervals (in seconds)
        self.data_refresh_interval = int(
            os.getenv("DATA_REFRESH_INTERVAL", "300")  # 5 minutes
        )
        self.signal_generation_interval = int(
            os.getenv("SIGNAL_GENERATION_INTERVAL", "600")  # 10 minutes
        )
        self.trade_monitoring_interval = int(
            os.getenv("TRADE_MONITORING_INTERVAL", "60")  # 1 minute
        )

        # CORS
        self.cors_origins = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:8000"
        ).split(",")

        # Frontend Configuration
        self.frontend_api_base_url = os.getenv(
            "FRONTEND_API_BASE_URL",
            "http://localhost:8000"
        )
        self.frontend_dashboard_prefix = os.getenv(
            "FRONTEND_DASHBOARD_PREFIX",
            "/api/api/dashboard"
        )
        self.demo_user_id = int(
            os.getenv("DEMO_USER_ID", "1")
        )

        # Data Providers
        self.alpha_vantage_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.finnhub_api_key = os.getenv("FINNHUB_API_KEY")
        self.yfinance_enabled = os.getenv("YFINANCE_ENABLED", "true").lower() == "true"

        # Broker
        self.broker_type = os.getenv("BROKER_TYPE", "paper")
        self.alpaca_api_key = os.getenv("ALPACA_API_KEY")
        self.alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY")
        self.alpaca_base_url = os.getenv(
            "ALPACA_BASE_URL",
            "https://paper-api.alpaca.markets"
        )

        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

    def is_dev(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEV

    def is_test(self) -> bool:
        """Check if running in test environment."""
        return self.environment == Environment.TEST

    def is_prod(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PROD


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get or create the global config instance.
    
    Uses lru_cache to ensure only one Config instance is created.
    
    Returns:
        Global Config instance
    """
    return Config()


# Create global config instance for backward compatibility
config = get_config()
