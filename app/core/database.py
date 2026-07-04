"""Database configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from typing import Generator

from app.core.config import get_config

# Get config instance
config = get_config()

# Create engine based on environment
if config.is_test():
    # Use in-memory SQLite for tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # Use configured database URL
    database_url = config.get_database_url()
    engine = create_engine(
        database_url,
        echo=config.is_development(),
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base for models
Base = declarative_base()


def get_db() -> Generator:
    """Get database session.
    
    Yields:
        Database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database by creating all tables."""
    # Import ORM models so they register with Base.metadata before create_all().
    import app.models.database  # noqa: F401

    Base.metadata.create_all(bind=engine)


def reset_db() -> None:
    """Reset database by dropping and recreating all tables."""
    # Import ORM models so they register with Base.metadata before drop/create.
    import app.models.database  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
