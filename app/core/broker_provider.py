"""Abstract base interface for broker providers.

Defines the contract that all broker providers (paper trading, Alpaca, Tradier, etc.) must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class PositionSide(str, Enum):
    """Position side enumeration."""
    LONG = "long"
    SHORT = "short"


@dataclass
class Order:
    """Represents a single order."""
    order_id: str
    symbol: str
    quantity: int
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    price: Optional[float] = None
    stop_price: Optional[float] = None
    filled_quantity: int = 0
    filled_price: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class Position:
    """Represents a single position."""
    symbol: str
    quantity: int
    side: PositionSide
    entry_price: float
    current_price: float
    market_value: float
    unrealized_pl: float
    unrealized_pl_pct: float
    updated_at: Optional[datetime] = None


@dataclass
class Account:
    """Represents account information."""
    account_id: str
    account_type: str  # "paper" or "live"
    cash: float
    portfolio_value: float
    buying_power: float
    multiplier: float
    equity: float
    last_equity: float
    status: str  # "active", "inactive", etc.
    updated_at: Optional[datetime] = None


@dataclass
class OrderPreview:
    """Preview of an order before execution.
    
    Shows the user all details of the order they are about to place,
    including strategy, contracts, quantity, risk metrics, and reason.
    """
    preview_id: str
    symbol: str
    strategy_type: str
    contracts: List[Dict] = field(default_factory=list)  # List of option contracts or underlying details
    quantity: int = 0
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None
    max_loss: float = 0.0
    max_profit: Optional[float] = None
    breakeven: Optional[float] = None
    reason: str = ""  # Explanation for the trade
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


@dataclass
class OrderPreviewResult:
    """Result of order preview operation."""
    preview_id: str
    status: str  # "pending", "confirmed", "cancelled", "expired"
    preview: OrderPreview
    message: str = ""
    created_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None


class BrokerProvider(ABC):
    """Abstract base class for broker providers.
    
    All broker providers must implement these methods to enable order placement,
    cancellation, position tracking, and account management.
    """

    @abstractmethod
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
            strategy_type: Name of the strategy (e.g., "covered_call")
            contracts: Optional list of option contracts involved
            max_loss: Maximum loss estimate in dollars
            max_profit: Maximum profit estimate in dollars (if defined)
            breakeven: Breakeven price (if applicable)
            reason: Explanation for the trade
            order_type: Type of order
            price: Limit price if applicable
            stop_price: Stop price if applicable
            
        Returns:
            OrderPreviewResult with preview_id and status
        """
        pass

    @abstractmethod
    def confirm_preview(self, preview_id: str) -> Order:
        """Confirm a preview and execute the order.
        
        Args:
            preview_id: ID of the preview to confirm
            
        Returns:
            Order object with order_id and status
            
        Raises:
            ValueError: If preview_id is invalid or expired
        """
        pass

    @abstractmethod
    def cancel_preview(self, preview_id: str) -> OrderPreviewResult:
        """Cancel a preview without executing the order.
        
        Args:
            preview_id: ID of the preview to cancel
            
        Returns:
            OrderPreviewResult with cancelled status
            
        Raises:
            ValueError: If preview_id is invalid
        """
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        quantity: int,
        side: OrderSide,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> Order:
        """Place an order.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            quantity: Number of shares to trade
            side: OrderSide.BUY or OrderSide.SELL
            order_type: Type of order (market, limit, stop, stop_limit)
            price: Limit price for limit orders
            stop_price: Stop price for stop orders
            
        Returns:
            Order object with order_id and status
            
        Raises:
            ValueError: If order parameters are invalid
            RuntimeError: If order placement fails
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> Order:
        """Cancel an existing order.
        
        Args:
            order_id: ID of the order to cancel
            
        Returns:
            Updated Order object with cancelled status
            
        Raises:
            ValueError: If order_id is invalid
            RuntimeError: If cancellation fails
        """
        pass

    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Get all open positions.
        
        Returns:
            List of Position objects for all open positions
        """
        pass

    @abstractmethod
    def get_account(self) -> Account:
        """Get account information.
        
        Returns:
            Account object with current account state
        """
        pass

    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order details by ID.
        
        Args:
            order_id: ID of the order to retrieve
            
        Returns:
            Order object or None if not found
        """
        pass

    @abstractmethod
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
            List of Order objects matching filters
        """
        pass
