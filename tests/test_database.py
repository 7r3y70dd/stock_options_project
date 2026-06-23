"""Tests for database functionality, migrations, and reset capability."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.config import Config, Environment
from app.core.database import SessionLocal, init_db, reset_db, Base, engine
from app.models.database import (
    User,
    Watchlist,
    WatchlistSymbol,
    OptionContract,
    Signal,
    Trade,
    BacktestResult,
    NewsArticle,
)


@pytest.fixture
def db_session() -> Session:
    """Create a test database session."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    session = SessionLocal()
    yield session
    
    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=engine)


class TestDatabaseInitialization:
    """Test database initialization."""

    def test_database_starts_locally(self, db_session: Session):
        """Test that database starts and is accessible."""
        # Simple query to verify connection
        result = db_session.query(User).first()
        assert result is None  # Should be empty

    def test_all_tables_created(self, db_session: Session):
        """Test that all required tables are created."""
        # Get all table names using instance-based inspector
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        required_tables = [
            "users",
            "watchlists",
            "watchlist_symbols",
            "option_contracts",
            "signals",
            "trades",
            "backtest_results",
            "news_articles",
        ]
        
        for table in required_tables:
            assert table in tables, f"Table {table} not found in database"


class TestUserModel:
    """Test User model."""

    def test_create_user(self, db_session: Session):
        """Test creating a user."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
            is_active=True,
            risk_level="medium",
        )
        db_session.add(user)
        db_session.commit()
        
        retrieved = db_session.query(User).filter_by(username="testuser").first()
        assert retrieved is not None
        assert retrieved.email == "test@example.com"
        assert retrieved.risk_level == "medium"

    def test_user_unique_constraints(self, db_session: Session):
        """Test that username and email are unique."""
        user1 = User(
            username="testuser",
            email="test1@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user1)
        db_session.commit()
        
        # Try to create duplicate username
        user2 = User(
            username="testuser",
            email="test2@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user2)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestWatchlistModel:
    """Test Watchlist model."""

    def test_create_watchlist(self, db_session: Session):
        """Test creating a watchlist."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        watchlist = Watchlist(
            user_id=user.id,
            name="Tech Stocks",
            description="Technology stocks",
        )
        db_session.add(watchlist)
        db_session.commit()
        
        retrieved = db_session.query(Watchlist).filter_by(name="Tech Stocks").first()
        assert retrieved is not None
        assert retrieved.user_id == user.id

    def test_watchlist_symbols(self, db_session: Session):
        """Test adding symbols to watchlist."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        watchlist = Watchlist(
            user_id=user.id,
            name="Tech Stocks",
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
        
        retrieved_symbols = db_session.query(WatchlistSymbol).filter_by(
            watchlist_id=watchlist.id
        ).all()
        assert len(retrieved_symbols) == 3
        assert [s.symbol for s in retrieved_symbols] == symbols

    def test_watchlist_symbol_remove(self, db_session: Session):
        """Test removing symbols from watchlist."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        watchlist = Watchlist(
            user_id=user.id,
            name="Tech Stocks",
        )
        db_session.add(watchlist)
        db_session.commit()
        
        # Add symbols
        symbols = ["AAPL", "MSFT", "GOOGL"]
        for symbol in symbols:
            ws = WatchlistSymbol(
                watchlist_id=watchlist.id,
                symbol=symbol,
            )
            db_session.add(ws)
        db_session.commit()
        
        # Remove one symbol
        to_remove = db_session.query(WatchlistSymbol).filter_by(
            watchlist_id=watchlist.id,
            symbol="MSFT"
        ).first()
        db_session.delete(to_remove)
        db_session.commit()
        
        # Verify removal
        retrieved_symbols = db_session.query(WatchlistSymbol).filter_by(
            watchlist_id=watchlist.id
        ).all()
        assert len(retrieved_symbols) == 2
        assert [s.symbol for s in retrieved_symbols] == ["AAPL", "GOOGL"]

    def test_watchlist_duplicate_symbols_blocked(self, db_session: Session):
        """Test that duplicate symbols are blocked in the same watchlist."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        watchlist = Watchlist(
            user_id=user.id,
            name="Tech Stocks",
        )
        db_session.add(watchlist)
        db_session.commit()
        
        # Add first symbol
        ws1 = WatchlistSymbol(
            watchlist_id=watchlist.id,
            symbol="AAPL",
        )
        db_session.add(ws1)
        db_session.commit()
        
        # Try to add duplicate symbol
        ws2 = WatchlistSymbol(
            watchlist_id=watchlist.id,
            symbol="AAPL",
        )
        db_session.add(ws2)
        
        # Should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestOptionContractModel:
    """Test OptionContract model."""

    def test_create_option_contract(self, db_session: Session):
        """Test creating an option contract."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-02-16",
            strike=150.0,
            contract_type="call",
            bid=2.0,
            ask=2.1,
            volume=1000,
            open_interest=5000,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
        )
        db_session.add(contract)
        db_session.commit()
        
        retrieved = db_session.query(OptionContract).filter_by(symbol="AAPL").first()
        assert retrieved is not None
        assert retrieved.strike == 150.0
        assert retrieved.contract_type == "call"


class TestSignalModel:
    """Test Signal model."""

    def test_create_signal_with_all_fields(self, db_session: Session):
        """Test creating a signal with all required fields."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        signal = Signal(
            user_id=user.id,
            symbol="AAPL",
            strategy_type="bull_call_spread",
            risk_level="medium",
            score=0.85,
            expected_profit=500.0,
            max_loss=200.0,
            probability_estimate=0.72,
            reason="Strong technical setup with bullish momentum and support at 150 level",
            status="pending",
        )
        db_session.add(signal)
        db_session.commit()
        
        retrieved = db_session.query(Signal).filter_by(user_id=user.id).first()
        assert retrieved is not None
        assert retrieved.symbol == "AAPL"
        assert retrieved.strategy_type == "bull_call_spread"
        assert retrieved.risk_level == "medium"
        assert retrieved.score == 0.85
        assert retrieved.expected_profit == 500.0
        assert retrieved.max_loss == 200.0
        assert retrieved.probability_estimate == 0.72
        assert retrieved.reason == "Strong technical setup with bullish momentum and support at 150 level"
        assert retrieved.status == "pending"

    def test_signal_has_explanation(self, db_session: Session):
        """Test that every signal has an explanation (reason field)."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        signal = Signal(
            user_id=user.id,
            symbol="MSFT",
            strategy_type="iron_condor",
            risk_level="low",
            score=0.65,
            expected_profit=300.0,
            max_loss=100.0,
            probability_estimate=0.68,
            reason="Earnings play with defined risk and high probability of profit",
            status="pending",
        )
        db_session.add(signal)
        db_session.commit()
        
        retrieved = db_session.query(Signal).filter_by(user_id=user.id).first()
        assert retrieved.reason is not None
        assert len(retrieved.reason) > 0

    def test_signal_has_max_loss_estimate(self, db_session: Session):
        """Test that every signal has a max-loss estimate."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        signal = Signal(
            user_id=user.id,
            symbol="GOOGL",
            strategy_type="covered_call",
            risk_level="low",
            score=0.75,
            expected_profit=250.0,
            max_loss=150.0,
            probability_estimate=0.80,
            reason="Income generation strategy with downside protection",
            status="pending",
        )
        db_session.add(signal)
        db_session.commit()
        
        retrieved = db_session.query(Signal).filter_by(user_id=user.id).first()
        assert retrieved.max_loss is not None
        assert retrieved.max_loss > 0

    def test_signal_status_transitions(self, db_session: Session):
        """Test that signal can have different status values."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        statuses = ["pending", "approved", "rejected", "expired", "executed"]
        
        for i, status in enumerate(statuses):
            signal = Signal(
                user_id=user.id,
                symbol=f"TEST{i}",
                strategy_type="bull_call_spread",
                risk_level="medium",
                score=0.75,
                expected_profit=300.0,
                max_loss=100.0,
                probability_estimate=0.70,
                reason=f"Test signal with status {status}",
                status=status,
            )
            db_session.add(signal)
        db_session.commit()
        
        # Verify all statuses were created
        for i, status in enumerate(statuses):
            retrieved = db_session.query(Signal).filter_by(
                user_id=user.id,
                symbol=f"TEST{i}"
            ).first()
            assert retrieved is not None
            assert retrieved.status == status
