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
    ALPHA_VANTAGE_API_KEY: Optional[str] = os.getenv("ALPHA_VANTAGE_API_KEY")
    FINNHUB_API_KEY: Optional[str] = os.getenv("FINNHUB_API_KEY")

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
