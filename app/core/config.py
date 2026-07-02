"""Application configuration management.

Supports dev, test, and prod environments via environment variables.
"""

import os
from enum import Enum
from typing import Optional, Dict


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

    # Sentiment Analysis Configuration
    SENTIMENT_ANALYSIS_ENABLED: bool = os.getenv("SENTIMENT_ANALYSIS_ENABLED", "True").lower() == "true"
    SENTIMENT_MODEL: str = os.getenv("SENTIMENT_MODEL", "finbert")  # "finbert" or "distilbert"
    SENTIMENT_BATCH_SIZE: int = int(os.getenv("SENTIMENT_BATCH_SIZE", "32"))
    SENTIMENT_USE_GPU: bool = os.getenv("SENTIMENT_USE_GPU", "False").lower() == "true"

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

    # Kill Switch Configuration
    # Global emergency kill switch to disable new orders
    KILL_SWITCH_ENABLED: bool = os.getenv("KILL_SWITCH_ENABLED", "False").lower() == "true"
    KILL_SWITCH_CLOSE_POSITIONS: bool = os.getenv("KILL_SWITCH_CLOSE_POSITIONS", "False").lower() == "true"

    # Paper Trading Comparison Configuration
    PAPER_TRADING_COMPARISON_ENABLED: bool = os.getenv("PAPER_TRADING_COMPARISON_ENABLED", "True").lower() == "true"
    PAPER_TRADING_FILL_RATE_THRESHOLD: float = float(os.getenv("PAPER_TRADING_FILL_RATE_THRESHOLD", "0.95"))
    PAPER_TRADING_SLIPPAGE_THRESHOLD: float = float(os.getenv("PAPER_TRADING_SLIPPAGE_THRESHOLD", "0.01"))
    PAPER_TRADING_PNL_VARIANCE_THRESHOLD: float = float(os.getenv("PAPER_TRADING_PNL_VARIANCE_THRESHOLD", "0.10"))
    PAPER_TRADING_DISABLE_ON_POOR_PERFORMANCE: bool = os.getenv("PAPER_TRADING_DISABLE_ON_POOR_PERFORMANCE", "True").lower() == "true"

    # Signal Scoring Thresholds
    # Minimum score threshold for recommending a trade (0-100 scale)
    MIN_SIGNAL_SCORE: float = float(os.getenv("MIN_SIGNAL_SCORE", "50.0"))
    
    # Minimum liquidity score threshold (0-100 scale)
    MIN_LIQUIDITY_SCORE: float = float(os.getenv("MIN_LIQUIDITY_SCORE", "40.0"))
    
    # Minimum liquidity score by risk level (can override MIN_LIQUIDITY_SCORE)
    MIN_LIQUIDITY_SCORE_LOW: float = float(os.getenv("MIN_LIQUIDITY_SCORE_LOW", "60.0"))
    MIN_LIQUIDITY_SCORE_MEDIUM: float = float(os.getenv("MIN_LIQUIDITY_SCORE_MEDIUM", "40.0"))
    MIN_LIQUIDITY_SCORE_HIGH: float = float(os.getenv("MIN_LIQUIDITY_SCORE_HIGH", "30.0"))

    # Risk-Adjusted Scoring Weights
    # Each risk level has different weight priorities
    # LOW: favors liquidity, defined risk, lower max loss
    # MEDIUM: balanced approach
    # HIGH: allows volatility and lower probability if payoff is larger
    SCORING_WEIGHTS_LOW: Dict[str, float] = {
        "liquidity": 0.30,      # Higher weight for liquidity
        "reward_risk": 0.15,    # Lower weight for reward/risk
        "probability": 0.25,    # High weight for probability
        "volatility": 0.05,     # Lower weight for volatility
        "sentiment": 0.10,      # Moderate weight for sentiment
        "trend": 0.10,          # Moderate weight for trend
        "event_risk": 0.05,     # Lower weight for event risk
    }
    
    SCORING_WEIGHTS_MEDIUM: Dict[str, float] = {
        "liquidity": 0.20,      # Standard weight
        "reward_risk": 0.20,    # Standard weight
        "probability": 0.20,    # Standard weight
        "volatility": 0.10,     # Standard weight
        "sentiment": 0.12,      # Standard weight
        "trend": 0.13,          # Standard weight
        "event_risk": 0.05,     # Standard weight
    }
    
    SCORING_WEIGHTS_HIGH: Dict[str, float] = {
        "liquidity": 0.10,      # Lower weight for liquidity
        "reward_risk": 0.25,    # Higher weight for reward/risk
        "probability": 0.15,    # Lower weight for probability
        "volatility": 0.15,     # Higher weight for volatility
        "sentiment": 0.15,      # Higher weight for sentiment
        "trend": 0.15,          # Higher weight for trend
        "event_risk": 0.05,     # Lower weight for event risk
    }

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

    # Cash-Secured Put Strategy Configuration
    CASH_SECURED_PUT_MIN_CASH: float = float(os.getenv("CASH_SECURED_PUT_MIN_CASH", "10000.0"))
    CASH_SECURED_PUT_OTM_THRESHOLD: float = float(os.getenv("CASH_SECURED_PUT_OTM_THRESHOLD", "0.02"))
    CASH_SECURED_PUT_MAX_OTM_THRESHOLD: float = float(os.getenv("CASH_SECURED_PUT_MAX_OTM_THRESHOLD", "0.15"))
    CASH_SECURED_PUT_MIN_DTE: int = int(os.getenv("CASH_SECURED_PUT_MIN_DTE", "7"))
    CASH_SECURED_PUT_MAX_DTE: int = int(os.getenv("CASH_SECURED_PUT_MAX_DTE", "60"))
    CASH_SECURED_PUT_MIN_VOLUME: int = int(os.getenv("CASH_SECURED_PUT_MIN_VOLUME", "10"))
    CASH_SECURED_PUT_MIN_OPEN_INTEREST: int = int(os.getenv("CASH_SECURED_PUT_MIN_OPEN_INTEREST", "20"))
    CASH_SECURED_PUT_MAX_SPREAD_PCT: float = float(os.getenv("CASH_SECURED_PUT_MAX_SPREAD_PCT", "0.05"))

    # Debit Spread Strategy Configuration
    DEBIT_SPREAD_MIN_DTE: int = int(os.getenv("DEBIT_SPREAD_MIN_DTE", "7"))
    DEBIT_SPREAD_MAX_DTE: int = int(os.getenv("DEBIT_SPREAD_MAX_DTE", "60"))
    DEBIT_SPREAD_MIN_VOLUME: int = int(os.getenv("DEBIT_SPREAD_MIN_VOLUME", "10"))
    DEBIT_SPREAD_MIN_OPEN_INTEREST: int = int(os.getenv("DEBIT_SPREAD_MIN_OPEN_INTEREST", "20"))
    DEBIT_SPREAD_MIN_LIQUIDITY_SCORE: float = float(os.getenv("DEBIT_SPREAD_MIN_LIQUIDITY_SCORE", "50.0"))
    DEBIT_SPREAD_LONG_OTM_THRESHOLD: float = float(os.getenv("DEBIT_SPREAD_LONG_OTM_THRESHOLD", "0.05"))
    DEBIT_SPREAD_SHORT_OTM_THRESHOLD: float = float(os.getenv("DEBIT_SPREAD_SHORT_OTM_THRESHOLD", "0.15"))
    DEBIT_SPREAD_MAX_DEBIT: float = float(os.getenv("DEBIT_SPREAD_MAX_DEBIT", "500.0"))
    DEBIT_SPREAD_MIN_REWARD_RISK_RATIO: float = float(os.getenv("DEBIT_SPREAD_MIN_REWARD_RISK_RATIO", "0.5"))

    # Credit Spread Strategy Configuration
    CREDIT_SPREAD_MIN_DTE: int = int(os.getenv("CREDIT_SPREAD_MIN_DTE", "7"))
    CREDIT_SPREAD_MAX_DTE: int = int(os.getenv("CREDIT_SPREAD_MAX_DTE", "60"))
    CREDIT_SPREAD_MIN_VOLUME: int = int(os.getenv("CREDIT_SPREAD_MIN_VOLUME", "10"))
    CREDIT_SPREAD_MIN_OPEN_INTEREST: int = int(os.getenv("CREDIT_SPREAD_MIN_OPEN_INTEREST", "20"))
    CREDIT_SPREAD_MIN_LIQUIDITY_SCORE: float = float(os.getenv("CREDIT_SPREAD_MIN_LIQUIDITY_SCORE", "50.0"))
    CREDIT_SPREAD_SHORT_OTM_THRESHOLD: float = float(os.getenv("CREDIT_SPREAD_SHORT_OTM_THRESHOLD", "0.05"))
    CREDIT_SPREAD_LONG_OTM_THRESHOLD: float = float(os.getenv("CREDIT_SPREAD_LONG_OTM_THRESHOLD", "0.15"))
    CREDIT_SPREAD_MAX_WIDTH: float = float(os.getenv("CREDIT_SPREAD_MAX_WIDTH", "500.0"))
    CREDIT_SPREAD_MIN_CREDIT: float = float(os.getenv("CREDIT_SPREAD_MIN_CREDIT", "0.10"))
    CREDIT_SPREAD_MIN_RETURN_ON_RISK: float = float(os.getenv("CREDIT_SPREAD_MIN_RETURN_ON_RISK", "0.20"))

    # Long Call/Put Strategy Configuration
    LONG_CALL_PUT_MIN_DTE: int = int(os.getenv("LONG_CALL_PUT_MIN_DTE", "7"))
    LONG_CALL_PUT_MAX_DTE: int = int(os.getenv("LONG_CALL_PUT_MAX_DTE", "60"))
    LONG_CALL_PUT_MIN_VOLUME: int = int(os.getenv("LONG_CALL_PUT_MIN_VOLUME", "10"))
    LONG_CALL_PUT_MIN_OPEN_INTEREST: int = int(os.getenv("LONG_CALL_PUT_MIN_OPEN_INTEREST", "20"))
    LONG_CALL_PUT_MIN_LIQUIDITY_SCORE: float = float(os.getenv("LONG_CALL_PUT_MIN_LIQUIDITY_SCORE", "50.0"))
    LONG_CALL_PUT_MIN_DELTA: float = float(os.getenv("LONG_CALL_PUT_MIN_DELTA", "0.30"))
    LONG_CALL_PUT_MAX_DELTA: float = float(os.getenv("LONG_CALL_PUT_MAX_DELTA", "0.90"))
    LONG_CALL_PUT_MAX_PREMIUM: float = float(os.getenv("LONG_CALL_PUT_MAX_PREMIUM", "500.0"))


# Global config singleton instance
config = Config()
