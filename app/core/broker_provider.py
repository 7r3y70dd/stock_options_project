"""Abstract base interface for broker providers.

Defines the contract that all broker providers (paper trading, Alpaca, Tradier, etc.) must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
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


class BrokerProvider(ABC):
    """Abstract base class for broker providers.
    
    All broker providers must implement these methods to enable order placement,
    cancellation, position tracking, and account management.
    """

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
