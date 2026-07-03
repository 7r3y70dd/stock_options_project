import os
from typing import Optional


class Config:
    """Application configuration."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.database_url = os.getenv(
            "DATABASE_URL", "sqlite:///./test.db"
        )
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.celery_broker = os.getenv("CELERY_BROKER", "redis://localhost:6379/0")
        self.celery_backend = os.getenv("CELERY_BACKEND", "redis://localhost:6379/1")
        self.api_key = os.getenv("API_KEY", "")
        self.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

    def is_test(self) -> bool:
        """Check if running in test mode.
        
        Returns:
            bool: True if running in test environment, False otherwise.
        """
        return self.environment == "test" or os.getenv("PYTEST_CURRENT_TEST") is not None

    def is_production(self) -> bool:
        """Check if running in production mode.
        
        Returns:
            bool: True if running in production environment, False otherwise.
        """
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development mode.
        
        Returns:
            bool: True if running in development environment, False otherwise.
        """
        return self.environment == "development"


config = Config()
