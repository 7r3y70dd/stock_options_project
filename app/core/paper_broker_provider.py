"""Paper trading broker provider for simulated trading.

Provides a paper trading implementation of the BrokerProvider interface
for testing strategies without real money.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.core.broker_provider import BrokerProvider, OrderStatus, Order
from app.models.database import Trade, User

logger = logging.getLogger(__name__)


class PaperBrokerProvider(BrokerProvider):
    """Paper trading broker provider.
    
    Simulates trading without real money. Maintains virtual portfolio
    and tracks trades in the database.
    """
    
    def __init__(
        self,
        initial_cash: float = 10000.0,
        enable_logging: bool = True,
    ):
        """Initialize paper broker provider.
        
        Args:
            initial_cash: Initial cash balance for paper trading
            enable_logging: Whether to enable detailed logging
        """
        self.initial_cash = initial_cash
        self.enable_logging = enable_logging
        logger.info(f"PaperBrokerProvider initialized with ${initial_cash:,.2f}")
    
    def place_order(
        self,
        symbol: str,
        quantity: int,
        order_type: str,
        price: Optional[float] = None,
        user_id: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Order:
        """Place a paper trading order.
        
        Args:
            symbol: Stock symbol
            quantity: Order quantity
            order_type: Order type (buy, sell, etc.)
            price: Optional limit price
            user_id: Optional user ID
            db: Optional database session
            
        Returns:
            Order object
        """
        if self.enable_logging:
            logger.info(f"Paper order: {order_type} {quantity} {symbol} @ ${price}")
        
        return Order(
            order_id="paper_" + str(datetime.utcnow().timestamp()),
            symbol=symbol,
            quantity=quantity,
            order_type=order_type,
            price=price,
            status=OrderStatus.FILLED,
            timestamp=datetime.utcnow(),
        )
    
    def get_order_status(
        self,
        order_id: str,
        user_id: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> OrderStatus:
        """Get paper order status.
        
        Args:
            order_id: Order ID
            user_id: Optional user ID
            db: Optional database session
            
        Returns:
            OrderStatus
        """
        # Paper orders are always filled immediately
        return OrderStatus.FILLED
    
    def cancel_order(
        self,
        order_id: str,
        user_id: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> bool:
        """Cancel a paper order.
        
        Args:
            order_id: Order ID
            user_id: Optional user ID
            db: Optional database session
            
        Returns:
            True if cancelled, False otherwise
        """
        if self.enable_logging:
            logger.info(f"Paper order cancelled: {order_id}")
        return True
    
    def get_portfolio(
        self,
        user_id: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Get paper trading portfolio summary.
        
        Calculates portfolio metrics from open trades in the database.
        Returns safe defaults if no trades exist.
        
        Args:
            user_id: Optional user ID
            db: Optional database session
            
        Returns:
            Portfolio summary dictionary with keys:
            - total_value: Total portfolio value
            - cash: Available cash
            - positions_value: Value of open positions
            - open_pl: Open profit/loss
            - open_pl_pct: Open profit/loss percentage
            - num_open_trades: Number of open trades
        """
        try:
            # Default safe values
            portfolio = {
                "total_value": self.initial_cash,
                "cash": self.initial_cash,
                "positions_value": 0.0,
                "open_pl": 0.0,
                "open_pl_pct": 0.0,
                "num_open_trades": 0,
            }
            
            # If no database session, return defaults
            if db is None or user_id is None:
                return portfolio
            
            # Query open trades for user
            open_trades = db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.status == "open"
            ).all()
            
            if not open_trades:
                return portfolio
            
            # Calculate positions value and open P/L from trades
            positions_value = 0.0
            open_pl = 0.0
            
            for trade in open_trades:
                if trade.entry_price and trade.quantity:
                    # Approximate position value
                    position_value = trade.entry_price * trade.quantity
                    positions_value += position_value
                    
                    # If exit price available, calculate P/L
                    if trade.exit_price:
                        trade_pl = (trade.exit_price - trade.entry_price) * trade.quantity
                        open_pl += trade_pl
            
            # Calculate totals
            total_value = self.initial_cash + open_pl
            cash = self.initial_cash - positions_value
            open_pl_pct = (open_pl / self.initial_cash * 100) if self.initial_cash > 0 else 0.0
            
            portfolio.update({
                "total_value": round(total_value, 2),
                "cash": round(cash, 2),
                "positions_value": round(positions_value, 2),
                "open_pl": round(open_pl, 2),
                "open_pl_pct": round(open_pl_pct, 2),
                "num_open_trades": len(open_trades),
            })
            
            if self.enable_logging:
                logger.info(f"Portfolio for user {user_id}: {portfolio}")
            
            return portfolio
            
        except Exception as e:
            logger.error(f"Error getting portfolio for user {user_id}: {e}", exc_info=True)
            # Return safe defaults on error
            return {
                "total_value": self.initial_cash,
                "cash": self.initial_cash,
                "positions_value": 0.0,
                "open_pl": 0.0,
                "open_pl_pct": 0.0,
                "num_open_trades": 0,
            }
