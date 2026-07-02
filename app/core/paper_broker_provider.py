"""Paper trading broker provider for simulating trades without real money.

Provides realistic paper trading simulation with comprehensive logging of all requests and responses.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

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

logger = logging.getLogger(__name__)

# Preview expiration time in seconds
PREVIEW_EXPIRATION_SECONDS = 300  # 5 minutes


class PaperBrokerProvider(BrokerProvider):
    """Paper trading broker provider.
    
    Simulates broker behavior for paper trading without real money.
    Logs every request and response for audit trail and debugging.
    Requires order preview and confirmation before execution.
    """

    def __init__(
        self,
        initial_cash: float = 100000.0,
        account_id: Optional[str] = None,
        enable_logging: bool = True,
    ):
        """Initialize paper broker provider.
        
        Args:
            initial_cash: Starting cash balance
            account_id: Optional custom account ID. If None, generates UUID.
            enable_logging: Whether to log all requests and responses
        """
        self.account_id = account_id or str(uuid.uuid4())
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.enable_logging = enable_logging
        
        # In-memory storage for paper trading
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.price_cache: Dict[str, float] = {}  # Mock current prices
        self.previews: Dict[str, OrderPreviewResult] = {}  # Store pending previews
        
        logger.info(
            f"PaperBrokerProvider initialized: account_id={self.account_id}, "
            f"initial_cash=${initial_cash:.2f}"
        )

    def _log_request(self, method: str, params: Dict) -> None:
        """Log a broker request.
        
        Args:
            method: Method name
            params: Request parameters
        """
        if self.enable_logging:
            logger.info(
                f"[BROKER REQUEST] {method}",
                extra={"params": json.dumps(params, default=str)},
            )

    def _log_response(self, method: str, result: Dict) -> None:
        """Log a broker response.
        
        Args:
            method: Method name
            result: Response data
        """
        if self.enable_logging:
            logger.info(
                f"[BROKER RESPONSE] {method}",
                extra={"result": json.dumps(result, default=str)},
            )

    def _log_error(self, method: str, error: str) -> None:
        """Log a broker error.
        
        Args:
            method: Method name
            error: Error message
        """
        if self.enable_logging:
            logger.error(
                f"[BROKER ERROR] {method}: {error}",
                extra={"account_id": self.account_id},
            )

    def _get_current_price(self, symbol: str) -> float:
        """Get current price for symbol (mock).
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Mock current price
        """
        if symbol not in self.price_cache:
            # Generate mock price based on symbol
            import random
            self.price_cache[symbol] = round(random.uniform(50, 500), 2)
        return self.price_cache[symbol]

    def preview_order(
        self,
        symbol: str,
        quantity: int,
        side: OrderSide,
        strategy_type: str,
        contracts: Optional[List[Dict]] = None,
        max_loss: float = 0.0,
        max_profit: Optional[float] = None,
        breakeven: Optional[float] = None,
        reason: str = "",
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> OrderPreviewResult:
        """Preview an order before execution.
        
        Args:
            symbol: Stock ticker symbol
            quantity: Number of shares/contracts
            side: OrderSide.BUY or OrderSide.SELL
            strategy_type: Name of the strategy
            contracts: Optional list of option contracts
            max_loss: Maximum loss estimate
            max_profit: Maximum profit estimate
            breakeven: Breakeven price
            reason: Explanation for the trade
            order_type: Type of order
            price: Limit price if applicable
            stop_price: Stop price if applicable
            
        Returns:
            OrderPreviewResult with preview details
        """
        # Validate parameters
        if quantity <= 0:
            error_msg = f"Invalid quantity: {quantity}"
            self._log_error("preview_order", error_msg)
            raise ValueError(error_msg)
        
        if not symbol or not isinstance(symbol, str):
            error_msg = f"Invalid symbol: {symbol}"
            self._log_error("preview_order", error_msg)
            raise ValueError(error_msg)
        
        # Log request
        self._log_request(
            "preview_order",
            {
                "symbol": symbol,
                "quantity": quantity,
                "side": side.value,
                "strategy_type": strategy_type,
                "max_loss": max_loss,
                "max_profit": max_profit,
                "reason": reason,
            },
        )
        
        # Generate preview ID
        preview_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Create preview
        preview = OrderPreview(
            preview_id=preview_id,
            symbol=symbol,
            strategy_type=strategy_type,
            contracts=contracts or [],
            quantity=quantity,
            side=side,
            order_type=order_type,
            price=price,
            max_loss=max_loss,
            max_profit=max_profit,
            breakeven=breakeven,
            reason=reason,
            created_at=now,
            expires_at=now + timedelta(seconds=PREVIEW_EXPIRATION_SECONDS),
        )
        
        # Create result
        result = OrderPreviewResult(
            preview_id=preview_id,
            status="pending",
            preview=preview,
            message=f"Order preview created. Review details and confirm to execute.",
            created_at=now,
        )
        
        # Store preview
        self.previews[preview_id] = result
        
        # Log response
        self._log_response(
            "preview_order",
            {
                "preview_id": preview_id,
                "status": "pending",
                "expires_at": preview.expires_at.isoformat(),
            },
        )
        
        return result

    def confirm_preview(self, preview_id: str) -> Order:
        """Confirm a preview and execute the order.
        
        Args:
            preview_id: ID of the preview to confirm
            
        Returns:
            Order object
            
        Raises:
            ValueError: If preview_id is invalid or expired
        """
        # Log request
        self._log_request("confirm_preview", {"preview_id": preview_id})
        
        # Find preview
        if preview_id not in self.previews:
            error_msg = f"Preview not found: {preview_id}"
            self._log_error("confirm_preview", error_msg)
            raise ValueError(error_msg)
        
        preview_result = self.previews[preview_id]
        preview = preview_result.preview
        
        # Check if preview is expired
        if datetime.utcnow() > preview.expires_at:
            error_msg = f"Preview expired: {preview_id}"
            self._log_error("confirm_preview", error_msg)
            preview_result.status = "expired"
            raise ValueError(error_msg)
        
        # Check if already confirmed
        if preview_result.status != "pending":
            error_msg = f"Preview already {preview_result.status}: {preview_id}"
            self._log_error("confirm_preview", error_msg)
            raise ValueError(error_msg)
        
        # Mark as confirmed
        preview_result.status = "confirmed"
        preview_result.confirmed_at = datetime.utcnow()
        
        # Execute the order
        order = self.place_order(
            symbol=preview.symbol,
            quantity=preview.quantity,
            side=preview.side,
            order_type=preview.order_type,
            price=preview.price,
            stop_price=None,  # stop_price not stored in preview
        )
        
        # Log response
        self._log_response(
            "confirm_preview",
            {
                "preview_id": preview_id,
                "order_id": order.order_id,
                "status": order.status.value,
            },
        )
        
        return order

    def cancel_preview(self, preview_id: str) -> OrderPreviewResult:
        """Cancel a preview without executing the order.
        
        Args:
            preview_id: ID of the preview to cancel
            
        Returns:
            OrderPreviewResult with cancelled status
            
        Raises:
            ValueError: If preview_id is invalid
        """
        # Log request
        self._log_request("cancel_preview", {"preview_id": preview_id})
        
        # Find preview
        if preview_id not in self.previews:
            error_msg = f"Preview not found: {preview_id}"
            self._log_error("cancel_preview", error_msg)
            raise ValueError(error_msg)
        
        preview_result = self.previews[preview_id]
        
        # Cancel preview
        preview_result.status = "cancelled"
        preview_result.message = "Preview cancelled by user."
        
        # Log response
        self._log_response(
            "cancel_preview",
            {"preview_id": preview_id, "status": "cancelled"},
        )
        
        return preview_result

    def place_order(
        self,
        symbol: str,
        quantity: int,
        side: OrderSide,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> Order:
        """Place an order in paper trading.
        
        Args:
            symbol: Stock ticker symbol
            quantity: Number of shares
            side: BUY or SELL
            order_type: Type of order
            price: Limit price if applicable
            stop_price: Stop price if applicable
            
        Returns:
            Order object
            
        Raises:
            ValueError: If parameters are invalid
        """
        # Validate parameters
        if quantity <= 0:
            error_msg = f"Invalid quantity: {quantity}"
            self._log_error("place_order", error_msg)
            raise ValueError(error_msg)
        
        if not symbol or not isinstance(symbol, str):
            error_msg = f"Invalid symbol: {symbol}"
            self._log_error("place_order", error_msg)
            raise ValueError(error_msg)
        
        # Log request
        self._log_request(
            "place_order",
            {
                "symbol": symbol,
                "quantity": quantity,
                "side": side.value,
                "order_type": order_type.value,
                "price": price,
                "stop_price": stop_price,
            },
        )
        
        # Generate order ID
        order_id = str(uuid.uuid4())
        
        # Get current price
        current_price = self._get_current_price(symbol)
        
        # Determine fill price based on order type
        if order_type == OrderType.MARKET:
            fill_price = current_price
            status = OrderStatus.FILLED
            filled_quantity = quantity
        elif order_type == OrderType.LIMIT:
            if price is None:
                error_msg = "Limit order requires price"
                self._log_error("place_order", error_msg)
                raise ValueError(error_msg)
            # In paper trading, assume limit orders fill immediately if price is reasonable
            if (side == OrderSide.BUY and price >= current_price * 0.95) or \
               (side == OrderSide.SELL and price <= current_price * 1.05):
                fill_price = price
                status = OrderStatus.FILLED
                filled_quantity = quantity
            else:
                fill_price = None
                status = OrderStatus.PENDING
                filled_quantity = 0
        else:
            # Stop and stop-limit orders start as pending
            fill_price = None
            status = OrderStatus.PENDING
            filled_quantity = 0
        
        # Create order
        order = Order(
            order_id=order_id,
            symbol=symbol,
            quantity=quantity,
            side=side,
            order_type=order_type,
            status=status,
            price=price,
            stop_price=stop_price,
            filled_quantity=filled_quantity,
            filled_price=fill_price,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        # Store order
        self.orders[order_id] = order
        
        # Update positions and cash if order filled
        if status == OrderStatus.FILLED:
            self._update_position(symbol, quantity, side, fill_price)
            self._update_cash(quantity, side, fill_price)
        
        # Log response
        self._log_response(
            "place_order",
            {
                "order_id": order_id,
                "status": status.value,
                "filled_quantity": filled_quantity,
                "filled_price": fill_price,
            },
        )
        
        return order

    def cancel_order(self, order_id: str) -> Order:
        """Cancel an order.
        
        Args:
            order_id: ID of order to cancel
            
        Returns:
            Updated Order object
            
        Raises:
            ValueError: If order not found or cannot be cancelled
        """
        # Log request
        self._log_request("cancel_order", {"order_id": order_id})
        
        # Find order
        if order_id not in self.orders:
            error_msg = f"Order not found: {order_id}"
            self._log_error("cancel_order", error_msg)
            raise ValueError(error_msg)
        
        order = self.orders[order_id]
        
        # Check if order can be cancelled
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            error_msg = f"Cannot cancel order with status: {order.status.value}"
            self._log_error("cancel_order", error_msg)
            raise ValueError(error_msg)
        
        # Cancel order
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        
        # Log response
        self._log_response(
            "cancel_order",
            {"order_id": order_id, "status": order.status.value},
        )
        
        return order

    def get_positions(self) -> List[Position]:
        """Get all open positions.
        
        Returns:
            List of Position objects
        """
        # Log request
        self._log_request("get_positions", {})
        
        # Update current prices and P&L
        positions = []
        for symbol, position in self.positions.items():
            current_price = self._get_current_price(symbol)
            position.current_price = current_price
            position.market_value = position.quantity * current_price
            position.unrealized_pl = (
                position.market_value - (position.quantity * position.entry_price)
                if position.side == PositionSide.LONG
                else (position.quantity * position.entry_price) - position.market_value
            )
            position.unrealized_pl_pct = (
                (position.unrealized_pl / (position.quantity * position.entry_price)) * 100
                if position.entry_price > 0
                else 0
            )
            position.updated_at = datetime.utcnow()
            positions.append(position)
        
        # Log response
        self._log_response(
            "get_positions",
            {"count": len(positions), "symbols": [p.symbol for p in positions]},
        )
        
        return positions

    def get_account(self) -> Account:
        """Get account information.
        
        Returns:
            Account object
        """
        # Log request
        self._log_request("get_account", {})
        
        # Calculate portfolio value
        positions_value = sum(
            p.quantity * self._get_current_price(p.symbol)
            for p in self.positions.values()
        )
        portfolio_value = self.cash + positions_value
        
        account = Account(
            account_id=self.account_id,
            account_type="paper",
            cash=self.cash,
            portfolio_value=portfolio_value,
            buying_power=self.cash * 4,  # 4x buying power for margin
            multiplier=4.0,
            equity=portfolio_value,
            last_equity=portfolio_value,
            status="active",
            updated_at=datetime.utcnow(),
        )
        
        # Log response
        self._log_response(
            "get_account",
            {
                "account_id": self.account_id,
                "cash": self.cash,
                "portfolio_value": portfolio_value,
                "buying_power": account.buying_power,
            },
        )
        
        return account

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID.
        
        Args:
            order_id: ID of order to retrieve
            
        Returns:
            Order object or None if not found
        """
        # Log request
        self._log_request("get_order", {"order_id": order_id})
        
        order = self.orders.get(order_id)
        
        # Log response
        if order:
            self._log_response(
                "get_order",
                {"order_id": order_id, "status": order.status.value},
            )
        else:
            self._log_error("get_order", f"Order not found: {order_id}")
        
        return order

    def get_orders(
        self,
        status: Optional[OrderStatus] = None,
        symbol: Optional[str] = None,
    ) -> List[Order]:
        """Get orders with optional filtering.
        
        Args:
            status: Optional filter by order status
            symbol: Optional filter by symbol
            
        Returns:
            List of Order objects
        """
        # Log request
        self._log_request(
            "get_orders",
            {"status": status.value if status else None, "symbol": symbol},
        )
        
        orders = list(self.orders.values())
        
        # Filter by status
        if status is not None:
            orders = [o for o in orders if o.status == status]
        
        # Filter by symbol
        if symbol is not None:
            orders = [o for o in orders if o.symbol == symbol]
        
        # Log response
        self._log_response(
            "get_orders",
            {"count": len(orders), "symbols": list(set(o.symbol for o in orders))},
        )
        
        return orders

    def _update_position(
        self,
        symbol: str,
        quantity: int,
        side: OrderSide,
        price: float,
    ) -> None:
        """Update position after order fill.
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: BUY or SELL
            price: Fill price
        """
        if symbol not in self.positions:
            # Create new position
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity if side == OrderSide.BUY else -quantity,
                side=PositionSide.LONG if side == OrderSide.BUY else PositionSide.SHORT,
                entry_price=price,
                current_price=price,
                market_value=quantity * price,
                unrealized_pl=0.0,
                unrealized_pl_pct=0.0,
                updated_at=datetime.utcnow(),
            )
        else:
            # Update existing position
            position = self.positions[symbol]
            if side == OrderSide.BUY:
                position.quantity += quantity
            else:
                position.quantity -= quantity
            position.updated_at = datetime.utcnow()

    def _update_cash(
        self,
        quantity: int,
        side: OrderSide,
        price: float,
    ) -> None:
        """Update cash balance after order fill.
        
        Args:
            quantity: Number of shares
            side: BUY or SELL
            price: Fill price
        """
        cost = quantity * price
        if side == OrderSide.BUY:
            self.cash -= cost
        else:
            self.cash += cost
