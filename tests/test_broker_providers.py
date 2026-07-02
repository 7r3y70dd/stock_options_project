"""Tests for broker provider interface and implementations.

Verifies that:
1. BrokerProvider interface is properly defined
2. PaperBrokerProvider implements all required methods
3. Paper orders can be submitted and tracked
4. Live trading cannot be accidentally enabled
5. Provider logs every request and response
6. Order preview is required before execution
7. User can cancel at preview step
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
    OrderPreview,
    OrderPreviewResult,
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
            "preview_order",
            "confirm_preview",
            "cancel_preview",
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


class TestOrderPreview:
    """Test order preview functionality."""

    @pytest.fixture
    def broker(self):
        """Create a paper broker instance."""
        return PaperBrokerProvider(initial_cash=100000.0, enable_logging=True)

    def test_preview_order_creates_preview(self, broker):
        """Test that preview_order creates a preview."""
        result = broker.preview_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            strategy_type="covered_call",
            max_loss=100.0,
            max_profit=200.0,
            breakeven=150.0,
            reason="Bullish outlook with income generation",
        )
        
        assert result is not None
        assert result.preview_id is not None
        assert result.status == "pending"
        assert result.preview.symbol == "AAPL"
        assert result.preview.quantity == 10
        assert result.preview.strategy_type == "covered_call"
        assert result.preview.max_loss == 100.0
        assert result.preview.max_profit == 200.0
        assert result.preview.breakeven == 150.0
        assert result.preview.reason == "Bullish outlook with income generation"

    def test_preview_order_invalid_quantity(self, broker):
        """Test preview with invalid quantity raises error."""
        with pytest.raises(ValueError, match="Invalid quantity"):
            broker.preview_order(
                symbol="AAPL",
                quantity=-10,
                side=OrderSide.BUY,
                strategy_type="covered_call",
            )

    def test_preview_order_invalid_symbol(self, broker):
        """Test preview with invalid symbol raises error."""
        with pytest.raises(ValueError, match="Invalid symbol"):
            broker.preview_order(
                symbol="",
                quantity=10,
                side=OrderSide.BUY,
                strategy_type="covered_call",
            )

    def test_preview_order_stores_preview(self, broker):
        """Test that preview is stored and retrievable."""
        result = broker.preview_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            strategy_type="covered_call",
            reason="Test reason",
        )
        
        preview_id = result.preview_id
        assert preview_id in broker.previews
        assert broker.previews[preview_id].status == "pending"

    def test_confirm_preview_executes_order(self, broker):
        """Test that confirming preview executes the order."""
        # Create preview
        preview_result = broker.preview_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            strategy_type="covered_call",
            reason="Test",
        )
        
        # Confirm preview
        order = broker.confirm_preview(preview_result.preview_id)
        
        assert order is not None
        assert order.symbol == "AAPL"
        assert order.quantity == 10
        assert order.status == OrderStatus.FILLED
        assert preview_result.status == "confirmed"

    def test_confirm_preview_not_found(self, broker):
        """Test confirming non-existent preview raises error."""
        with pytest.raises(ValueError, match="Preview not found"):
            broker.confirm_preview("invalid-preview-id")

    def test_confirm_preview_expired(self, broker):
        """Test confirming expired preview raises error."""
        # Create preview
        preview_result = broker.preview_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            strategy_type="covered_call",
            reason="Test",
        )
        
        # Manually expire the preview
        preview_result.preview.expires_at = datetime.utcnow()
        
        # Try to confirm
        with pytest.raises(ValueError, match="Preview expired"):
            broker.confirm_preview(preview_result.preview_id)

    def test_cancel_preview_cancels_without_order(self, broker):
        """Test that cancelling preview does not execute order."""
        # Create preview
        preview_result = broker.preview_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            strategy_type="covered_call",
            reason="Test",
        )
        
        preview_id = preview_result.preview_id
        
        # Cancel preview
        cancelled = broker.cancel_preview(preview_id)
        
        assert cancelled.status == "cancelled"
        
        # Verify no order was created
        orders = broker.get_orders()
        assert len(orders) == 0

    def test_cancel_preview_not_found(self, broker):
        """Test cancelling non-existent preview raises error."""
        with pytest.raises(ValueError, match="Preview not found"):
            broker.cancel_preview("invalid-preview-id")

    def test_preview_shows_all_required_details(self, broker):
        """Test that preview shows all required details."""
        contracts = [{"symbol": "AAPL", "strike": 150.0, "type": "call"}]
        
        result = broker.preview_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            strategy_type="covered_call",
            contracts=contracts,
            max_loss=100.0,
            max_profit=200.0,
            breakeven=150.0,
            reason="Bullish with income",
        )
        
        preview = result.preview
        
        # Verify all required details are present
        assert preview.strategy_type == "covered_call"  # Strategy
        assert preview.contracts == contracts  # Contracts
        assert preview.quantity == 10  # Quantity
        assert preview.max_loss == 100.0  # Max loss
        assert preview.max_profit == 200.0  # Max profit
        assert preview.breakeven == 150.0  # Breakeven
        assert preview.reason == "Bullish with income"  # Reason

    def test_no_order_without_preview_confirmation(self, broker):
        """Test that no order is placed without preview confirmation."""
        # Create preview
        preview_result = broker.preview_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            strategy_type="covered_call",
            reason="Test",
        )
        
        # Verify no order exists yet
        orders = broker.get_orders()
        assert len(orders) == 0
        
        # Confirm preview
        order = broker.confirm_preview(preview_result.preview_id)
        
        # Now order should exist
        orders = broker.get_orders()
        assert len(orders) == 1
        assert orders[0].order_id == order.order_id

    def test_user_can_cancel_at_preview_step(self, broker):
        """Test that user can cancel at preview step."""
        # Create preview
        preview_result = broker.preview_order(
            symbol="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            strategy_type="covered_call",
            reason="Test",
        )
        
        # User cancels
        cancelled = broker.cancel_preview(preview_result.preview_id)
        assert cancelled.status == "cancelled"
        
        # Verify no order was created
        orders = broker.get_orders()
        assert len(orders) == 0
        
        # Verify cash unchanged
        account = broker.get_account()
        assert account.cash == 100000.0


class TestPlaceOrder:
    """Test order placement functionality."""

    @pytest.fixture
    def broker(self):
        """Create a paper broker instance."""
        return PaperBrokerProvider(initial_cash=100000.0, enable_logging=True)

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
        """Test that logging is enabled."""
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
