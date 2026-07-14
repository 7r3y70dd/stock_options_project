"""Application configuration.

Manages environment variables and configuration settings for the application.
"""

import os
from typing import Optional


class Config:
    """Application configuration."""
    
    # Database
    DATABASE_URL: str = os.getenv(
        'DATABASE_URL',
        'sqlite:///./test.db'
    )
    
    # API Configuration
    API_BASE_URL: str = os.getenv(
        'API_BASE_URL',
        'http://localhost:8000'
    )
    
    DASHBOARD_PREFIX: str = os.getenv(
        'DASHBOARD_PREFIX',
        '/api/api/dashboard'
    )
    
    # Frontend Configuration
    DEMO_USER_ID: int = int(os.getenv('DEMO_USER_ID', '1'))
    
    # Data Provider
    DATA_PROVIDER: str = os.getenv('DATA_PROVIDER', 'mock')
    
    # Broker Provider
    BROKER_PROVIDER: str = os.getenv('BROKER_PROVIDER', 'paper')
    
    # Celery Configuration
    CELERY_BROKER_URL: str = os.getenv(
        'CELERY_BROKER_URL',
        'redis://localhost:6379/0'
    )
    
    CELERY_RESULT_BACKEND: str = os.getenv(
        'CELERY_RESULT_BACKEND',
        'redis://localhost:6379/0'
    )
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # Feature Flags
    PAPER_TRADING_ENABLED: bool = os.getenv('PAPER_TRADING_ENABLED', 'true').lower() == 'true'
    LIVE_TRADING_ENABLED: bool = os.getenv('LIVE_TRADING_ENABLED', 'false').lower() == 'true'
    
    @classmethod
    def get_api_base_url(cls) -> str:
        """Get API base URL.
        
        Returns:
            API base URL
        """
        return cls.API_BASE_URL
    
    @classmethod
    def get_dashboard_prefix(cls) -> str:
        """Get dashboard prefix.
        
        Returns:
            Dashboard prefix
        """
        return cls.DASHBOARD_PREFIX
    
    @classmethod
    def get_demo_user_id(cls) -> int:
        """Get demo user ID.
        
        Returns:
            Demo user ID
        """
        return cls.DEMO_USER_ID
