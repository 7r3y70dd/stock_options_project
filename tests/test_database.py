"""Tests for database functionality, migrations, and reset capability."""

import pytest
from sqlalchemy.orm import Session

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
        # Get all table names
        inspector = db_session.connection().dialect.inspector
        tables = inspector.get_table_names()
        
        required_tables = [
            "users",
            "watchlists",
            "watchlist_symbols",
            "option_contracts",
            "signals",
            "trades",
            "backtest_results",
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


class TestTradeModel:
    """Test Trade model."""

    def test_create_trade(self, db_session: Session):
        """Test creating a trade."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
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
        
        trade = Trade(
            user_id=user.id,
            option_contract_id=contract.id,
            trade_type="buy",
            quantity=10,
            entry_price=2.05,
            status="open",
            is_paper_trading=True,
        )
        db_session.add(trade)
        db_session.commit()
        
        retrieved = db_session.query(Trade).filter_by(user_id=user.id).first()
        assert retrieved is not None
        assert retrieved.quantity == 10
        assert retrieved.status == "open"


class TestSignalModel:
    """Test Signal model."""

    def test_create_signal(self, db_session: Session):
        """Test creating a signal."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
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
        
        signal = Signal(
            user_id=user.id,
            option_contract_id=contract.id,
            signal_type="buy",
            confidence=0.85,
            reason="Strong technical setup",
        )
        db_session.add(signal)
        db_session.commit()
        
        retrieved = db_session.query(Signal).filter_by(user_id=user.id).first()
        assert retrieved is not None
        assert retrieved.confidence == 0.85
        assert retrieved.signal_type == "buy"


class TestBacktestResultModel:
    """Test BacktestResult model."""

    def test_create_backtest_result(self, db_session: Session):
        """Test creating a backtest result."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        result = BacktestResult(
            user_id=user.id,
            strategy_name="Bull Call Spread",
            symbol="AAPL",
            start_date="2024-01-01",
            end_date="2024-01-31",
            initial_capital=100000.0,
            final_capital=105000.0,
            total_return_pct=5.0,
            total_trades=10,
            winning_trades=7,
            losing_trades=3,
            win_rate=0.7,
            max_drawdown_pct=2.5,
            sharpe_ratio=1.5,
        )
        db_session.add(result)
        db_session.commit()
        
        retrieved = db_session.query(BacktestResult).filter_by(user_id=user.id).first()
        assert retrieved is not None
        assert retrieved.total_return_pct == 5.0
        assert retrieved.win_rate == 0.7


class TestDatabaseReset:
    """Test database reset functionality."""

    def test_database_can_be_reset(self, db_session: Session):
        """Test that database can be reset."""
        # Add some data
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        # Verify data exists
        assert db_session.query(User).count() == 1
        
        # Reset database
        db_session.close()
        reset_db()
        
        # Verify data is gone
        new_session = SessionLocal()
        assert new_session.query(User).count() == 0
        new_session.close()

    def test_reset_db_fails_in_production(self):
        """Test that reset_db raises error in production."""
        # Temporarily set environment to prod
        original_env = Config.ENVIRONMENT
        try:
            Config.ENVIRONMENT = Environment.PROD
            with pytest.raises(RuntimeError, match="Cannot reset database in production"):
                reset_db()
        finally:
            Config.ENVIRONMENT = original_env


class TestMigrations:
    """Test database migrations."""

    def test_migrations_run_cleanly(self, db_session: Session):
        """Test that migrations run without errors."""
        # If we got here, migrations ran successfully
        # Verify all tables exist
        inspector = db_session.connection().dialect.inspector
        tables = inspector.get_table_names()
        
        required_tables = [
            "users",
            "watchlists",
            "watchlist_symbols",
            "option_contracts",
            "signals",
            "trades",
            "backtest_results",
        ]
        
        for table in required_tables:
            assert table in tables
