"""Application configuration management.

Handles environment-based configuration for different deployment scenarios.
"""

import os
from typing import Optional
from functools import lru_cache


class Config:
    """Base configuration class."""

    # Environment
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    TESTING: bool = os.getenv("TESTING", "False").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./test.db" if os.getenv("TESTING") else "sqlite:///./app.db",
    )

    # API Keys
    ALPHAVANTAGE_API_KEY: Optional[str] = os.getenv("ALPHAVANTAGE_API_KEY")
    FINNHUB_API_KEY: Optional[str] = os.getenv("FINNHUB_API_KEY")

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
    )

    # Application
    APP_NAME: str = "Stock Options Trading"
    APP_VERSION: str = "0.1.0"

    def is_test(self) -> bool:
        """Check if the application is running in test mode.

        Returns:
            bool: True if TESTING environment variable is set to true, False otherwise.
        """
        return self.TESTING or os.getenv("TESTING", "").lower() == "true"


@lru_cache()
def get_config() -> Config:
    """Get the application configuration.

    Returns:
        Config: The application configuration instance.
    """
    return Config()


config = get_config()
