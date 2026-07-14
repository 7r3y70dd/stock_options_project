"""Tests for TradeManager class.

Covers signal approval, trade creation, validation, and closure.
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.database import (
    User,
    Signal,
    Trade,
    OptionContract,
    Watchlist,
    WatchlistSymbol,
)
from app.trading.trade_manager import TradeManager
from app.core.database import Base, engine


@pytest.fixture
def db():
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    from app.core.database import SessionLocal
    db = SessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def trade_manager():
    """Create a TradeManager instance."""
    return TradeManager()


@pytest.fixture
def test_user(db: Session):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        risk_level="medium",
        paper_trading_enabled=True,
        live_trading_enabled=False,
        initial_portfolio_value=100000.0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_option_contract(db: Session):
    """Create a test option contract."""
    contract = OptionContract(
        symbol="AAPL",
        underlying_symbol="AAPL",
        expiration="2026-12-18",
        strike=150.0,
        contract_type="call",
        bid=3.50,
        ask=3.90,
        last=3.70,
        volume=1000,
        open_interest=5000,
        implied_volatility=0.25,
        delta=0.65,
        gamma=0.02,
        theta=-0.05,
        vega=0.15,
        underlying_price=155.0,
        days_to_expiration=30,
        earnings_date=None,
        historical_volatility=0.22,
        volatility_context="fair",
        theoretical_price=3.70,
        pricing_difference=0.0,
        pricing_assessment="fair",
        liquidity_score=85.0,
        event_risks=None,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


@pytest.fixture
def test_signal(db: Session, test_user: User, test_option_contract: OptionContract):
    """Create a test pending signal."""
    signal = Signal(
        user_id=test_user.id,
        symbol="AAPL",
        strategy_type="covered_call",
        risk_level="medium",
        score=0.85,
        expected_profit=150.0,
        max_loss=500.0,
        probability_estimate=0.72,
        reason="Strong uptrend with high IV",
        status="pending",
        option_contract_id=test_option_contract.id,
        breakdown='{"trend": 0.9, "volatility": 0.8}',
        event_risks=None,
        exit_rules='[{"type": "profit_target", "value": 150}]',
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


class TestApproveSignalAsPaperTrade:
    """Tests for approve_signal_as_paper_trade method."""

    def test_approve_pending_signal_creates_trade(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
        test_signal: Signal,
        test_option_contract: OptionContract,
    ):
        """Test that approving a pending signal creates a trade."""
        trade = trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db,
            quantity=1,
        )

        assert trade is not None
        assert trade.user_id == test_user.id
        assert trade.signal_id == test_signal.id
        assert trade.option_contract_id == test_option_contract.id
        assert trade.status == "open"
        assert trade.order_status == "filled"
        assert trade.is_paper_trading is True
        assert trade.quantity == 1
        
        # Entry price should be mid-price
        expected_entry_price = (test_option_contract.bid + test_option_contract.ask) / 2
        assert trade.entry_price == expected_entry_price
        assert trade.entry_price == 3.70  # (3.50 + 3.90) / 2

    def test_approve_signal_updates_signal_status(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
        test_signal: Signal,
    ):
        """Test that approving a signal updates its status to 'approved'."""
        assert test_signal.status == "pending"
        
        trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db,
        )
        
        # Refresh signal from DB
        db.refresh(test_signal)
        assert test_signal.status == "approved"

    def test_approve_signal_with_custom_quantity(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
        test_signal: Signal,
    ):
        """Test that custom quantity is respected."""
        trade = trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db,
            quantity=5,
        )
        
        assert trade.quantity == 5

    def test_approve_missing_signal_fails(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
    ):
        """Test that approving a non-existent signal raises ValueError."""
        with pytest.raises(ValueError, match="Signal 999 not found"):
            trade_manager.approve_signal_as_paper_trade(
                user_id=test_user.id,
                signal_id=999,
                db=db,
            )

    def test_approve_signal_for_wrong_user_fails(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_signal: Signal,
    ):
        """Test that approving a signal for a different user fails."""
        wrong_user_id = test_signal.user_id + 1
        
        with pytest.raises(ValueError, match="belongs to user"):
            trade_manager.approve_signal_as_paper_trade(
                user_id=wrong_user_id,
                signal_id=test_signal.id,
                db=db,
            )

    def test_approve_already_approved_signal_fails(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
        test_signal: Signal,
    ):
        """Test that approving an already-approved signal fails."""
        # First approval succeeds
        trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db,
        )
        
        # Second approval should fail
        with pytest.raises(ValueError, match="status 'approved'"):
            trade_manager.approve_signal_as_paper_trade(
                user_id=test_user.id,
                signal_id=test_signal.id,
                db=db,
            )

    def test_approve_signal_without_option_contract_fails(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
    ):
        """Test that approving a signal without option contract fails."""
        signal = Signal(
            user_id=test_user.id,
            symbol="MSFT",
            strategy_type="covered_call",
            risk_level="medium",
            score=0.80,
            expected_profit=100.0,
            max_loss=400.0,
            probability_estimate=0.70,
            reason="Test signal",
            status="pending",
            option_contract_id=None,  # No contract
            exit_rules='[]',
        )
        db.add(signal)
        db.commit()
        
        with pytest.raises(ValueError, match="no linked option contract"):
            trade_manager.approve_signal_as_paper_trade(
                user_id=test_user.id,
                signal_id=signal.id,
                db=db,
            )


class TestGetOpenTrades:
    """Tests for get_open_trades method."""

    def test_get_open_trades_returns_open_trades(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
        test_signal: Signal,
    ):
        """Test that get_open_trades returns only open trades."""
        # Create an open trade
        trade = trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db,
        )
        
        open_trades = trade_manager.get_open_trades(test_user.id, db)
        
        assert len(open_trades) == 1
        assert open_trades[0].id == trade.id
        assert open_trades[0].status == "open"

    def test_get_open_trades_excludes_closed_trades(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
        test_signal: Signal,
    ):
        """Test that closed trades are not returned."""
        # Create and close a trade
        trade = trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db,
        )
        
        trade_manager.close_trade(
            user_id=test_user.id,
            trade_id=trade.id,
            db=db,
            exit_price=4.50,
        )
        
        open_trades = trade_manager.get_open_trades(test_user.id, db)
        
        assert len(open_trades) == 0

    def test_get_open_trades_for_user_with_no_trades(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
    ):
        """Test that empty list is returned for user with no trades."""
        open_trades = trade_manager.get_open_trades(test_user.id, db)
        
        assert len(open_trades) == 0
        assert open_trades == []


class TestCloseTrade:
    """Tests for close_trade method."""

    def test_close_open_trade_calculates_realized_pnl(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
        test_signal: Signal,
    ):
        """Test that closing a trade calculates realized P/L correctly."""
        # Create trade at entry price 3.70
        trade = trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db,
            quantity=1,
        )
        
        # Close at exit price 4.50
        closed_trade = trade_manager.close_trade(
            user_id=test_user.id,
            trade_id=trade.id,
            db=db,
            exit_price=4.50,
        )
        
        # P/L = (4.50 - 3.70) * 1 * 100 = 80
        assert closed_trade.realized_pnl == 80.0

    def test_close_trade_with_loss(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
        test_signal: Signal,
    ):
        """Test that closing a trade with loss calculates negative P/L."""
        trade = trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db,
            quantity=1,
        )
        
        # Close at lower price
        closed_trade = trade_manager.close_trade(
            user_id=test_user.id,
            trade_id=trade.id,
            db=db,
            exit_price=2.50,
        )
        
        # P/L = (2.50 - 3.70) * 1 * 100 = -120
        assert closed_trade.realized_pnl == -120.0

    def test_close_trade_with_multiple_quantity(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
        test_signal: Signal,
    ):
        """Test P/L calculation with multiple contracts."""
        trade = trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db,
            quantity=3,
        )
        
        closed_trade = trade_manager.close_trade(
            user_id=test_user.id,
            trade_id=trade.id,
            db=db,
            exit_price=4.50,
        )
        
        # P/L = (4.50 - 3.70) * 3 * 100 = 240
        assert closed_trade.realized_pnl == 240.0

    def test_close_trade_updates_status(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
        test_signal: Signal,
    ):
        """Test that closing a trade updates its status."""
        trade = trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db,
        )
        
        assert trade.status == "open"
        
        closed_trade = trade_manager.close_trade(
            user_id=test_user.id,
            trade_id=trade.id,
            db=db,
            exit_price=4.50,
        )
        
        assert closed_trade.status == "closed"
        assert closed_trade.exit_price == 4.50
        assert closed_trade.closed_at is not None

    def test_close_trade_with_custom_exit_reason(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
        test_signal: Signal,
    ):
        """Test that custom exit reason is stored."""
        trade = trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db,
        )
        
        closed_trade = trade_manager.close_trade(
            user_id=test_user.id,
            trade_id=trade.id,
            db=db,
            exit_price=4.50,
            exit_reason="profit_target_hit",
        )
        
        assert closed_trade.exit_reason == "profit_target_hit"

    def test_close_missing_trade_fails(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
    ):
        """Test that closing a non-existent trade fails."""
        with pytest.raises(ValueError, match="Trade 999 not found"):
            trade_manager.close_trade(
                user_id=test_user.id,
                trade_id=999,
                db=db,
                exit_price=4.50,
            )

    def test_close_trade_for_wrong_user_fails(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
        test_signal: Signal,
    ):
        """Test that closing a trade for a different user fails."""
        trade = trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db,
        )
        
        wrong_user_id = test_user.id + 1
        
        with pytest.raises(ValueError, match="not found for user"):
            trade_manager.close_trade(
                user_id=wrong_user_id,
                trade_id=trade.id,
                db=db,
                exit_price=4.50,
            )

    def test_close_already_closed_trade_fails(
        self,
        trade_manager: TradeManager,
        db: Session,
        test_user: User,
        test_signal: Signal,
    ):
        """Test that closing an already-closed trade fails."""
        trade = trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db,
        )
        
        # First close succeeds
        trade_manager.close_trade(
            user_id=test_user.id,
            trade_id=trade.id,
            db=db,
            exit_price=4.50,
        )
        
        # Second close should fail
        with pytest.raises(ValueError, match="status 'closed'"):
            trade_manager.close_trade(
                user_id=test_user.id,
                trade_id=trade.id,
                db=db,
                exit_price=5.00,
            )
