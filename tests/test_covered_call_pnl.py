"""Tests for covered call P/L calculations.

Tests verify that covered call P/L includes both:
1. Option leg P/L (short call)
2. Underlying stock leg P/L
3. Combined total P/L

Tests cover scenarios where:
- Option is profitable but stock is losing (net loss)
- Both option and stock are profitable (net profit)
- Maximum profit calculation includes stock appreciation
- Break-even calculation includes premium received
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.database import User, Signal, Trade, OptionContract
from app.trading.trade_manager import TradeManager
from app.core.database import get_db


@pytest.fixture
def db_session():
    """Create a test database session."""
    db = next(get_db())
    yield db
    db.close()


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user."""
    user = User(
        username="test_covered_call_user",
        email="test_cc@example.com",
        hashed_password="hashed",
        risk_level="medium",
        paper_trading_enabled=True,
        initial_portfolio_value=100000.0,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_option_contract(db_session: Session):
    """Create a test option contract for SOFI covered call."""
    contract = OptionContract(
        symbol="SOFI",
        underlying_symbol="SOFI",
        expiration="2026-08-14",
        strike=18.50,
        contract_type="call",
        bid=0.70,
        ask=0.74,
        last=0.72,
        volume=100,
        open_interest=500,
        implied_volatility=0.45,
        delta=0.35,
        theta=-0.02,
        underlying_price=17.87,
        days_to_expiration=30,
    )
    db_session.add(contract)
    db_session.commit()
    db_session.refresh(contract)
    return contract


@pytest.fixture
def test_signal(db_session: Session, test_user: User, test_option_contract: OptionContract):
    """Create a test covered call signal."""
    signal = Signal(
        user_id=test_user.id,
        symbol="SOFI",
        strategy_type="covered_call",
        risk_level="medium",
        score=0.75,
        expected_profit=154.0,
        max_loss=-1787.0,
        probability_estimate=0.65,
        reason="Covered call opportunity on SOFI",
        status="pending",
        option_contract_id=test_option_contract.id,
    )
    db_session.add(signal)
    db_session.commit()
    db_session.refresh(signal)
    return signal


def test_covered_call_option_profitable_stock_losing(db_session: Session, test_user: User, test_signal: Signal):
    """Test covered call where option is profitable but stock is losing.
    
    Scenario:
    - Stock entry: $17.87
    - Current stock: $16.50
    - Option entry: $1.54
    - Current option: $0.72
    
    Expected:
    - Stock P/L: -$137
    - Option P/L: +$82
    - Total P/L: -$55
    """
    trade_manager = TradeManager(db=db_session)
    
    # Execute trade
    trade = trade_manager.execute_trade(
        user_id=test_user.id,
        signal_id=test_signal.id,
        quantity=1,
        is_paper_trade=True,
        underlying_entry_price=17.87,
        underlying_quantity=100,
    )
    
    assert trade is not None
    assert trade.strategy_type == "covered_call"
    assert trade.underlying_entry_price == 17.87
    assert trade.underlying_quantity == 100
    
    # Update prices to simulate market movement
    trade = trade_manager.update_trade_prices(
        trade_id=trade.id,
        current_option_price=0.72,
        current_stock_price=16.50,
    )
    
    # Verify P/L calculations
    assert trade.option_pnl is not None
    assert trade.stock_pnl is not None
    assert trade.unrealized_pnl is not None
    
    # Option P/L: (1.54 - 0.72) * 100 = +82
    assert abs(trade.option_pnl - 82.0) < 0.01
    
    # Stock P/L: (16.50 - 17.87) * 100 = -137
    assert abs(trade.stock_pnl - (-137.0)) < 0.01
    
    # Total P/L: 82 + (-137) = -55
    assert abs(trade.unrealized_pnl - (-55.0)) < 0.01
    
    # Verify the position is showing as losing overall
    assert trade.unrealized_pnl < 0, "Total P/L should be negative"


def test_covered_call_both_profitable(db_session: Session, test_user: User, test_signal: Signal):
    """Test covered call where both option and stock are profitable.
    
    Scenario:
    - Stock entry: $17.87
    - Current stock: $18.20
    - Option entry: $1.54
    - Current option: $1.00
    
    Expected:
    - Stock P/L: +$33
    - Option P/L: +$54
    - Total P/L: +$87
    """
    trade_manager = TradeManager(db=db_session)
    
    # Execute trade
    trade = trade_manager.execute_trade(
        user_id=test_user.id,
        signal_id=test_signal.id,
        quantity=1,
        is_paper_trade=True,
        underlying_entry_price=17.87,
        underlying_quantity=100,
    )
    
    # Update prices
    trade = trade_manager.update_trade_prices(
        trade_id=trade.id,
        current_option_price=1.00,
        current_stock_price=18.20,
    )
    
    # Verify P/L calculations
    # Option P/L: (1.54 - 1.00) * 100 = +54
    assert abs(trade.option_pnl - 54.0) < 0.01
    
    # Stock P/L: (18.20 - 17.87) * 100 = +33
    assert abs(trade.stock_pnl - 33.0) < 0.01
    
    # Total P/L: 54 + 33 = +87
    assert abs(trade.unrealized_pnl - 87.0) < 0.01
    
    # Verify the position is showing as profitable
    assert trade.unrealized_pnl > 0, "Total P/L should be positive"


def test_covered_call_max_profit_calculation(db_session: Session, test_user: User, test_signal: Signal):
    """Test maximum profit calculation includes stock appreciation.
    
    Scenario:
    - Stock entry: $17.87
    - Strike: $18.50
    - Premium: $1.54
    
    Expected:
    - Stock appreciation: ($18.50 - $17.87) * 100 = $63
    - Premium received: $1.54 * 100 = $154
    - Maximum profit: $63 + $154 = $217
    """
    trade_manager = TradeManager(db=db_session)
    
    # Execute trade
    trade = trade_manager.execute_trade(
        user_id=test_user.id,
        signal_id=test_signal.id,
        quantity=1,
        is_paper_trade=True,
        underlying_entry_price=17.87,
        underlying_quantity=100,
    )
    
    # Get trade details
    details = trade_manager.get_trade_details(trade.id)
    
    assert details is not None
    assert "max_profit" in details
    assert "premium_received" in details
    assert "strike" in details
    
    # Verify premium received
    assert abs(details["premium_received"] - 154.0) < 0.01
    
    # Verify maximum profit includes stock appreciation
    # Stock appreciation: (18.50 - 17.87) * 100 = 63
    # Total max profit: 63 + 154 = 217
    assert abs(details["max_profit"] - 217.0) < 0.01


def test_covered_call_break_even_calculation(db_session: Session, test_user: User, test_signal: Signal):
    """Test break-even calculation includes premium received.
    
    Scenario:
    - Stock entry: $17.87
    - Premium: $1.54
    
    Expected:
    - Break-even: $17.87 - $1.54 = $16.33
    """
    trade_manager = TradeManager(db=db_session)
    
    # Execute trade
    trade = trade_manager.execute_trade(
        user_id=test_user.id,
        signal_id=test_signal.id,
        quantity=1,
        is_paper_trade=True,
        underlying_entry_price=17.87,
        underlying_quantity=100,
    )
    
    # Get trade details
    details = trade_manager.get_trade_details(trade.id)
    
    assert details is not None
    assert "break_even" in details
    
    # Verify break-even calculation
    # Break-even: 17.87 - 1.54 = 16.33
    assert abs(details["break_even"] - 16.33) < 0.01


def test_covered_call_premium_captured_percentage(db_session: Session, test_user: User, test_signal: Signal):
    """Test premium captured percentage is separate from total return.
    
    Scenario:
    - Premium received: $154
    - Option P/L: +$82
    
    Expected:
    - Premium captured: 82 / 154 = 53.25%
    """
    trade_manager = TradeManager(db=db_session)
    
    # Execute trade
    trade = trade_manager.execute_trade(
        user_id=test_user.id,
        signal_id=test_signal.id,
        quantity=1,
        is_paper_trade=True,
        underlying_entry_price=17.87,
        underlying_quantity=100,
    )
    
    # Update prices
    trade = trade_manager.update_trade_prices(
        trade_id=trade.id,
        current_option_price=0.72,
        current_stock_price=16.50,
    )
    
    # Get trade details
    details = trade_manager.get_trade_details(trade.id)
    
    assert details is not None
    assert "premium_captured_pct" in details
    assert "total_return_pct" in details
    
    # Verify premium captured percentage
    # Option P/L: 82, Premium: 154
    # Premium captured: 82 / 154 = 53.25%
    assert abs(details["premium_captured_pct"] - 53.25) < 0.1
    
    # Verify total return is different (and negative in this case)
    assert details["total_return_pct"] != details["premium_captured_pct"]
    assert details["total_return_pct"] < 0, "Total return should be negative when position is losing"


def test_portfolio_summary_no_double_counting(db_session: Session, test_user: User, test_signal: Signal):
    """Test portfolio summary doesn't double-count stock holdings.
    
    Verifies that covered call P/L includes both legs but doesn't
    create duplicate stock positions in portfolio value.
    """
    trade_manager = TradeManager(db=db_session)
    
    # Execute trade
    trade = trade_manager.execute_trade(
        user_id=test_user.id,
        signal_id=test_signal.id,
        quantity=1,
        is_paper_trade=True,
        underlying_entry_price=17.87,
        underlying_quantity=100,
    )
    
    # Update prices
    trade = trade_manager.update_trade_prices(
        trade_id=trade.id,
        current_option_price=0.72,
        current_stock_price=16.50,
    )
    
    # Get portfolio summary
    summary = trade_manager.get_portfolio_summary(test_user.id)
    
    assert summary is not None
    assert "total_unrealized_pnl" in summary
    assert "option_pnl" in summary
    assert "stock_pnl" in summary
    
    # Verify combined P/L matches trade P/L
    assert abs(summary["total_unrealized_pnl"] - trade.unrealized_pnl) < 0.01
    
    # Verify option and stock P/L are tracked separately
    assert abs(summary["option_pnl"] - trade.option_pnl) < 0.01
    assert abs(summary["stock_pnl"] - trade.stock_pnl) < 0.01
    
    # Verify total equals sum of components
    assert abs(summary["total_unrealized_pnl"] - (summary["option_pnl"] + summary["stock_pnl"])) < 0.01


def test_covered_call_without_underlying_price(db_session: Session, test_user: User, test_signal: Signal):
    """Test covered call handles missing underlying entry price gracefully.
    
    When underlying entry price is not provided, should use current price
    as estimated basis with appropriate warning.
    """
    trade_manager = TradeManager(db=db_session)
    
    # Execute trade without underlying entry price
    trade = trade_manager.execute_trade(
        user_id=test_user.id,
        signal_id=test_signal.id,
        quantity=1,
        is_paper_trade=True,
        # underlying_entry_price not provided
    )
    
    assert trade is not None
    assert trade.underlying_entry_price is not None, "Should fallback to current price"
    assert trade.underlying_quantity == 100, "Should default to 100 shares per contract"
    
    # Should still calculate P/L (though it will be zero initially)
    assert trade.option_pnl is not None
    assert trade.stock_pnl is not None
    assert trade.unrealized_pnl is not None
