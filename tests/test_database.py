"""Tests for database functionality, migrations, and reset capability."""

import pytest
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
            retrieved = db_session.query(Signal).filter_by(symbol=f"TEST{i}").first()
            assert retrieved.status == status


class TestTradeModel:
    """Test Trade model."""

    def test_create_trade_linked_to_signal(self, db_session: Session):
        """Test creating a trade linked to a signal (acceptance criteria: every order is linked to a signal)."""
        # Create user
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        # Create option contract
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
        
        # Create signal
        signal = Signal(
            user_id=user.id,
            symbol="AAPL",
            strategy_type="bull_call_spread",
            risk_level="medium",
            score=0.85,
            expected_profit=500.0,
            max_loss=200.0,
            probability_estimate=0.72,
            reason="Strong technical setup",
            status="approved",
            option_contract_id=contract.id,
        )
        db_session.add(signal)
        db_session.commit()
        
        # Create trade linked to signal
        trade = Trade(
            user_id=user.id,
            signal_id=signal.id,
            option_contract_id=contract.id,
            broker_order_id="broker_123",
            status="open",
            entry_price=2.05,
            quantity=10,
            is_paper_trading=True,
        )
        db_session.add(trade)
        db_session.commit()
        
        # Verify trade is linked to signal
        retrieved_trade = db_session.query(Trade).filter_by(user_id=user.id).first()
        assert retrieved_trade is not None
        assert retrieved_trade.signal_id == signal.id
        assert retrieved_trade.signal.symbol == "AAPL"

    def test_trade_pnl_calculation_after_close(self, db_session: Session):
        """Test P/L calculation after trade close (acceptance criteria: P/L can be calculated after close)."""
        # Create user
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        # Create option contract
        contract = OptionContract(
            symbol="MSFT",
            expiration="2024-02-16",
            strike=300.0,
            contract_type="call",
            bid=3.0,
            ask=3.1,
            volume=1000,
            open_interest=5000,
            implied_volatility=0.25,
            underlying_price=300.0,
            days_to_expiration=30,
        )
        db_session.add(contract)
        db_session.commit()
        
        # Create signal
        signal = Signal(
            user_id=user.id,
            symbol="MSFT",
            strategy_type="bull_call_spread",
            risk_level="medium",
            score=0.80,
            expected_profit=400.0,
            max_loss=150.0,
            probability_estimate=0.70,
            reason="Bullish setup",
            status="executed",
            option_contract_id=contract.id,
        )
        db_session.add(signal)
        db_session.commit()
        
        # Create trade
        trade = Trade(
            user_id=user.id,
            signal_id=signal.id,
            option_contract_id=contract.id,
            broker_order_id="broker_456",
            status="open",
            entry_price=3.05,
            quantity=5,
            is_paper_trading=True,
        )
        db_session.add(trade)
        db_session.commit()
        
        # Close trade and calculate P/L
        trade.status = "closed"
        trade.exit_price = 4.50  # Profit per contract
        trade.realized_pnl = (trade.exit_price - trade.entry_price) * trade.quantity
        trade.closed_at = trade.opened_at  # In real scenario, this would be later
        db_session.commit()
        
        # Verify P/L calculation
        retrieved_trade = db_session.query(Trade).filter_by(id=trade.id).first()
        assert retrieved_trade.status == "closed"
        assert retrieved_trade.exit_price == 4.50
        assert retrieved_trade.realized_pnl == (4.50 - 3.05) * 5  # 7.25 * 5 = 36.25
        assert retrieved_trade.closed_at is not None

    def test_trade_with_all_required_fields(self, db_session: Session):
        """Test creating a trade with all required fields from Issue #018."""
        # Create user
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        # Create option contract
        contract = OptionContract(
            symbol="GOOGL",
            expiration="2024-03-15",
            strike=140.0,
            contract_type="put",
            bid=1.5,
            ask=1.6,
            volume=500,
            open_interest=2000,
            implied_volatility=0.20,
            underlying_price=140.0,
            days_to_expiration=45,
        )
        db_session.add(contract)
        db_session.commit()
        
        # Create signal
        signal = Signal(
            user_id=user.id,
            symbol="GOOGL",
            strategy_type="protective_put",
            risk_level="low",
            score=0.70,
            expected_profit=200.0,
            max_loss=100.0,
            probability_estimate=0.75,
            reason="Downside protection",
            status="approved",
            option_contract_id=contract.id,
        )
        db_session.add(signal)
        db_session.commit()
        
        # Create trade with all required fields
        trade = Trade(
            id=None,  # Auto-generated
            user_id=user.id,
            signal_id=signal.id,
            broker_order_id="broker_789",
            status="open",
            entry_price=1.55,
            exit_price=None,  # Not closed yet
            quantity=20,
            opened_at=None,  # Will use default
            closed_at=None,  # Not closed yet
            realized_pnl=None,  # Not closed yet
            option_contract_id=contract.id,
            is_paper_trading=True,
        )
        db_session.add(trade)
        db_session.commit()
        
        # Verify all fields
        retrieved_trade = db_session.query(Trade).filter_by(user_id=user.id).first()
        assert retrieved_trade.id is not None
        assert retrieved_trade.user_id == user.id
        assert retrieved_trade.signal_id == signal.id
        assert retrieved_trade.broker_order_id == "broker_789"
        assert retrieved_trade.status == "open"
        assert retrieved_trade.entry_price == 1.55
        assert retrieved_trade.exit_price is None
        assert retrieved_trade.quantity == 20
        assert retrieved_trade.opened_at is not None
        assert retrieved_trade.closed_at is None
        assert retrieved_trade.realized_pnl is None
        assert retrieved_trade.option_contract_id == contract.id
        assert retrieved_trade.is_paper_trading is True

    def test_trade_paper_vs_live_trading(self, db_session: Session):
        """Test that trades can be marked as paper or live trading."""
        # Create user
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
        )
        db_session.add(user)
        db_session.commit()
        
        # Create option contract
        contract = OptionContract(
            symbol="TSLA",
            expiration="2024-02-16",
            strike=250.0,
            contract_type="call",
            bid=5.0,
            ask=5.2,
            volume=2000,
            open_interest=10000,
            implied_volatility=0.35,
            underlying_price=250.0,
            days_to_expiration=30,
        )
        db_session.add(contract)
        db_session.commit()
        
        # Create signal
        signal = Signal(
            user_id=user.id,
            symbol="TSLA",
            strategy_type="bull_call_spread",
            risk_level="high",
            score=0.90,
            expected_profit=1000.0,
            max_loss=500.0,
            probability_estimate=0.65,
            reason="Strong momentum",
            status="approved",
            option_contract_id=contract.id,
        )
        db_session.add(signal)
        db_session.commit()
        
        # Create paper trade
        paper_trade = Trade(
            user_id=user.id,
            signal_id=signal.id,
            option_contract_id=contract.id,
            broker_order_id="paper_order_1",
            status="open",
            entry_price=5.1,
            quantity=10,
            is_paper_trading=True,
        )
        db_session.add(paper_trade)
        db_session.commit()
        
        # Create live trade
        live_trade = Trade(
            user_id=user.id,
            signal_id=signal.id,
            option_contract_id=contract.id,
            broker_order_id="live_order_1",
            status="open",
            entry_price=5.1,
            quantity=5,
            is_paper_trading=False,
        )
        db_session.add(live_trade)
        db_session.commit()
        
        # Verify both trades exist with correct trading type
        paper_trades = db_session.query(Trade).filter_by(is_paper_trading=True).all()
        live_trades = db_session.query(Trade).filter_by(is_paper_trading=False).all()
        
        assert len(paper_trades) == 1
        assert len(live_trades) == 1
        assert paper_trades[0].is_paper_trading is True
        assert live_trades[0].is_paper_trading is False
