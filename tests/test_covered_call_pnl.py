"""Tests for covered call P/L calculations.

Verifies that covered call positions correctly calculate:
1. Stock P/L (underlying shares)
2. Option P/L (short call)
3. Combined total P/L
4. Premium captured %
5. Total return %
6. Break-even price
7. Maximum profit

Tests cover scenarios from issue #240:
- Option profitable, stock losing (total negative)
- Both stock and option profitable
- Maximum profit calculation
- Break-even calculation
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from app.models.database import Trade, User
from app.trading.trade_manager import TradeManager
from sqlalchemy.orm import Session


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed",
        initial_portfolio_value=100000.0
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def trade_manager(db_session: Session) -> TradeManager:
    """Create a TradeManager instance."""
    return TradeManager(db_session)


def test_covered_call_option_profitable_stock_losing(db_session: Session, test_user: User, trade_manager: TradeManager):
    """Test covered call where option is profitable but stock is losing.
    
    Scenario from issue:
    Stock Entry:       $17.87
    Current Stock:     $16.50
    Option Entry:       $1.54
    Current Option:     $0.72
    
    Stock P/L:         -$137
    Option P/L:         +$82
    Total P/L:          -$55
    
    Expected: Total P/L = -$55 (NOT +$82)
    """
    # Create covered call trade
    trade = Trade(
        user_id=test_user.id,
        symbol="SOFI",
        strategy_type="covered_call",
        status="open",
        quantity=1,
        entry_price=1.54,  # Option premium received
        current_price=0.72,  # Current option price
        strike_price=18.50,
        expiration_date=(datetime.utcnow() + timedelta(days=180)).date(),
        underlying_entry_price=17.87,  # Stock entry price
        underlying_current_price=16.50,  # Current stock price
        underlying_quantity=100,
        premium_received=154.0,  # $1.54 * 100
        opened_at=datetime.utcnow()
    )
    db_session.add(trade)
    db_session.commit()
    db_session.refresh(trade)
    
    # Calculate P/L
    trade_manager.update_trade_pnl(trade)
    db_session.refresh(trade)
    
    # Verify stock P/L
    expected_stock_pnl = (16.50 - 17.87) * 100
    assert abs(trade.stock_pnl - expected_stock_pnl) < 0.01, f"Stock P/L should be {expected_stock_pnl}, got {trade.stock_pnl}"
    assert trade.stock_pnl < 0, "Stock P/L should be negative"
    assert abs(trade.stock_pnl - (-137.0)) < 0.01, f"Stock P/L should be -$137, got {trade.stock_pnl}"
    
    # Verify option P/L (short call: profit when price decreases)
    expected_option_pnl = (1.54 - 0.72) * 100
    assert abs(trade.option_pnl - expected_option_pnl) < 0.01, f"Option P/L should be {expected_option_pnl}, got {trade.option_pnl}"
    assert trade.option_pnl > 0, "Option P/L should be positive"
    assert abs(trade.option_pnl - 82.0) < 0.01, f"Option P/L should be +$82, got {trade.option_pnl}"
    
    # Verify total P/L (MUST be negative, not positive)
    expected_total_pnl = expected_stock_pnl + expected_option_pnl
    assert abs(trade.unrealized_pnl - expected_total_pnl) < 0.01, f"Total P/L should be {expected_total_pnl}, got {trade.unrealized_pnl}"
    assert trade.unrealized_pnl < 0, "Total P/L MUST be negative when stock losses exceed option gains"
    assert abs(trade.unrealized_pnl - (-55.0)) < 0.01, f"Total P/L should be -$55, got {trade.unrealized_pnl}"
    
    # Get detailed metrics
    details = trade_manager.get_trade_details(trade)
    
    # Verify premium captured %
    premium_captured_pct = details.get('premium_captured_pct', 0.0)
    expected_premium_pct = (82.0 / 154.0) * 100
    assert abs(premium_captured_pct - expected_premium_pct) < 0.1, f"Premium captured should be ~53%, got {premium_captured_pct}%"
    
    # Verify total return % (should be negative)
    total_return_pct = details.get('total_return_pct', 0.0)
    assert total_return_pct < 0, "Total return % should be negative"


def test_covered_call_both_profitable(db_session: Session, test_user: User, trade_manager: TradeManager):
    """Test covered call where both stock and option are profitable.
    
    Scenario from issue:
    Stock Entry:       $17.87
    Current Stock:     $18.20
    Option Entry:       $1.54
    Current Option:     $1.00
    
    Stock P/L:          +$33
    Option P/L:          +$54
    Total P/L:           +$87
    """
    trade = Trade(
        user_id=test_user.id,
        symbol="SOFI",
        strategy_type="covered_call",
        status="open",
        quantity=1,
        entry_price=1.54,
        current_price=1.00,
        strike_price=18.50,
        expiration_date=(datetime.utcnow() + timedelta(days=180)).date(),
        underlying_entry_price=17.87,
        underlying_current_price=18.20,
        underlying_quantity=100,
        premium_received=154.0,
        opened_at=datetime.utcnow()
    )
    db_session.add(trade)
    db_session.commit()
    db_session.refresh(trade)
    
    # Calculate P/L
    trade_manager.update_trade_pnl(trade)
    db_session.refresh(trade)
    
    # Verify stock P/L
    expected_stock_pnl = (18.20 - 17.87) * 100
    assert abs(trade.stock_pnl - expected_stock_pnl) < 0.01
    assert abs(trade.stock_pnl - 33.0) < 0.01, f"Stock P/L should be +$33, got {trade.stock_pnl}"
    
    # Verify option P/L
    expected_option_pnl = (1.54 - 1.00) * 100
    assert abs(trade.option_pnl - expected_option_pnl) < 0.01
    assert abs(trade.option_pnl - 54.0) < 0.01, f"Option P/L should be +$54, got {trade.option_pnl}"
    
    # Verify total P/L
    expected_total_pnl = 33.0 + 54.0
    assert abs(trade.unrealized_pnl - expected_total_pnl) < 0.01
    assert abs(trade.unrealized_pnl - 87.0) < 0.01, f"Total P/L should be +$87, got {trade.unrealized_pnl}"


def test_covered_call_maximum_profit(db_session: Session, test_user: User, trade_manager: TradeManager):
    """Test maximum profit calculation for covered call.
    
    Scenario from issue:
    Stock Entry:       $17.87
    Strike:            $18.50
    Premium:            $1.54
    Quantity:                1
    
    Expected Maximum Profit: $217
    (Stock appreciation: $63 + Premium: $154 = $217)
    """
    trade = Trade(
        user_id=test_user.id,
        symbol="SOFI",
        strategy_type="covered_call",
        status="open",
        quantity=1,
        entry_price=1.54,
        current_price=1.54,
        strike_price=18.50,
        expiration_date=(datetime.utcnow() + timedelta(days=180)).date(),
        underlying_entry_price=17.87,
        underlying_current_price=17.87,
        underlying_quantity=100,
        premium_received=154.0,
        opened_at=datetime.utcnow()
    )
    db_session.add(trade)
    db_session.commit()
    db_session.refresh(trade)
    
    # Get trade details
    details = trade_manager.get_trade_details(trade)
    
    # Verify maximum profit
    max_profit = details.get('max_profit', 0.0)
    stock_appreciation = (18.50 - 17.87) * 100  # $63
    expected_max_profit = stock_appreciation + 154.0  # $217
    
    assert abs(max_profit - expected_max_profit) < 0.01, f"Max profit should be ${expected_max_profit:.2f}, got ${max_profit:.2f}"
    assert abs(max_profit - 217.0) < 0.01, f"Max profit should be $217, got ${max_profit:.2f}"


def test_covered_call_break_even(db_session: Session, test_user: User, trade_manager: TradeManager):
    """Test break-even calculation for covered call.
    
    Scenario from issue:
    Stock Entry:       $17.87
    Premium:            $1.54
    
    Expected Break-even: $16.33
    ($17.87 - $1.54 = $16.33)
    """
    trade = Trade(
        user_id=test_user.id,
        symbol="SOFI",
        strategy_type="covered_call",
        status="open",
        quantity=1,
        entry_price=1.54,
        current_price=1.54,
        strike_price=18.50,
        expiration_date=(datetime.utcnow() + timedelta(days=180)).date(),
        underlying_entry_price=17.87,
        underlying_current_price=17.87,
        underlying_quantity=100,
        premium_received=154.0,
        opened_at=datetime.utcnow()
    )
    db_session.add(trade)
    db_session.commit()
    db_session.refresh(trade)
    
    # Get trade details
    details = trade_manager.get_trade_details(trade)
    
    # Verify break-even
    break_even = details.get('break_even', 0.0)
    expected_break_even = 17.87 - 1.54  # $16.33
    
    assert abs(break_even - expected_break_even) < 0.01, f"Break-even should be ${expected_break_even:.2f}, got ${break_even:.2f}"
    assert abs(break_even - 16.33) < 0.01, f"Break-even should be $16.33, got ${break_even:.2f}"


def test_covered_call_premium_captured_vs_total_return(db_session: Session, test_user: User, trade_manager: TradeManager):
    """Test that premium captured % differs from total return %.
    
    Premium captured % = option P/L / premium received
    Total return % = total P/L / net capital at risk
    
    These should be different metrics.
    """
    trade = Trade(
        user_id=test_user.id,
        symbol="SOFI",
        strategy_type="covered_call",
        status="open",
        quantity=1,
        entry_price=1.54,
        current_price=0.72,
        strike_price=18.50,
        expiration_date=(datetime.utcnow() + timedelta(days=180)).date(),
        underlying_entry_price=17.87,
        underlying_current_price=16.50,
        underlying_quantity=100,
        premium_received=154.0,
        opened_at=datetime.utcnow()
    )
    db_session.add(trade)
    db_session.commit()
    db_session.refresh(trade)
    
    # Calculate P/L
    trade_manager.update_trade_pnl(trade)
    db_session.refresh(trade)
    
    # Get detailed metrics
    details = trade_manager.get_trade_details(trade)
    
    premium_captured_pct = details.get('premium_captured_pct', 0.0)
    total_return_pct = details.get('total_return_pct', 0.0)
    
    # Premium captured should be positive (~53%)
    assert premium_captured_pct > 0, "Premium captured % should be positive"
    assert abs(premium_captured_pct - 53.25) < 1.0, f"Premium captured should be ~53%, got {premium_captured_pct}%"
    
    # Total return should be negative (overall position losing)
    assert total_return_pct < 0, "Total return % should be negative when position is losing"
    
    # They should be different
    assert abs(premium_captured_pct - total_return_pct) > 10, "Premium captured % and total return % should differ significantly"


def test_portfolio_no_double_counting(db_session: Session, test_user: User, trade_manager: TradeManager):
    """Test that portfolio P/L doesn't double-count underlying shares.
    
    If a covered call exists, the underlying shares should only be counted once
    in the portfolio P/L calculation.
    """
    # Create two covered calls on different symbols
    trade1 = Trade(
        user_id=test_user.id,
        symbol="SOFI",
        strategy_type="covered_call",
        status="open",
        quantity=1,
        entry_price=1.54,
        current_price=0.72,
        strike_price=18.50,
        expiration_date=(datetime.utcnow() + timedelta(days=180)).date(),
        underlying_entry_price=17.87,
        underlying_current_price=16.50,
        underlying_quantity=100,
        premium_received=154.0,
        opened_at=datetime.utcnow()
    )
    
    trade2 = Trade(
        user_id=test_user.id,
        symbol="AAPL",
        strategy_type="covered_call",
        status="open",
        quantity=1,
        entry_price=5.00,
        current_price=3.00,
        strike_price=180.00,
        expiration_date=(datetime.utcnow() + timedelta(days=180)).date(),
        underlying_entry_price=175.00,
        underlying_current_price=178.00,
        underlying_quantity=100,
        premium_received=500.0,
        opened_at=datetime.utcnow()
    )
    
    db_session.add_all([trade1, trade2])
    db_session.commit()
    
    # Calculate P/L for both trades
    trade_manager.update_trade_pnl(trade1)
    trade_manager.update_trade_pnl(trade2)
    db_session.refresh(trade1)
    db_session.refresh(trade2)
    
    # Get portfolio summary
    summary = trade_manager.get_portfolio_summary(test_user.id)
    
    # Verify separate tracking
    total_option_pnl = summary.get('option_pnl', 0.0)
    total_stock_pnl = summary.get('stock_pnl', 0.0)
    total_pnl = summary.get('total_unrealized_pnl', 0.0)
    
    # Total should equal sum of individual trades
    expected_total = trade1.unrealized_pnl + trade2.unrealized_pnl
    assert abs(total_pnl - expected_total) < 0.01, "Portfolio total should equal sum of individual trade P/Ls"
    
    # Option and stock P/L should be tracked separately
    expected_option_pnl = trade1.option_pnl + trade2.option_pnl
    expected_stock_pnl = trade1.stock_pnl + trade2.stock_pnl
    
    assert abs(total_option_pnl - expected_option_pnl) < 0.01, "Portfolio option P/L should equal sum of individual option P/Ls"
    assert abs(total_stock_pnl - expected_stock_pnl) < 0.01, "Portfolio stock P/L should equal sum of individual stock P/Ls"
    
    # Combined should equal total
    assert abs((total_option_pnl + total_stock_pnl) - total_pnl) < 0.01, "Option P/L + Stock P/L should equal Total P/L"
