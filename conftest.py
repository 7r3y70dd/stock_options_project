"""Shared pytest fixtures."""

import pytest
from sqlalchemy.orm import Session

from app.core.database import Base, engine, SessionLocal


@pytest.fixture
def db_session() -> Session:
    """Create a clean database session for each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
