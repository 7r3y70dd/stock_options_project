import os
from enum import Enum
from typing import Optional


class Environment(str, Enum):
    """Environment enumeration for configuration."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class Config:
    """Application configuration class."""

    def __init__(self):
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
        self.DEBUG = self.ENVIRONMENT == "development"
        self.TESTING = self.ENVIRONMENT == "testing"
        self.DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql://user:password@db:5432/options_tracker"
        )
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.API_KEY = os.getenv("API_KEY", "")
        self.SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == Environment.DEVELOPMENT.value

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == Environment.PRODUCTION.value

    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.ENVIRONMENT == Environment.TESTING.value or self.TESTING

    def get_database_url(self) -> str:
        """Get the database URL for the current environment."""
        if self.is_test():
            return "sqlite:///:memory:"
        return self.DATABASE_URL

    def get_log_level(self) -> str:
        """Get the log level for the current environment."""
        return self.LOG_LEVEL


# Global config singleton instance
config = Config()


def get_config() -> Config:
    """Get the global config instance."""
    return config
