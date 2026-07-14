"""Tests for watchlist functionality.

Tests cover:
- Watchlist retrieval
- Symbol validation
- Adding symbols
- Removing symbols
- Duplicate prevention
- Error handling
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.database import User, Watchlist, WatchlistSymbol
from app.frontend.dashboard import Dashboard, WatchlistItem


class TestWatchlistValidation:
    """Test symbol validation."""

    def test_validate_valid_symbol(self):
        """Test validating a valid symbol."""
        dashboard = Dashboard()
        result = dashboard.validate_symbol("AAPL")
        
        assert result["valid"] is True
        assert result["symbol"] == "AAPL"
        assert "valid" in result["message"].lower()

    def test_validate_lowercase_symbol(self):
        """Test that lowercase symbols are converted to uppercase."""
        dashboard = Dashboard()
        result = dashboard.validate_symbol("aapl")
        
        assert result["valid"] is True
        assert result["symbol"] == "AAPL"

    def test_validate_symbol_with_spaces(self):
        """Test that symbols with spaces are trimmed."""
        dashboard = Dashboard()
        result = dashboard.validate_symbol("  AAPL  ")
        
        assert result["valid"] is True
        assert result["symbol"] == "AAPL"

    def test_validate_empty_symbol(self):
        """Test that empty symbols are rejected."""
        dashboard = Dashboard()
        result = dashboard.validate_symbol("")
        
        assert result["valid"] is False
        assert "empty" in result["message"].lower()

    def test_validate_too_long_symbol(self):
        """Test that symbols longer than 5 characters are rejected."""
        dashboard = Dashboard()
        result = dashboard.validate_symbol("TOOLONG")
        
        assert result["valid"] is False
        assert "invalid" in result["message"].lower()

    def test_validate_symbol_with_numbers(self):
        """Test that symbols with numbers are rejected."""
        dashboard = Dashboard()
        result = dashboard.validate_symbol("AAP1")
        
        assert result["valid"] is False
        assert "invalid" in result["message"].lower()

    def test_validate_symbol_with_special_chars(self):
        """Test that symbols with special characters are rejected."""
        dashboard = Dashboard()
        result = dashboard.validate_symbol("AA-PL")
        
        assert result["valid"] is False
        assert "invalid" in result["message"].lower()

    def test_validate_none_symbol(self):
        """Test that None symbols are rejected."""
        dashboard = Dashboard()
        result = dashboard.validate_symbol(None)
        
        assert result["valid"] is False


class TestWatchlistOperations:
    """Test watchlist add/remove operations."""

    def test_add_symbol_to_watchlist(self, db_session: Session):
        """Test adding a symbol to watchlist."""
        # Create user
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        dashboard = Dashboard()
        result = dashboard.add_symbol(user.id, "AAPL", db_session)
        
        assert result["status"] == "success"
        assert result["symbol"] == "AAPL"
        assert "added" in result["message"].lower()
        
        # Verify in database
        watchlist = db_session.query(Watchlist).filter(
            Watchlist.user_id == user.id
        ).first()
        assert watchlist is not None
        
        symbol = db_session.query(WatchlistSymbol).filter(
            WatchlistSymbol.watchlist_id == watchlist.id,
            WatchlistSymbol.symbol == "AAPL",
        ).first()
        assert symbol is not None

    def test_add_duplicate_symbol(self, db_session: Session):
        """Test that adding duplicate symbols is prevented."""
        # Create user and watchlist
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        watchlist = Watchlist(
            user_id=user.id,
            name="Test Watchlist",
        )
        db_session.add(watchlist)
        db_session.commit()
        
        # Add symbol
        ws = WatchlistSymbol(
            watchlist_id=watchlist.id,
            symbol="AAPL",
        )
        db_session.add(ws)
        db_session.commit()
        
        # Try to add duplicate
        dashboard = Dashboard()
        result = dashboard.add_symbol(user.id, "AAPL", db_session)
        
        assert result["status"] == "error"
        assert "already" in result["message"].lower()

    def test_add_invalid_symbol(self, db_session: Session):
        """Test that invalid symbols are rejected."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        dashboard = Dashboard()
        result = dashboard.add_symbol(user.id, "INVALID123", db_session)
        
        assert result["status"] == "error"
        assert "invalid" in result["message"].lower()

    def test_remove_symbol_from_watchlist(self, db_session: Session):
        """Test removing a symbol from watchlist."""
        # Create user and watchlist with symbol
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        watchlist = Watchlist(
            user_id=user.id,
            name="Test Watchlist",
        )
        db_session.add(watchlist)
        db_session.commit()
        
        ws = WatchlistSymbol(
            watchlist_id=watchlist.id,
            symbol="AAPL",
        )
        db_session.add(ws)
        db_session.commit()
        
        # Remove symbol
        dashboard = Dashboard()
        result = dashboard.remove_symbol(user.id, "AAPL", db_session)
        
        assert result["status"] == "success"
        assert result["symbol"] == "AAPL"
        assert "removed" in result["message"].lower()
        
        # Verify removed from database
        symbol = db_session.query(WatchlistSymbol).filter(
            WatchlistSymbol.watchlist_id == watchlist.id,
            WatchlistSymbol.symbol == "AAPL",
        ).first()
        assert symbol is None

    def test_remove_nonexistent_symbol(self, db_session: Session):
        """Test removing a symbol that doesn't exist."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        watchlist = Watchlist(
            user_id=user.id,
            name="Test Watchlist",
        )
        db_session.add(watchlist)
        db_session.commit()
        
        dashboard = Dashboard()
        result = dashboard.remove_symbol(user.id, "AAPL", db_session)
        
        assert result["status"] == "error"
        assert "not in watchlist" in result["message"].lower()

    def test_remove_symbol_nonexistent_user(self, db_session: Session):
        """Test removing symbol for nonexistent user."""
        dashboard = Dashboard()
        result = dashboard.remove_symbol(99999, "AAPL", db_session)
        
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()


class TestWatchlistRetrieval:
    """Test watchlist retrieval."""

    def test_get_empty_watchlist(self, db_session: Session):
        """Test getting an empty watchlist."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        dashboard = Dashboard()
        items = dashboard.get_watchlist(user.id, db_session)
        
        assert items == []

    def test_get_watchlist_with_symbols(self, db_session: Session):
        """Test getting a watchlist with symbols."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        watchlist = Watchlist(
            user_id=user.id,
            name="Test Watchlist",
        )
        db_session.add(watchlist)
        db_session.commit()
        
        symbols = ["AAPL", "MSFT", "GOOGL"]
        for symbol in symbols:
            ws = WatchlistSymbol(
                watchlist_id=watchlist.id,
                symbol=symbol,
            )
            db_session.add(ws)
        db_session.commit()
        
        dashboard = Dashboard()
        items = dashboard.get_watchlist(user.id, db_session)
        
        assert len(items) == 3
        assert [item.symbol for item in items] == symbols
        assert all(isinstance(item, WatchlistItem) for item in items)

    def test_get_watchlist_nonexistent_user(self, db_session: Session):
        """Test getting watchlist for nonexistent user."""
        dashboard = Dashboard()
        items = dashboard.get_watchlist(99999, db_session)
        
        assert items == []


class TestWatchlistIntegration:
    """Integration tests for watchlist functionality."""

    def test_add_multiple_symbols(self, db_session: Session):
        """Test adding multiple symbols to watchlist."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        dashboard = Dashboard()
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        
        for symbol in symbols:
            result = dashboard.add_symbol(user.id, symbol, db_session)
            assert result["status"] == "success"
        
        # Verify all symbols are in watchlist
        items = dashboard.get_watchlist(user.id, db_session)
        assert len(items) == 5
        assert set(item.symbol for item in items) == set(symbols)

    def test_add_and_remove_workflow(self, db_session: Session):
        """Test complete add and remove workflow."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        dashboard = Dashboard()
        
        # Add symbols
        dashboard.add_symbol(user.id, "AAPL", db_session)
        dashboard.add_symbol(user.id, "MSFT", db_session)
        dashboard.add_symbol(user.id, "GOOGL", db_session)
        
        items = dashboard.get_watchlist(user.id, db_session)
        assert len(items) == 3
        
        # Remove one symbol
        result = dashboard.remove_symbol(user.id, "MSFT", db_session)
        assert result["status"] == "success"
        
        items = dashboard.get_watchlist(user.id, db_session)
        assert len(items) == 2
        assert "MSFT" not in [item.symbol for item in items]
