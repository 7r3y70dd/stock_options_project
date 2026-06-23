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

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 30 * 60  # 30 minutes
    CELERY_TASK_SOFT_TIME_LIMIT: int = 25 * 60  # 25 minutes

    # API Keys
    ALPHAVANTAGE_API_KEY: Optional[str] = os.getenv("ALPHAVANTAGE_API_KEY")
    POLYGON_API_KEY: Optional[str] = os.getenv("POLYGON_API_KEY")
    NEWS_API_KEY: Optional[str] = os.getenv("NEWS_API_KEY")
    FINNHUB_API_KEY: Optional[str] = os.getenv("FINNHUB_API_KEY")

    # Data Provider Configuration
    DATA_PROVIDER: str = os.getenv("DATA_PROVIDER", "mock")  # "mock", "alphavantage", "yfinance", etc.
    ALPHAVANTAGE_RATE_LIMIT_CALLS_PER_MINUTE: int = int(
        os.getenv("ALPHAVANTAGE_RATE_LIMIT_CALLS_PER_MINUTE", "5")
    )
    ALPHAVANTAGE_CACHE_TTL_SECONDS: int = int(
        os.getenv("ALPHAVANTAGE_CACHE_TTL_SECONDS", "300")
    )
    
    # yfinance Configuration
    YFINANCE_ENABLED: bool = os.getenv("YFINANCE_ENABLED", "True").lower() == "true"
    # Disable yfinance in production by default (can be overridden)
    if ENVIRONMENT == Environment.PROD:
        YFINANCE_ENABLED = os.getenv("YFINANCE_ENABLED", "False").lower() == "true"

    # Finnhub Configuration
    FINNHUB_ENABLED: bool = os.getenv("FINNHUB_ENABLED", "True").lower() == "true"
    FINNHUB_RATE_LIMIT_CALLS_PER_SECOND: int = int(
        os.getenv("FINNHUB_RATE_LIMIT_CALLS_PER_SECOND", "1")
    )
    FINNHUB_CACHE_TTL_SECONDS: int = int(
        os.getenv("FINNHUB_CACHE_TTL_SECONDS", "300")
    )

    # Paper Trading & Broker Configuration
    PAPER_TRADING_ENABLED: bool = os.getenv("PAPER_TRADING_ENABLED", "True").lower() == "true"
    LIVE_TRADING_ENABLED: bool = os.getenv("LIVE_TRADING_ENABLED", "False").lower() == "true"
    INITIAL_PORTFOLIO_VALUE: float = float(os.getenv("INITIAL_PORTFOLIO_VALUE", "100000"))
    
    # Broker Provider Configuration
    BROKER_PROVIDER: str = os.getenv("BROKER_PROVIDER", "paper")  # "paper", "alpaca", "tradier", etc.
    BROKER_PAPER_INITIAL_CASH: float = float(os.getenv("BROKER_PAPER_INITIAL_CASH", "100000"))
    BROKER_ENABLE_LOGGING: bool = os.getenv("BROKER_ENABLE_LOGGING", "True").lower() == "true"
    
    # Live Trading Safeguards
    # In production, live trading is disabled by default and requires explicit user approval
    if ENVIRONMENT == Environment.PROD:
        LIVE_TRADING_ENABLED = os.getenv("LIVE_TRADING_ENABLED", "False").lower() == "true"
        PAPER_TRADING_ENABLED = os.getenv("PAPER_TRADING_ENABLED", "True").lower() == "true"

    # Risk Management
    DEFAULT_RISK_LEVEL: str = os.getenv("DEFAULT_RISK_LEVEL", "medium")
    MAX_DAILY_LOSS_PCT: float = float(os.getenv("MAX_DAILY_LOSS_PCT", "5.0"))

    # Strategy Configuration
    ENABLED_STRATEGIES: list = os.getenv("ENABLED_STRATEGIES", "").split(",") if os.getenv("ENABLED_STRATEGIES") else []
    DISABLED_STRATEGIES: list = os.getenv("DISABLED_STRATEGIES", "").split(",") if os.getenv("DISABLED_STRATEGIES") else []

    # Covered Call Strategy Configuration
    COVERED_CALL_MIN_SHARES: int = int(os.getenv("COVERED_CALL_MIN_SHARES", "100"))
    COVERED_CALL_OTM_THRESHOLD: float = float(os.getenv("COVERED_CALL_OTM_THRESHOLD", "0.02"))
    COVERED_CALL_MAX_OTM_THRESHOLD: float = float(os.getenv("COVERED_CALL_MAX_OTM_THRESHOLD", "0.15"))
    COVERED_CALL_MIN_DTE: int = int(os.getenv("COVERED_CALL_MIN_DTE", "7"))
    COVERED_CALL_MAX_DTE: int = int(os.getenv("COVERED_CALL_MAX_DTE", "60"))
    COVERED_CALL_MIN_VOLUME: int = int(os.getenv("COVERED_CALL_MIN_VOLUME", "10"))
    COVERED_CALL_MIN_OPEN_INTEREST: int = int(os.getenv("COVERED_CALL_MIN_OPEN_INTEREST", "20"))
    COVERED_CALL_MAX_SPREAD_PCT: float = float(os.getenv("COVERED_CALL_MAX_SPREAD_PCT", "0.05"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Job Scheduling
    DATA_REFRESH_INTERVAL_SECONDS: int = int(os.getenv("DATA_REFRESH_INTERVAL_SECONDS", "300"))  # 5 minutes
    SIGNAL_GENERATION_INTERVAL_SECONDS: int = int(os.getenv("SIGNAL_GENERATION_INTERVAL_SECONDS", "600"))  # 10 minutes
    TRADE_MONITORING_INTERVAL_SECONDS: int = int(os.getenv("TRADE_MONITORING_INTERVAL_SECONDS", "60"))  # 1 minute
    NEWS_FETCH_INTERVAL_SECONDS: int = int(os.getenv("NEWS_FETCH_INTERVAL_SECONDS", "1800"))  # 30 minutes

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

    @classmethod
    def is_live_trading_enabled(cls) -> bool:
        """Check if live trading is enabled.
        
        Returns:
            True only if both LIVE_TRADING_ENABLED is True and PAPER_TRADING_ENABLED is False
        """
        return cls.LIVE_TRADING_ENABLED and not cls.PAPER_TRADING_ENABLED

    @classmethod
    def is_paper_trading_enabled(cls) -> bool:
        """Check if paper trading is enabled.
        
        Returns:
            True if PAPER_TRADING_ENABLED is True
        """
        return cls.PAPER_TRADING_ENABLED

    @classmethod
    def is_strategy_enabled(cls, strategy_name: str) -> bool:
        """Check if a strategy is enabled.
        
        Args:
            strategy_name: Name of strategy to check
            
        Returns:
            True if strategy is enabled (not in disabled list)
        """
        # If explicitly disabled, return False
        if strategy_name in cls.DISABLED_STRATEGIES:
            return False
        # If enabled list is specified and strategy is in it, return True
        if cls.ENABLED_STRATEGIES and strategy_name in cls.ENABLED_STRATEGIES:
            return True
        # If enabled list is empty, all strategies are enabled by default
        return not cls.ENABLED_STRATEGIES


# Export singleton config instance
config = Config()
