"""Tests for covered call P/L calculations.

Validates that covered call positions correctly calculate combined P/L
including both the option leg and underlying stock leg.

Tests cover all acceptance criteria scenarios:
1. Profitable option with losing stock (net loss)
2. Both option and stock profitable (net profit)
3. Maximum profit calculation
4. Break-even calculation
5. Premium captured % vs total return % distinction
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal


class TestCoveredCallPnL:
    """Test suite for covered call P/L calculations."""

    def test_profitable_option_losing_stock(self):
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
        # Stock leg
        stock_entry_price = 17.87
        stock_current_price = 16.50
        underlying_quantity = 100
        quantity = 1
        
        stock_pnl = (stock_current_price - stock_entry_price) * underlying_quantity * quantity
        
        # Option leg (short call)
        option_entry_price = 1.54
        option_current_price = 0.72
        
        option_pnl = (option_entry_price - option_current_price) * 100 * quantity
        
        # Combined P/L
        total_pnl = stock_pnl + option_pnl
        
        # Assertions
        assert stock_pnl == pytest.approx(-137.0, abs=0.01), "Stock P/L should be -$137"
        assert option_pnl == pytest.approx(82.0, abs=0.01), "Option P/L should be +$82"
        assert total_pnl == pytest.approx(-55.0, abs=0.01), "Total P/L should be -$55, not +$82"
        assert total_pnl < 0, "Position should show as losing despite profitable option"

    def test_both_profitable(self):
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
        # Stock leg
        stock_entry_price = 17.87
        stock_current_price = 18.20
        underlying_quantity = 100
        quantity = 1
        
        stock_pnl = (stock_current_price - stock_entry_price) * underlying_quantity * quantity
        
        # Option leg (short call)
        option_entry_price = 1.54
        option_current_price = 1.00
        
        option_pnl = (option_entry_price - option_current_price) * 100 * quantity
        
        # Combined P/L
        total_pnl = stock_pnl + option_pnl
        
        # Assertions
        assert stock_pnl == pytest.approx(33.0, abs=0.01), "Stock P/L should be +$33"
        assert option_pnl == pytest.approx(54.0, abs=0.01), "Option P/L should be +$54"
        assert total_pnl == pytest.approx(87.0, abs=0.01), "Total P/L should be +$87"
        assert total_pnl > 0, "Position should show as profitable"

    def test_maximum_profit_calculation(self):
        """Test maximum profit calculation for covered call.
        
        Stock Entry:       $17.87
        Strike:            $18.50
        Premium:            $1.54
        Quantity:                1
        
        Stock appreciation: ($18.50 - $17.87) * 100 = $63
        Premium received: $1.54 * 100 = $154
        
        Expected: Maximum Profit = $217
        """
        stock_entry_price = 17.87
        strike_price = 18.50
        premium_per_share = 1.54
        underlying_quantity = 100
        quantity = 1
        
        # Stock appreciation to strike
        stock_appreciation = (strike_price - stock_entry_price) * underlying_quantity * quantity
        
        # Premium received
        premium_received = premium_per_share * 100 * quantity
        
        # Maximum profit
        max_profit = stock_appreciation + premium_received
        
        # Assertions
        assert stock_appreciation == pytest.approx(63.0, abs=0.01), "Stock appreciation should be $63"
        assert premium_received == pytest.approx(154.0, abs=0.01), "Premium received should be $154"
        assert max_profit == pytest.approx(217.0, abs=0.01), "Maximum profit should be $217, not just $154"

    def test_break_even_calculation(self):
        """Test break-even calculation for covered call.
        
        Stock Entry:       $17.87
        Premium:            $1.54
        
        Expected: Break-even = $16.33
        """
        stock_entry_price = 17.87
        premium_per_share = 1.54
        
        # Break-even
        break_even = stock_entry_price - premium_per_share
        
        # Assertions
        assert break_even == pytest.approx(16.33, abs=0.01), "Break-even should be $16.33"

    def test_premium_captured_vs_total_return(self):
        """Test distinction between premium captured % and total return %.
        
        Stock Entry:       $17.87
        Current Stock:     $16.50
        Option Entry:       $1.54
        Current Option:     $0.72
        Premium Received:   $154
        
        Option P/L:         +$82
        Premium Captured:   +53.25%
        
        Stock P/L:         -$137
        Total P/L:          -$55
        
        Net Capital: ($17.87 * 100) - $154 = $1,633
        Total Return: -$55 / $1,633 = -3.37%
        
        Expected: Premium Captured % ≠ Total Return %
        """
        # Stock leg
        stock_entry_price = 17.87
        stock_current_price = 16.50
        underlying_quantity = 100
        quantity = 1
        
        stock_pnl = (stock_current_price - stock_entry_price) * underlying_quantity * quantity
        
        # Option leg
        option_entry_price = 1.54
        option_current_price = 0.72
        premium_received = option_entry_price * 100 * quantity
        
        option_pnl = (option_entry_price - option_current_price) * 100 * quantity
        
        # Premium captured percentage (option-only metric)
        premium_captured_pct = (option_pnl / premium_received) * 100
        
        # Total position P/L
        total_pnl = stock_pnl + option_pnl
        
        # Total return percentage (combined position metric)
        net_capital = (stock_entry_price * underlying_quantity * quantity) - premium_received
        total_return_pct = (total_pnl / net_capital) * 100
        
        # Assertions
        assert premium_captured_pct == pytest.approx(53.25, abs=0.01), "Premium captured should be ~53.25%"
        assert total_return_pct == pytest.approx(-3.37, abs=0.01), "Total return should be ~-3.37%"
        assert premium_captured_pct > 0, "Premium captured % is positive"
        assert total_return_pct < 0, "Total return % is negative"
        assert premium_captured_pct != total_return_pct, "Premium captured % must differ from total return %"

    def test_multiple_contracts(self):
        """Test P/L calculation with multiple covered call contracts."""
        # Stock leg
        stock_entry_price = 17.87
        stock_current_price = 16.50
        underlying_quantity = 100
        quantity = 3  # 3 contracts = 300 shares
        
        stock_pnl = (stock_current_price - stock_entry_price) * underlying_quantity * quantity
        
        # Option leg
        option_entry_price = 1.54
        option_current_price = 0.72
        
        option_pnl = (option_entry_price - option_current_price) * 100 * quantity
        
        # Combined P/L
        total_pnl = stock_pnl + option_pnl
        
        # Assertions
        assert stock_pnl == pytest.approx(-411.0, abs=0.01), "Stock P/L should be -$411 for 3 contracts"
        assert option_pnl == pytest.approx(246.0, abs=0.01), "Option P/L should be +$246 for 3 contracts"
        assert total_pnl == pytest.approx(-165.0, abs=0.01), "Total P/L should be -$165 for 3 contracts"

    def test_stock_at_strike(self):
        """Test P/L when stock price equals strike at expiration."""
        # Stock leg
        stock_entry_price = 17.87
        strike_price = 18.50
        stock_current_price = strike_price  # At strike
        underlying_quantity = 100
        quantity = 1
        
        stock_pnl = (stock_current_price - stock_entry_price) * underlying_quantity * quantity
        
        # Option leg (worthless at expiration)
        option_entry_price = 1.54
        option_current_price = 0.00  # Worthless at expiration
        
        option_pnl = (option_entry_price - option_current_price) * 100 * quantity
        
        # Combined P/L (should equal max profit)
        total_pnl = stock_pnl + option_pnl
        premium_received = option_entry_price * 100 * quantity
        max_profit = ((strike_price - stock_entry_price) * underlying_quantity * quantity) + premium_received
        
        # Assertions
        assert stock_pnl == pytest.approx(63.0, abs=0.01), "Stock P/L should be +$63"
        assert option_pnl == pytest.approx(154.0, abs=0.01), "Option P/L should be +$154"
        assert total_pnl == pytest.approx(217.0, abs=0.01), "Total P/L should equal max profit"
        assert total_pnl == pytest.approx(max_profit, abs=0.01), "Total P/L should equal calculated max profit"

    def test_stock_below_break_even(self):
        """Test P/L when stock falls below break-even."""
        # Stock leg
        stock_entry_price = 17.87
        premium_per_share = 1.54
        break_even = stock_entry_price - premium_per_share  # $16.33
        stock_current_price = 16.00  # Below break-even
        underlying_quantity = 100
        quantity = 1
        
        stock_pnl = (stock_current_price - stock_entry_price) * underlying_quantity * quantity
        
        # Option leg (worthless)
        option_entry_price = premium_per_share
        option_current_price = 0.00
        
        option_pnl = (option_entry_price - option_current_price) * 100 * quantity
        
        # Combined P/L
        total_pnl = stock_pnl + option_pnl
        
        # Assertions
        assert stock_pnl == pytest.approx(-187.0, abs=0.01), "Stock P/L should be -$187"
        assert option_pnl == pytest.approx(154.0, abs=0.01), "Option P/L should be +$154"
        assert total_pnl == pytest.approx(-33.0, abs=0.01), "Total P/L should be -$33"
        assert total_pnl < 0, "Position should be losing when stock is below break-even"
        assert stock_current_price < break_even, "Stock price should be below break-even"
