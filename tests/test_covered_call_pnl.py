"""Tests for covered call P/L calculations.

Verifies that covered call positions correctly calculate combined P/L
including both underlying stock and option components, as specified in
issue #240.
"""

import pytest
from datetime import datetime, timedelta
from app.models.database import Trade, User
from app.trading.trade_manager import TradeManager
from sqlalchemy.orm import Session


class TestCoveredCallPnL:
    """Test covered call P/L calculations."""

    def test_option_profitable_stock_losing(self, db_session: Session):
        """Test scenario where option is profitable but stock is losing.
        
        Stock Entry:       $17.87
        Current Stock:     $16.50
        Option Entry:       $1.54
        Current Option:     $0.72
        
        Stock P/L:         -$137
        Option P/L:         +$82
        Total P/L:          -$55
        
        Expected: Total P/L = -$55 (not +$82)
        """
        # Create test user
        user = User(
            username="test_user",
            email="test@example.com",
            hashed_password="hashed",
            initial_portfolio_value=100000.0
        )
        db_session.add(user)
        db_session.commit()
        
        # Create covered call trade
        trade = Trade(
            user_id=user.id,
            symbol="SOFI",
            strategy_type="covered_call",
            status="open",
            quantity=1,
            entry_price=1.54,
            current_price=0.72,
            strike_price=18.50,
            expiration=datetime.now() + timedelta(days=30),
            underlying_entry_price=17.87,
            underlying_current_price=16.50,
            underlying_quantity=100,
            option_type="call",
            position_type="short"
        )
        db_session.add(trade)
        db_session.commit()
        
        # Calculate P/L
        trade_manager = TradeManager(db_session)
        trade_manager.update_trade_pnl(trade)
        
        # Verify calculations
        assert trade.stock_pnl == pytest.approx(-137.0, abs=0.01), "Stock P/L should be -$137"
        assert trade.option_pnl == pytest.approx(82.0, abs=0.01), "Option P/L should be +$82"
        assert trade.pnl == pytest.approx(-55.0, abs=0.01), "Total P/L should be -$55"
        assert trade.pnl < 0, "Total position should be losing money"
        assert trade.option_pnl > 0, "Option leg should be profitable"

    def test_stock_and_option_both_profitable(self, db_session: Session):
        """Test scenario where both stock and option are profitable.
        
        Stock Entry:       $17.87
        Current Stock:     $18.20
        Option Entry:       $1.54
        Current Option:     $1.00
        
        Stock P/L:          +$33
        Option P/L:          +$54
        Total P/L:           +$87
        
        Expected: Total P/L = +$87
        """
        user = User(
            username="test_user2",
            email="test2@example.com",
            hashed_password="hashed",
            initial_portfolio_value=100000.0
        )
        db_session.add(user)
        db_session.commit()
        
        trade = Trade(
            user_id=user.id,
            symbol="SOFI",
            strategy_type="covered_call",
            status="open",
            quantity=1,
            entry_price=1.54,
            current_price=1.00,
            strike_price=18.50,
            expiration=datetime.now() + timedelta(days=30),
            underlying_entry_price=17.87,
            underlying_current_price=18.20,
            underlying_quantity=100,
            option_type="call",
            position_type="short"
        )
        db_session.add(trade)
        db_session.commit()
        
        trade_manager = TradeManager(db_session)
        trade_manager.update_trade_pnl(trade)
        
        assert trade.stock_pnl == pytest.approx(33.0, abs=0.01), "Stock P/L should be +$33"
        assert trade.option_pnl == pytest.approx(54.0, abs=0.01), "Option P/L should be +$54"
        assert trade.pnl == pytest.approx(87.0, abs=0.01), "Total P/L should be +$87"

    def test_maximum_profit_calculation(self, db_session: Session):
        """Test maximum profit calculation for covered call.
        
        Stock Entry:       $17.87
        Strike:            $18.50
        Premium:            $1.54
        Quantity:                1
        
        Stock appreciation: ($18.50 - $17.87) * 100 = $63
        Premium received: $1.54 * 100 = $154
        Maximum Profit: $63 + $154 = $217
        """
        user = User(
            username="test_user3",
            email="test3@example.com",
            hashed_password="hashed",
            initial_portfolio_value=100000.0
        )
        db_session.add(user)
        db_session.commit()
        
        trade = Trade(
            user_id=user.id,
            symbol="SOFI",
            strategy_type="covered_call",
            status="open",
            quantity=1,
            entry_price=1.54,
            current_price=1.54,
            strike_price=18.50,
            expiration=datetime.now() + timedelta(days=30),
            underlying_entry_price=17.87,
            underlying_current_price=17.87,
            underlying_quantity=100,
            option_type="call",
            position_type="short"
        )
        db_session.add(trade)
        db_session.commit()
        
        trade_manager = TradeManager(db_session)
        details = trade_manager.get_trade_details(trade)
        
        max_profit = details.get('max_profit', 0.0)
        assert max_profit == pytest.approx(217.0, abs=0.01), "Maximum profit should be $217"

    def test_break_even_calculation(self, db_session: Session):
        """Test break-even calculation for covered call.
        
        Stock Entry:       $17.87
        Premium:            $1.54
        
        Break-even: $17.87 - $1.54 = $16.33
        """
        user = User(
            username="test_user4",
            email="test4@example.com",
            hashed_password="hashed",
            initial_portfolio_value=100000.0
        )
        db_session.add(user)
        db_session.commit()
        
        trade = Trade(
            user_id=user.id,
            symbol="SOFI",
            strategy_type="covered_call",
            status="open",
            quantity=1,
            entry_price=1.54,
            current_price=1.54,
            strike_price=18.50,
            expiration=datetime.now() + timedelta(days=30),
            underlying_entry_price=17.87,
            underlying_current_price=17.87,
            underlying_quantity=100,
            option_type="call",
            position_type="short"
        )
        db_session.add(trade)
        db_session.commit()
        
        trade_manager = TradeManager(db_session)
        details = trade_manager.get_trade_details(trade)
        
        break_even = details.get('break_even', 0.0)
        assert break_even == pytest.approx(16.33, abs=0.01), "Break-even should be $16.33"

    def test_premium_captured_vs_total_return(self, db_session: Session):
        """Test that premium captured % differs from total return %.
        
        Premium captured % = option P/L / premium received
        Total return % = total P/L / net capital at risk
        """
        user = User(
            username="test_user5",
            email="test5@example.com",
            hashed_password="hashed",
            initial_portfolio_value=100000.0
        )
        db_session.add(user)
        db_session.commit()
        
        trade = Trade(
            user_id=user.id,
            symbol="SOFI",
            strategy_type="covered_call",
            status="open",
            quantity=1,
            entry_price=1.54,
            current_price=0.72,
            strike_price=18.50,
            expiration=datetime.now() + timedelta(days=30),
            underlying_entry_price=17.87,
            underlying_current_price=16.50,
            underlying_quantity=100,
            option_type="call",
            position_type="short"
        )
        db_session.add(trade)
        db_session.commit()
        
        trade_manager = TradeManager(db_session)
        trade_manager.update_trade_pnl(trade)
        details = trade_manager.get_trade_details(trade)
        
        premium_captured_pct = details.get('premium_captured_pct', 0.0)
        total_return_pct = details.get('total_return_pct', 0.0)
        
        # Premium captured should be positive (option profitable)
        assert premium_captured_pct > 0, "Premium captured % should be positive"
        
        # Total return should be negative (overall position losing)
        assert total_return_pct < 0, "Total return % should be negative"
        
        # They should be different values
        assert premium_captured_pct != total_return_pct, "Premium captured % should differ from total return %"

    def test_portfolio_pnl_no_double_counting(self, db_session: Session):
        """Test that portfolio P/L doesn't double-count underlying shares."""
        user = User(
            username="test_user6",
            email="test6@example.com",
            hashed_password="hashed",
            initial_portfolio_value=100000.0
        )
        db_session.add(user)
        db_session.commit()
        
        # Create two covered call trades
        trade1 = Trade(
            user_id=user.id,
            symbol="SOFI",
            strategy_type="covered_call",
            status="open",
            quantity=1,
            entry_price=1.54,
            current_price=0.72,
            strike_price=18.50,
            expiration=datetime.now() + timedelta(days=30),
            underlying_entry_price=17.87,
            underlying_current_price=16.50,
            underlying_quantity=100,
            option_type="call",
            position_type="short"
        )
        
        trade2 = Trade(
            user_id=user.id,
            symbol="AAPL",
            strategy_type="covered_call",
            status="open",
            quantity=1,
            entry_price=2.00,
            current_price=1.50,
            strike_price=150.00,
            expiration=datetime.now() + timedelta(days=30),
            underlying_entry_price=145.00,
            underlying_current_price=148.00,
            underlying_quantity=100,
            option_type="call",
            position_type="short"
        )
        
        db_session.add(trade1)
        db_session.add(trade2)
        db_session.commit()
        
        trade_manager = TradeManager(db_session)
        trade_manager.update_trade_pnl(trade1)
        trade_manager.update_trade_pnl(trade2)
        
        # Calculate portfolio P/L
        portfolio_pnl = trade1.pnl + trade2.pnl
        portfolio_option_pnl = trade1.option_pnl + trade2.option_pnl
        portfolio_stock_pnl = trade1.stock_pnl + trade2.stock_pnl
        
        # Verify components sum correctly
        assert portfolio_pnl == pytest.approx(portfolio_option_pnl + portfolio_stock_pnl, abs=0.01)
        
        # Verify each trade's P/L is the sum of its components
        assert trade1.pnl == pytest.approx(trade1.option_pnl + trade1.stock_pnl, abs=0.01)
        assert trade2.pnl == pytest.approx(trade2.option_pnl + trade2.stock_pnl, abs=0.01)
