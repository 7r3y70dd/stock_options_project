"""Application configuration management.

Handles environment variables and configuration for the application.
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration."""

    # Database
    database_url: str
    
    # API Configuration
    api_base_url: str  # Base URL for API (e.g., 'http://localhost:8000/api')
    dashboard_prefix: str  # Dashboard route prefix (e.g., '/api/dashboard')
    
    # Frontend Configuration
    demo_user_id: int  # Demo user ID for local development
    
    # External APIs
    alphavantage_api_key: Optional[str] = None
    polygon_api_key: Optional[str] = None
    news_api_key: Optional[str] = None
    finnhub_api_key: Optional[str] = None
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # Environment
    environment: str = "development"
    debug: bool = False


def get_config() -> Config:
    """Get application configuration from environment variables.
    
    Returns:
        Config instance with values from environment
    """
    return Config(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql://user:password@localhost:5432/options_tracker",
        ),
        api_base_url=os.getenv(
            "API_BASE_URL",
            "http://localhost:8000/api",
        ),
        dashboard_prefix=os.getenv(
            "DASHBOARD_PREFIX",
            "/api/dashboard",
        ),
        demo_user_id=int(os.getenv("DEMO_USER_ID", "1")),
        alphavantage_api_key=os.getenv("ALPHAVANTAGE_API_KEY"),
        polygon_api_key=os.getenv("POLYGON_API_KEY"),
        news_api_key=os.getenv("NEWS_API_KEY"),
        finnhub_api_key=os.getenv("FINNHUB_API_KEY"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        celery_broker_url=os.getenv(
            "CELERY_BROKER_URL", "redis://localhost:6379/0"
        ),
        celery_result_backend=os.getenv(
            "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
        ),
        environment=os.getenv("ENVIRONMENT", "development"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
    )
