"""Database connection and session management."""

import logging
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.core.config import config

logger = logging.getLogger(__name__)

# SQLAlchemy declarative base for all models
Base = declarative_base()

# Create engine
if config.is_test():
    # Use in-memory SQLite for tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # Use PostgreSQL for dev/prod
    engine = create_engine(
        config.DATABASE_URL,
        echo=config.DEBUG,
        pool_pre_ping=True,
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session for dependency injection.
    
    Yields:
        SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database by creating all tables."""
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def reset_db() -> None:
    """Reset database by dropping and recreating all tables.
    
    WARNING: This will delete all data. Use only in test/dev environments.
    """
    if config.is_prod():
        raise RuntimeError("Cannot reset database in production environment")
    
    logger.warning("Resetting database - all data will be deleted")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.info("Database reset complete")
