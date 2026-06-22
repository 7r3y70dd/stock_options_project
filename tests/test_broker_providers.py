"""Tests for broker provider interface and implementations.

Verifies that:
1. BrokerProvider interface is properly defined
2. PaperBrokerProvider implements all required methods
3. Paper orders can be submitted and tracked
4. Live trading cannot be accidentally enabled
5. Provider logs every request and response
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import logging

from app.core.broker_provider import (
    BrokerProvider,
    Order,
    OrderStatus,
    OrderType,
    OrderSide,
    Position,
    PositionSide,
    Account,
)
from app.core.paper_broker_provider import PaperBrokerProvider
from app.core.config import config


class TestBrokerProviderInterface:
    """Test that BrokerProvider interface is properly defined."""

    def test_broker_provider_is_abstract(self):
        """Test that BrokerProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BrokerProvider()

    def test_broker_provider_has_required_methods(self):
        """Test that BrokerProvider defines all required methods."""
        required_methods = [
            "place_order",
            "cancel_order",
            "get_positions",
            "get_account",
            "get_order",
            "get_orders",
        ]
        for method in required_methods:
            assert hasattr(BrokerProvider, method), f"BrokerProvider missing method: {method}"


class TestPaperBrokerProvider:
    """Test PaperBrokerProvider implementation."""

    @pytest.fixture
    def broker(self):
        """Create a paper broker instance."""
        return PaperBrokerProvider(initial_cash=100000.0, enable_logging=True)

    def test_paper_broker_is_broker_provider(self, broker):
        """Test that PaperBrokerProvider is a BrokerProvider."""
        assert isinstance(broker, BrokerProvider)

    def test_paper_broker_initialization(self, broker):
        """Test paper broker initializes with correct values."""
        assert broker.cash == 100000.0
        assert broker.initial_cash == 100000.0
        assert broker.account_id is not None
        assert len(broker.account_id) > 0

    def test_place_market_order_buy(self, broker):
        """Test placing a market buy order."""
        order = broker.place_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )
        
        assert order is not None
        assert order.symbol == "AAPL"
        assert order.quantity == 10
        assert order.side == OrderSide.BUY
        assert order.status == OrderStatus.FILLED
        assert order.filled_quantity == 10
        assert order.filled_price is not None
        assert order.order_id is not None

    def test_place_market_order_sell(self, broker):
        """Test placing a market sell order."""
        # First buy some shares
        broker.place_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )
        
        # Then sell them
        order = broker.place_order(
            symbol="AAPL",
            quantity=5,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
        )
        
        assert order.status == OrderStatus.FILLED
        assert order.side == OrderSide.SELL
        assert order.filled_quantity == 5

    def test_place_order_invalid_quantity(self, broker):
        """Test placing order with invalid quantity raises error."""
        with pytest.raises(ValueError, match="Invalid quantity"):
            broker.place_order(
                symbol="AAPL",
                quantity=-10,
                side=OrderSide.BUY,
            )
        
        with pytest.raises(ValueError, match="Invalid quantity"):
            broker.place_order(
                symbol="AAPL",
                quantity=0,
                side=OrderSide.BUY,
            )

    def test_place_order_invalid_symbol(self, broker):
        """Test placing order with invalid symbol raises error."""
        with pytest.raises(ValueError, match="Invalid symbol"):
            broker.place_order(
                symbol="",
                quantity=10,
                side=OrderSide.BUY,
            )
        
        with pytest.raises(ValueError, match="Invalid symbol"):
            broker.place_order(
                symbol=None,
                quantity=10,
                side=OrderSide.BUY,
            )

    def test_place_limit_order(self, broker):
        """Test placing a limit order."""
        order = broker.place_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=150.0,
        )
        
        assert order is not None
        assert order.order_type == OrderType.LIMIT
        assert order.price == 150.0

    def test_place_limit_order_requires_price(self, broker):
        """Test placing limit order without price raises error."""
        with pytest.raises(ValueError, match="Limit order requires price"):
            broker.place_order(
                symbol="AAPL",
                quantity=10,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
            )

    def test_cancel_order(self, broker):
        """Test cancelling an order."""
        # Place a pending order
        order = broker.place_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=50.0,  # Very low price to keep order pending
        )
        
        # Cancel it
        cancelled = broker.cancel_order(order.order_id)
        
        assert cancelled.status == OrderStatus.CANCELLED
        assert cancelled.order_id == order.order_id

    def test_cancel_order_not_found(self, broker):
        """Test cancelling non-existent order raises error."""
        with pytest.raises(ValueError, match="Order not found"):
            broker.cancel_order("invalid-order-id")

    def test_cancel_filled_order_fails(self, broker):
        """Test cancelling a filled order raises error."""
        # Place and fill an order
        order = broker.place_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )
        
        # Try to cancel it
        with pytest.raises(ValueError, match="Cannot cancel order"):
            broker.cancel_order(order.order_id)

    def test_get_positions_empty(self, broker):
        """Test getting positions when none exist."""
        positions = broker.get_positions()
        assert positions == []

    def test_get_positions_after_buy(self, broker):
        """Test getting positions after buying shares."""
        broker.place_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )
        
        positions = broker.get_positions()
        
        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].quantity == 10
        assert positions[0].side == PositionSide.LONG
        assert positions[0].entry_price > 0
        assert positions[0].market_value > 0

    def test_get_positions_multiple_symbols(self, broker):
        """Test getting positions for multiple symbols."""
        broker.place_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )
        broker.place_order(
            symbol="MSFT",
            quantity=5,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )
        
        positions = broker.get_positions()
        
        assert len(positions) == 2
        symbols = {p.symbol for p in positions}
        assert symbols == {"AAPL", "MSFT"}

    def test_get_account(self, broker):
        """Test getting account information."""
        account = broker.get_account()
        
        assert account is not None
        assert account.account_id == broker.account_id
        assert account.account_type == "paper"
        assert account.cash == 100000.0
        assert account.portfolio_value == 100000.0
        assert account.status == "active"

    def test_get_account_after_trade(self, broker):
        """Test account values update after trades."""
        initial_account = broker.get_account()
        initial_cash = initial_account.cash
        
        # Place a buy order
        broker.place_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )
        
        # Check account
        updated_account = broker.get_account()
        
        assert updated_account.cash < initial_cash
        assert updated_account.portfolio_value == initial_account.portfolio_value

    def test_get_order(self, broker):
        """Test getting order by ID."""
        order = broker.place_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )
        
        retrieved = broker.get_order(order.order_id)
        
        assert retrieved is not None
        assert retrieved.order_id == order.order_id
        assert retrieved.symbol == order.symbol

    def test_get_order_not_found(self, broker):
        """Test getting non-existent order returns None."""
        order = broker.get_order("invalid-order-id")
        assert order is None

    def test_get_orders_empty(self, broker):
        """Test getting orders when none exist."""
        orders = broker.get_orders()
        assert orders == []

    def test_get_orders_all(self, broker):
        """Test getting all orders."""
        broker.place_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )
        broker.place_order(
            symbol="MSFT",
            quantity=5,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )
        
        orders = broker.get_orders()
        assert len(orders) == 2

    def test_get_orders_filter_by_status(self, broker):
        """Test filtering orders by status."""
        # Place a filled order
        broker.place_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )
        
        # Place a pending order
        broker.place_order(
            symbol="MSFT",
            quantity=5,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=50.0,
        )
        
        filled_orders = broker.get_orders(status=OrderStatus.FILLED)
        assert len(filled_orders) == 1
        assert filled_orders[0].symbol == "AAPL"
        
        pending_orders = broker.get_orders(status=OrderStatus.PENDING)
        assert len(pending_orders) == 1
        assert pending_orders[0].symbol == "MSFT"

    def test_get_orders_filter_by_symbol(self, broker):
        """Test filtering orders by symbol."""
        broker.place_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )
        broker.place_order(
            symbol="AAPL",
            quantity=5,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )
        broker.place_order(
            symbol="MSFT",
            quantity=3,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )
        
        aapl_orders = broker.get_orders(symbol="AAPL")
        assert len(aapl_orders) == 2
        
        msft_orders = broker.get_orders(symbol="MSFT")
        assert len(msft_orders) == 1

    def test_logging_enabled(self, caplog):
        """Test that broker logs requests and responses."""
        broker = PaperBrokerProvider(initial_cash=100000.0, enable_logging=True)
        
        with caplog.at_level(logging.INFO):
            broker.place_order(
                symbol="AAPL",
                quantity=10,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
            )
        
        # Check that request and response were logged
        log_messages = [record.message for record in caplog.records]
        assert any("BROKER REQUEST" in msg for msg in log_messages)
        assert any("BROKER RESPONSE" in msg for msg in log_messages)

    def test_logging_disabled(self, caplog):
        """Test that logging can be disabled."""
        broker = PaperBrokerProvider(initial_cash=100000.0, enable_logging=False)
        
        with caplog.at_level(logging.INFO):
            broker.place_order(
                symbol="AAPL",
                quantity=10,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
            )
        
        # Check that broker logs were not created
        log_messages = [record.message for record in caplog.records]
        assert not any("BROKER REQUEST" in msg for msg in log_messages)
        assert not any("BROKER RESPONSE" in msg for msg in log_messages)


class TestLiveTradingPrevention:
    """Test that live trading cannot be accidentally enabled."""

    def test_paper_trading_enabled_by_default(self):
        """Test that paper trading is enabled by default."""
        assert config.PAPER_TRADING_ENABLED is True

    def test_live_trading_disabled_by_default(self):
        """Test that live trading is disabled by default."""
        assert config.LIVE_TRADING_ENABLED is False

    def test_live_trading_requires_explicit_approval(self):
        """Test that live trading requires explicit approval."""
        # Live trading should only be enabled if both conditions are met:
        # 1. LIVE_TRADING_ENABLED is True
        # 2. PAPER_TRADING_ENABLED is False
        
        # Default state: paper trading enabled, live trading disabled
        assert config.is_paper_trading_enabled() is True
        assert config.is_live_trading_enabled() is False

    def test_paper_broker_is_default(self):
        """Test that paper broker is the default."""
        assert config.BROKER_PROVIDER == "paper"

    def test_paper_broker_cannot_execute_live_trades(self):
        """Test that paper broker simulates trades without real money."""
        broker = PaperBrokerProvider(initial_cash=100000.0)
        
        # All trades should be simulated
        order = broker.place_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
        )
        
        # Order should be filled in paper trading
        assert order.status == OrderStatus.FILLED
        
        # Account should show simulated values
        account = broker.get_account()
        assert account.account_type == "paper"
        assert account.cash < 100000.0  # Cash reduced by trade
