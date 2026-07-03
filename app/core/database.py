"""Database configuration and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_config


def get_database_url() -> str:
    """Get the database URL based on environment."""
    config = get_config()
    return config.get_database_url()


def create_db_engine():
    """Create database engine based on environment."""
    config = get_config()
    database_url = config.get_database_url()
    
    if config.is_test():
        # Use in-memory SQLite for tests
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(database_url, pool_pre_ping=True)
    
    return engine


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
