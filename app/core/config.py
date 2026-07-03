"""Application configuration management."""

from enum import Enum
from typing import Optional
from pydantic import BaseSettings


class Environment(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Config(BaseSettings):
    """Application configuration."""
    
    # Environment
    environment: Environment = Environment.DEVELOPMENT
    
    # Database
    database_url: str = "sqlite:///./test.db"
    
    # API
    api_title: str = "Stock Options API"
    api_version: str = "1.0.0"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # External APIs
    alpha_vantage_api_key: Optional[str] = None
    finnhub_api_key: Optional[str] = None
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def is_test(self) -> bool:
        """Check if running in test environment."""
        return self.environment == Environment.TESTING
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT
