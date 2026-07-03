"""Application configuration management."""

from enum import Enum
from typing import Optional
from functools import lru_cache
import os


class Environment(str, Enum):
    """Environment types."""
    TEST = "test"
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Config:
    """Application configuration."""

    def __init__(self, environment: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            environment: Environment type (test, development, production).
                        If None, reads from ENVIRONMENT env var, defaults to development.
        """
        if environment is None:
            environment = os.getenv("ENVIRONMENT", "development")
        
        try:
            self.environment = Environment(environment.lower())
        except (ValueError, AttributeError):
            self.environment = Environment.DEVELOPMENT

    def is_test(self) -> bool:
        """Check if running in test environment.
        
        Returns:
            True if environment is test, False otherwise.
        """
        return self.environment == Environment.TEST

    def is_development(self) -> bool:
        """Check if running in development environment.
        
        Returns:
            True if environment is development, False otherwise.
        """
        return self.environment == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """Check if running in production environment.
        
        Returns:
            True if environment is production, False otherwise.
        """
        return self.environment == Environment.PRODUCTION

    def get_database_url(self) -> str:
        """Get database URL based on environment.
        
        Returns:
            Database connection URL.
        """
        if self.is_test():
            return os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
        elif self.is_production():
            return os.getenv("DATABASE_URL", "postgresql://localhost/stock_options_prod")
        else:
            return os.getenv("DATABASE_URL", "sqlite:///./stock_options.db")

    def get_log_level(self) -> str:
        """Get log level based on environment.
        
        Returns:
            Log level string.
        """
        if self.is_production():
            return "INFO"
        elif self.is_test():
            return "DEBUG"
        else:
            return "DEBUG"


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get or create the global config instance.
    
    Returns:
        Config instance.
    """
    return Config()
