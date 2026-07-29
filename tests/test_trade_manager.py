"""Tests for trade manager functionality."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.database import User, Signal, Trade, OptionContract, Watchlist, WatchlistSymbol
from app.trading.trade_manager import TradeManager
from app.core.database import get_db
from fastapi.testclient import TestClient
from app.core.main import app


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        risk_level="medium",
        paper_trading_enabled=True,
        initial_portfolio_value=100000.0,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_option_contract(db_session: Session) -> OptionContract:
    """Create a test option contract."""
    contract = OptionContract(
        symbol="AAPL",
        expiration="2024-12-20",
        strike=150.0,
        contract_type="call",
        bid=5.0,
        ask=5.5,
        volume=1000,
        open_interest=5000,
        implied_volatility=0.25,
        underlying_price=155.0,
        days_to_expiration=30,
    )
    db_session.add(contract)
    db_session.commit()
    db_session.refresh(contract)
    return contract


@pytest.fixture
def test_signal(db_session: Session, test_user: User, test_option_contract: OptionContract) -> Signal:
    """Create a test signal with covered_call strategy (allowed for medium risk)."""
    signal = Signal(
        user_id=test_user.id,
        symbol="AAPL",
        strategy_type="covered_call",
        risk_level="medium",
        score=85.0,
        expected_profit=500.0,
        max_loss=550.0,
        probability_estimate=0.7,
        reason="Test signal",
        status="pending",
        option_contract_id=test_option_contract.id,
        exit_rules='[{"type": "profit_target", "value": 0.5}]',
    )
    db_session.add(signal)
    db_session.commit()
    db_session.refresh(signal)
    return signal


@pytest.fixture
def trade_manager() -> TradeManager:
    """Create a trade manager instance."""
    return TradeManager()


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


def test_approve_signal_as_paper_trade(
    db_session: Session,
    trade_manager: TradeManager,
    test_user: User,
    test_signal: Signal,
    test_option_contract: OptionContract,
):
    """Test approving a signal as a paper trade."""
    trade = trade_manager.approve_signal_as_paper_trade(
        user_id=test_user.id,
        signal_id=test_signal.id,
        db=db_session,
        quantity=2,
    )
    
    assert trade is not None
    assert trade.user_id == test_user.id
    assert trade.signal_id == test_signal.id
    assert trade.status == "open"
    assert trade.quantity == 2
    assert trade.is_paper_trading is True
    assert trade.entry_price == (test_option_contract.bid + test_option_contract.ask) / 2
    
    # Verify signal status updated
    db_session.refresh(test_signal)
    assert test_signal.status == "approved"


def test_approve_signal_wrong_user(
    db_session: Session,
    trade_manager: TradeManager,
    test_signal: Signal,
):
    """Test that approving a signal for wrong user fails."""
    with pytest.raises(ValueError, match="belongs to user"):
        trade_manager.approve_signal_as_paper_trade(
            user_id=999,  # Wrong user ID
            signal_id=test_signal.id,
            db=db_session,
            quantity=1,
        )


def test_approve_signal_already_approved(
    db_session: Session,
    trade_manager: TradeManager,
    test_user: User,
    test_signal: Signal,
):
    """Test that approving an already approved signal fails."""
    # First approval
    trade_manager.approve_signal_as_paper_trade(
        user_id=test_user.id,
        signal_id=test_signal.id,
        db=db_session,
        quantity=1,
    )
    
    # Second approval should fail
    with pytest.raises(ValueError, match="cannot approve"):
        trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db_session,
            quantity=1,
        )


def test_get_open_trades(
    db_session: Session,
    trade_manager: TradeManager,
    test_user: User,
    test_signal: Signal,
):
    """Test getting open trades for a user."""
    # Create a trade
    trade = trade_manager.approve_signal_as_paper_trade(
        user_id=test_user.id,
        signal_id=test_signal.id,
        db=db_session,
        quantity=1,
    )
    
    # Get open trades
    open_trades = trade_manager.get_open_trades(test_user.id, db_session)
    
    assert len(open_trades) == 1
    assert open_trades[0].id == trade.id
    assert open_trades[0].status == "open"


def test_close_trade(
    db_session: Session,
    trade_manager: TradeManager,
    test_user: User,
    test_signal: Signal,
):
    """Test closing an open trade."""
    # Create a trade
    trade = trade_manager.approve_signal_as_paper_trade(
        user_id=test_user.id,
        signal_id=test_signal.id,
        db=db_session,
        quantity=1,
    )
    
    # Close the trade
    exit_price = 6.0
    closed_trade = trade_manager.close_trade(
        user_id=test_user.id,
        trade_id=trade.id,
        db=db_session,
        exit_price=exit_price,
        exit_reason="test_close",
    )
    
    assert closed_trade.status == "closed"
    assert closed_trade.exit_price == exit_price
    assert closed_trade.exit_reason == "test_close"
    assert closed_trade.realized_pnl is not None
    assert closed_trade.closed_at is not None


def test_close_trade_wrong_user(
    db_session: Session,
    trade_manager: TradeManager,
    test_user: User,
    test_signal: Signal,
):
    """Test that closing a trade for wrong user fails."""
    # Create a trade
    trade = trade_manager.approve_signal_as_paper_trade(
        user_id=test_user.id,
        signal_id=test_signal.id,
        db=db_session,
        quantity=1,
    )
    
    # Try to close with wrong user
    with pytest.raises(ValueError, match="not found for user"):
        trade_manager.close_trade(
            user_id=999,  # Wrong user ID
            trade_id=trade.id,
            db=db_session,
            exit_price=6.0,
        )


def test_open_trade_count_endpoint(
    client: TestClient,
    db_session: Session,
    test_user: User,
    test_signal: Signal,
):
    """Test the open trade count endpoint."""
    # Override the database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        # Create a trade
        trade_manager = TradeManager()
        trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db_session,
            quantity=1,
        )
        
        # Test the endpoint
        response = client.get(f"/api/api/dashboard/trades/open/count?user_id={test_user.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user.id
        assert data["open_trade_count"] == 1
    finally:
        app.dependency_overrides.clear()



def clone_option_contract(
    db_session: Session,
    source: OptionContract,
    *,
    symbol: str,
    option_type: str,
) -> OptionContract:
    """Create a test contract based on an existing fixture."""

    values = {
        column.name: getattr(source, column.name)
        for column in OptionContract.__table__.columns
        if not column.primary_key
    }

    values.update(
        symbol=symbol,
        option_type=option_type,
    )

    contract = OptionContract(**values)
    db_session.add(contract)
    db_session.commit()
    db_session.refresh(contract)

    return contract

def test_csv_export_endpoint_returns_csv(
    client: TestClient,
    db_session: Session,
    test_user: User,
    test_signal: Signal,
    test_option_contract: OptionContract,
):
    """Test that CSV export endpoint returns valid CSV with correct headers."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        # Create a trade
        trade_manager = TradeManager()
        trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db_session,
            quantity=1,
        )
        
        # Test the export endpoint
        response = client.get(f"/api/api/dashboard/trades/export?user_id={test_user.id}")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert f"trades-user-{test_user.id}.csv" in response.headers["content-disposition"]
        
        # Verify CSV content
        csv_content = response.text
        lines = csv_content.strip().split("\n")
        assert len(lines) >= 2  # Header + at least one trade
        
        # Check header
        header = lines[0]
        assert "Trade ID" in header
        assert "Symbol" in header
        assert "Strategy" in header
        assert "Status" in header
        assert "Option Type" in header
        assert "Strike" in header
        assert "Expiration" in header
        assert "Quantity" in header
        assert "Entry Price" in header
        assert "Exit Price" in header
        assert "Realized P/L" in header
        assert "Opened At" in header
        assert "Closed At" in header
        assert "Paper Trade" in header
    finally:
        app.dependency_overrides.clear()


def test_csv_export_filters_by_user(
    client: TestClient,
    db_session: Session,
    test_option_contract: OptionContract,
):
    """Test that CSV export only includes trades for the requested user."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        # Create two users
        user1 = User(
            username="user1",
            email="user1@example.com",
            hashed_password="hashed",
            risk_level="medium",
            paper_trading_enabled=True,
        )
        user2 = User(
            username="user2",
            email="user2@example.com",
            hashed_password="hashed",
            risk_level="medium",
            paper_trading_enabled=True,
        )
        db_session.add_all([user1, user2])
        db_session.commit()
        
        # Create signals for both users with allowed strategies
        signal1 = Signal(
            user_id=user1.id,
            symbol="AAPL",
            strategy_type="covered_call",
            risk_level="medium",
            score=85.0,
            expected_profit=500.0,
            max_loss=550.0,
            probability_estimate=0.7,
            reason="Test",
            status="pending",
            option_contract_id=test_option_contract.id,
            exit_rules="[]",
        )
        signal2 = Signal(
            user_id=user2.id,
            symbol="MSFT",
            strategy_type="cash_secured_put",
            risk_level="medium",
            score=80.0,
            expected_profit=400.0,
            max_loss=450.0,
            probability_estimate=0.65,
            reason="Test",
            status="pending",
            option_contract_id=test_option_contract.id,
            exit_rules="[]",
        )
        db_session.add_all([signal1, signal2])
        db_session.commit()
        
        # Create trades for both users
        trade_manager = TradeManager()
        trade_manager.approve_signal_as_paper_trade(
            user_id=user1.id,
            signal_id=signal1.id,
            db=db_session,
            quantity=1,
        )
        trade_manager.approve_signal_as_paper_trade(
            user_id=user2.id,
            signal_id=signal2.id,
            db=db_session,
            quantity=1,
        )
        
        # Export for user1
        response = client.get(f"/api/api/dashboard/trades/export?user_id={user1.id}")
        
        assert response.status_code == 200
        csv_content = response.text
        
        # Should contain AAPL but not MSFT
        assert "AAPL" in csv_content
        assert "MSFT" not in csv_content
    finally:
        app.dependency_overrides.clear()


def test_csv_export_status_filter_open(
    client: TestClient,
    db_session: Session,
    test_user: User,
    test_option_contract: OptionContract,
):
    """Test that status=open filter excludes closed trades."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        # Create two signals with allowed strategies
        signal1 = Signal(
            user_id=test_user.id,
            symbol="AAPL",
            strategy_type="covered_call",
            risk_level="medium",
            score=85.0,
            expected_profit=500.0,
            max_loss=550.0,
            probability_estimate=0.7,
            reason="Test",
            status="pending",
            option_contract_id=test_option_contract.id,
            exit_rules="[]",
        )
        signal2 = Signal(
            user_id=test_user.id,
            symbol="MSFT",
            strategy_type="cash_secured_put",
            risk_level="medium",
            score=80.0,
            expected_profit=400.0,
            max_loss=450.0,
            probability_estimate=0.65,
            reason="Test",
            status="pending",
            option_contract_id=test_option_contract.id,
            exit_rules="[]",
        )
        db_session.add_all([signal1, signal2])
        db_session.commit()
        
        # Create two trades
        trade_manager = TradeManager()
        trade1 = trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=signal1.id,
            db=db_session,
            quantity=1,
        )
        trade2 = trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=signal2.id,
            db=db_session,
            quantity=1,
        )
        
        # Close trade2
        trade_manager.close_trade(
            user_id=test_user.id,
            trade_id=trade2.id,
            db=db_session,
            exit_price=6.0,
        )
        
        # Export with status=open filter
        response = client.get(f"/api/api/dashboard/trades/export?user_id={test_user.id}&status=open")
        
        assert response.status_code == 200
        csv_content = response.text
        lines = csv_content.strip().split("\n")
        
        # Should have header + 1 open trade
        assert len(lines) == 2
        assert "AAPL" in csv_content
        assert "MSFT" not in csv_content
    finally:
        app.dependency_overrides.clear()


def test_csv_export_status_filter_closed(
    client: TestClient,
    db_session: Session,
    test_user: User,
    test_option_contract: OptionContract,
):
    """Test that status=closed returns only closed trades."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        msft_contract = clone_option_contract(
            db_session,
            test_option_contract,
            symbol="MSFT",
            option_type="put",
        )

        signal1 = Signal(
            user_id=test_user.id,
            symbol="AAPL",
            strategy_type="covered_call",
            risk_level="medium",
            score=85.0,
            expected_profit=500.0,
            max_loss=550.0,
            probability_estimate=0.7,
            reason="Test open trade",
            status="pending",
            option_contract_id=test_option_contract.id,
            exit_rules="[]",
        )

        signal2 = Signal(
            user_id=test_user.id,
            symbol="MSFT",
            strategy_type="cash_secured_put",
            risk_level="medium",
            score=80.0,
            expected_profit=400.0,
            max_loss=450.0,
            probability_estimate=0.65,
            reason="Test closed trade",
            status="pending",
            option_contract_id=msft_contract.id,
            exit_rules="[]",
        )

        db_session.add_all([signal1, signal2])
        db_session.commit()
        db_session.refresh(signal1)
        db_session.refresh(signal2)

        trade_manager = TradeManager()

        trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=signal1.id,
            db=db_session,
            quantity=1,
        )

        closed_trade = trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=signal2.id,
            db=db_session,
            quantity=1,
        )

        trade_manager.close_trade(
            user_id=test_user.id,
            trade_id=closed_trade.id,
            db=db_session,
            exit_price=6.0,
        )

        response = client.get(
            f"/api/api/dashboard/trades/export"
            f"?user_id={test_user.id}&status=closed"
        )

        assert response.status_code == 200

        import csv
        import io

        rows = list(csv.DictReader(io.StringIO(response.text)))

        assert len(rows) == 1
        assert rows[0]["Symbol"] == "MSFT"
        assert rows[0]["Strategy"] == "cash_secured_put"
        assert rows[0]["Status"] == "closed"

    finally:
        app.dependency_overrides.clear()


def test_csv_export_empty_trades(
    client: TestClient,
    db_session: Session,
    test_user: User,
):
    """Test that CSV export returns header-only CSV when user has no trades."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        # Export for user with no trades
        response = client.get(f"/api/api/dashboard/trades/export?user_id={test_user.id}")
        
        assert response.status_code == 200
        csv_content = response.text
        lines = csv_content.strip().split("\n")
        
        # Should have only header
        assert len(lines) == 1
        assert "Trade ID" in lines[0]
    finally:
        app.dependency_overrides.clear()


def test_csv_export_special_characters(
    client: TestClient,
    db_session: Session,
    test_user: User,
    test_option_contract: OptionContract,
):
    """Test that CSV export properly escapes special characters."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        # Create signal with special characters in reason and allowed strategy
        signal = Signal(
            user_id=test_user.id,
            symbol="AAPL",
            strategy_type="covered_call",
            risk_level="medium",
            score=85.0,
            expected_profit=500.0,
            max_loss=550.0,
            probability_estimate=0.7,
            reason='Test with "quotes" and, commas',
            status="pending",
            option_contract_id=test_option_contract.id,
            exit_rules="[]",
        )
        db_session.add(signal)
        db_session.commit()
        
        # Create trade
        trade_manager = TradeManager()
        trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=signal.id,
            db=db_session,
            quantity=1,
        )
        
        # Export
        response = client.get(f"/api/api/dashboard/trades/export?user_id={test_user.id}")
        
        assert response.status_code == 200
        csv_content = response.text
        
        # CSV should be parseable and contain the data
        import csv
        import io
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        
        assert len(rows) == 2  # Header + 1 trade
        assert rows[0][0] == "Trade ID"
        assert rows[1][1] == "AAPL"  # Symbol should be properly parsed
    finally:
        app.dependency_overrides.clear()


def test_csv_export_does_not_modify_trades(
    client: TestClient,
    db_session: Session,
    test_user: User,
    test_signal: Signal,
):
    """Test that CSV export does not modify trade records."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        # Create trade
        trade_manager = TradeManager()
        trade = trade_manager.approve_signal_as_paper_trade(
            user_id=test_user.id,
            signal_id=test_signal.id,
            db=db_session,
            quantity=1,
        )
        
        # Record original values
        original_status = trade.status
        original_updated_at = trade.updated_at
        
        # Export
        response = client.get(f"/api/api/dashboard/trades/export?user_id={test_user.id}")
        
        assert response.status_code == 200
        
        # Verify trade unchanged
        db_session.refresh(trade)
        assert trade.status == original_status
        assert trade.updated_at == original_updated_at
    finally:
        app.dependency_overrides.clear()
