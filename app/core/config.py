"""Application configuration management.

Supports dev, test, and prod environments via environment variables.
"""

import os
from enum import Enum
from typing import Optional


class Environment(str, Enum):
    """Application environment."""

    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class Config:
    """Base configuration."""

    # Environment
    ENVIRONMENT: Environment = Environment(os.getenv("ENVIRONMENT", "dev"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # App
    APP_NAME: str = "Options Tracker"
    APP_VERSION: str = "0.1.0"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALLOWED_HOSTS: list = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://options_user:options_password@localhost:5432/options_tracker",
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # API Keys
    ALPHAVANTAGE_API_KEY: Optional[str] = os.getenv("ALPHAVANTAGE_API_KEY")
    POLYGON_API_KEY: Optional[str] = os.getenv("POLYGON_API_KEY")
    NEWS_API_KEY: Optional[str] = os.getenv("NEWS_API_KEY")

    # Paper Trading
    PAPER_TRADING_ENABLED: bool = os.getenv("PAPER_TRADING_ENABLED", "True").lower() == "true"
    LIVE_TRADING_ENABLED: bool = os.getenv("LIVE_TRADING_ENABLED", "False").lower() == "true"
    INITIAL_PORTFOLIO_VALUE: float = float(os.getenv("INITIAL_PORTFOLIO_VALUE", "100000"))

    # Risk Management
    DEFAULT_RISK_LEVEL: str = os.getenv("DEFAULT_RISK_LEVEL", "medium")
    MAX_DAILY_LOSS_PCT: float = float(os.getenv("MAX_DAILY_LOSS_PCT", "5.0"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def is_dev(cls) -> bool:
        """Check if running in development mode."""
        return cls.ENVIRONMENT == Environment.DEV

    @classmethod
    def is_test(cls) -> bool:
        """Check if running in test mode."""
        return cls.ENVIRONMENT == Environment.TEST

    @classmethod
    def is_prod(cls) -> bool:
        """Check if running in production mode."""
        return cls.ENVIRONMENT == Environment.PROD


# Export singleton config instance
config = Config()
