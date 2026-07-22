"""Trade manager for executing and tracking trades.

Handles trade execution, position tracking, P/L calculations, and exit rule monitoring.
For covered calls, calculates combined P/L including both option and underlying stock legs.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from sqlalchemy.orm import Session

from app.models.database import Trade, Signal, User, OptionContract
from app.core.broker_provider import BrokerProvider
from app.core.paper_broker_provider import PaperBrokerProvider
from app.data_sources.data_provider import DataProvider

logger = logging.getLogger(__name__)


class TradeManager:
    """Manages trade execution and tracking.
    
    Handles:
    - Trade execution (paper and live)
    - Position tracking
    - P/L calculations (including combined covered call P/L)
    - Exit rule monitoring
    - Trade updates
    """

    def __init__(
        self,
        db: Session,
        broker_provider: Optional[BrokerProvider] = None,
        data_provider: Optional[DataProvider] = None,
    ):
        """Initialize trade manager.
        
        Args:
            db: Database session
            broker_provider: Broker provider for live trades
            data_provider: Data provider for market data
        """
        self.db = db
        self.broker_provider = broker_provider or PaperBrokerProvider()
        self.data_provider = data_provider

    def execute_trade(
        self,
        user_id: int,
        signal_id: int,
        quantity: int = 1,
        is_paper_trade: bool = True,
        underlying_entry_price: Optional[float] = None,
        underlying_quantity: Optional[int] = None,
    ) -> Optional[Trade]:
        """Execute a trade based on a signal.
        
        Args:
            user_id: User ID
            signal_id: Signal ID to execute
            quantity: Number of contracts
            is_paper_trade: Whether this is a paper trade
            underlying_entry_price: Stock entry price for covered calls
            underlying_quantity: Number of shares for covered calls
            
        Returns:
            Trade object if successful, None otherwise
        """
        # Get signal
        signal = self.db.query(Signal).filter(Signal.id == signal_id).first()
        if not signal:
            logger.error(f"Signal {signal_id} not found")
            return None

        # Get user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found")
            return None

        # Check if paper trading is enabled
        if is_paper_trade and not user.paper_trading_enabled:
            logger.error(f"Paper trading disabled for user {user_id}")
            return None

        # Check if live trading is enabled and approved
        if not is_paper_trade and (not user.live_trading_enabled or not user.live_trading_approved):
            logger.error(f"Live trading not enabled/approved for user {user_id}")
            return None

        # Get option contract
        option_contract = None
        if signal.option_contract_id:
            option_contract = self.db.query(OptionContract).filter(
                OptionContract.id == signal.option_contract_id
            ).first()

        # Determine entry price
        entry_price = 0.0
        if option_contract:
            # Use mid-price as entry
            entry_price = (option_contract.bid + option_contract.ask) / 2
        else:
            logger.warning(f"No option contract linked to signal {signal_id}")

        # For covered calls, determine underlying stock information
        underlying_entry = underlying_entry_price
        underlying_qty = underlying_quantity
        
        if signal.strategy_type == "covered_call":
            if underlying_entry is None and option_contract:
                # Fallback: use current underlying price as estimated basis
                underlying_entry = option_contract.underlying_price
                logger.warning(
                    f"No underlying entry price provided for covered call {signal.symbol}. "
                    f"Using current price ${underlying_entry:.2f} as estimated basis."
                )
            
            if underlying_qty is None:
                # Standard covered call: 100 shares per contract
                underlying_qty = 100 * quantity

        # Create trade record
        trade = Trade(
            user_id=user_id,
            signal_id=signal_id,
            symbol=signal.symbol,
            strategy_type=signal.strategy_type,
            option_contract_id=signal.option_contract_id,
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            underlying_entry_price=underlying_entry,
            underlying_current_price=underlying_entry if underlying_entry else None,
            underlying_quantity=underlying_qty,
            status="open",
            is_paper_trade=is_paper_trade,
            opened_at=datetime.utcnow(),
        )

        # Calculate initial P/L (should be zero at entry)
        self._update_trade_pnl(trade)

        # Save to database
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)

        # Update signal status
        signal.status = "executed"
        self.db.commit()

        logger.info(
            f"Executed {signal.strategy_type} trade for {signal.symbol}: "
            f"quantity={quantity}, entry_price=${entry_price:.2f}, "
            f"underlying_entry=${underlying_entry:.2f if underlying_entry else 'N/A'}, "
            f"paper={is_paper_trade}"
        )

        return trade

    def update_trade_prices(
        self,
        trade_id: int,
        current_option_price: Optional[float] = None,
        current_stock_price: Optional[float] = None,
    ) -> Optional[Trade]:
        """Update trade with current market prices and recalculate P/L.
        
        Args:
            trade_id: Trade ID
            current_option_price: Current option price
            current_stock_price: Current underlying stock price
            
        Returns:
            Updated trade object
        """
        trade = self.db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            logger.error(f"Trade {trade_id} not found")
            return None

        if trade.status != "open":
            logger.debug(f"Trade {trade_id} is not open, skipping price update")
            return trade

        # Update option price
        if current_option_price is not None:
            trade.current_price = current_option_price

        # Update stock price for covered calls
        if current_stock_price is not None and trade.strategy_type == "covered_call":
            trade.underlying_current_price = current_stock_price

        # Recalculate P/L
        self._update_trade_pnl(trade)

        self.db.commit()
        self.db.refresh(trade)

        return trade

    def close_trade(
        self,
        trade_id: int,
        exit_price: Optional[float] = None,
        exit_rule: Optional[str] = None,
    ) -> Optional[Trade]:
        """Close a trade.
        
        Args:
            trade_id: Trade ID
            exit_price: Exit price (if None, uses current_price)
            exit_rule: Exit rule that triggered the close
            
        Returns:
            Closed trade object
        """
        trade = self.db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            logger.error(f"Trade {trade_id} not found")
            return None

        if trade.status != "open":
            logger.warning(f"Trade {trade_id} is already closed")
            return trade

        # Use current price if exit price not provided
        if exit_price is None:
            exit_price = trade.current_price

        trade.exit_price = exit_price
        trade.status = "closed"
        trade.closed_at = datetime.utcnow()
        trade.exit_rule_applied = exit_rule

        # Calculate final realized P/L
        self._update_trade_pnl(trade, is_closing=True)
        trade.realized_pnl = trade.unrealized_pnl
        trade.unrealized_pnl = 0.0

        self.db.commit()
        self.db.refresh(trade)

        logger.info(
            f"Closed trade {trade_id} for {trade.symbol}: "
            f"realized_pnl=${trade.realized_pnl:.2f}, exit_rule={exit_rule}"
        )

        return trade

    def get_open_trades(self, user_id: int) -> List[Trade]:
        """Get all open trades for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of open trades
        """
        return self.db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.status == "open"
        ).all()

    def get_trade_details(self, trade_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed trade information including P/L breakdown.
        
        Args:
            trade_id: Trade ID
            
        Returns:
            Dictionary with trade details and P/L breakdown
        """
        trade = self.db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            return None

        details = {
            "id": trade.id,
            "symbol": trade.symbol,
            "strategy_type": trade.strategy_type,
            "quantity": trade.quantity,
            "status": trade.status,
            "entry_price": trade.entry_price,
            "current_price": trade.current_price,
            "exit_price": trade.exit_price,
            "opened_at": trade.opened_at.isoformat() if trade.opened_at else None,
            "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
            "is_paper_trade": trade.is_paper_trade,
        }

        # Add P/L information
        if trade.strategy_type == "covered_call":
            # Covered call: show separate option and stock P/L
            details["option_pnl"] = trade.option_pnl or 0.0
            details["stock_pnl"] = trade.stock_pnl or 0.0
            details["total_pnl"] = trade.unrealized_pnl if trade.status == "open" else trade.realized_pnl
            details["underlying_entry_price"] = trade.underlying_entry_price
            details["underlying_current_price"] = trade.underlying_current_price
            details["underlying_quantity"] = trade.underlying_quantity
            
            # Calculate metrics
            if trade.underlying_entry_price and trade.underlying_quantity:
                premium_received = trade.entry_price * 100 * trade.quantity
                details["premium_received"] = premium_received
                
                # Premium captured percentage
                if trade.option_pnl is not None and premium_received > 0:
                    details["premium_captured_pct"] = (trade.option_pnl / premium_received) * 100
                
                # Total position return percentage
                net_capital = (trade.underlying_entry_price * trade.underlying_quantity) - premium_received
                if net_capital > 0 and details["total_pnl"] is not None:
                    details["total_return_pct"] = (details["total_pnl"] / net_capital) * 100
                
                # Break-even
                premium_per_share = trade.entry_price
                details["break_even"] = trade.underlying_entry_price - premium_per_share
                
                # Maximum profit (if option contract available)
                if trade.option_contract:
                    option_contract = self.db.query(OptionContract).filter(
                        OptionContract.id == trade.option_contract_id
                    ).first()
                    if option_contract:
                        stock_appreciation = (option_contract.strike - trade.underlying_entry_price) * trade.underlying_quantity
                        details["max_profit"] = stock_appreciation + premium_received
                        details["strike"] = option_contract.strike
                        details["expiration"] = option_contract.expiration
        else:
            # Other strategies: show total P/L only
            details["total_pnl"] = trade.unrealized_pnl if trade.status == "open" else trade.realized_pnl
            details["option_pnl"] = details["total_pnl"]

        return details

    def refresh_all_open_trades(self, user_id: int) -> int:
        """Refresh prices for all open trades.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of trades updated
        """
        if not self.data_provider:
            logger.warning("No data provider configured, cannot refresh trade prices")
            return 0

        open_trades = self.get_open_trades(user_id)
        updated_count = 0

        for trade in open_trades:
            try:
                # Get current stock price
                stock_quote = self.data_provider.get_quote(trade.symbol)
                current_stock_price = stock_quote.get("price") if stock_quote else None

                # Get current option price if option contract exists
                current_option_price = None
                if trade.option_contract_id:
                    option_contract = self.db.query(OptionContract).filter(
                        OptionContract.id == trade.option_contract_id
                    ).first()
                    if option_contract:
                        # Refresh option contract data
                        # For now, use existing bid/ask as approximation
                        current_option_price = (option_contract.bid + option_contract.ask) / 2

                # Update trade
                self.update_trade_prices(
                    trade_id=trade.id,
                    current_option_price=current_option_price,
                    current_stock_price=current_stock_price,
                )
                updated_count += 1

            except Exception as e:
                logger.error(f"Error refreshing trade {trade.id}: {e}")

        logger.info(f"Refreshed {updated_count} open trades for user {user_id}")
        return updated_count

    def _update_trade_pnl(self, trade: Trade, is_closing: bool = False) -> None:
        """Update trade P/L calculations.
        
        For covered calls, calculates:
        - option_pnl: P/L from short call option
        - stock_pnl: P/L from underlying shares
        - unrealized_pnl: Combined total P/L
        
        For other strategies:
        - unrealized_pnl: Option P/L only
        
        Args:
            trade: Trade object to update
            is_closing: Whether this is a closing calculation
        """
        if trade.strategy_type == "covered_call":
            # Calculate option P/L (short call)
            # For short calls: profit when option price decreases
            option_price_change = trade.entry_price - (trade.exit_price if is_closing else trade.current_price)
            trade.option_pnl = option_price_change * 100 * trade.quantity

            # Calculate stock P/L
            if trade.underlying_entry_price and trade.underlying_current_price and trade.underlying_quantity:
                stock_price_change = trade.underlying_current_price - trade.underlying_entry_price
                trade.stock_pnl = stock_price_change * trade.underlying_quantity
            else:
                trade.stock_pnl = 0.0

            # Combined P/L
            trade.unrealized_pnl = trade.option_pnl + trade.stock_pnl

        else:
            # Other strategies: calculate option P/L only
            # Assume long positions for now (profit when price increases)
            price_change = (trade.exit_price if is_closing else trade.current_price) - trade.entry_price
            trade.unrealized_pnl = price_change * 100 * trade.quantity
            trade.option_pnl = trade.unrealized_pnl
            trade.stock_pnl = 0.0

    def get_portfolio_summary(self, user_id: int) -> Dict[str, Any]:
        """Get portfolio summary including total P/L.
        
        Args:
            user_id: User ID
            
        Returns:
            Portfolio summary dictionary
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}

        open_trades = self.get_open_trades(user_id)
        
        total_unrealized_pnl = 0.0
        total_option_pnl = 0.0
        total_stock_pnl = 0.0
        positions_value = 0.0

        for trade in open_trades:
            if trade.unrealized_pnl:
                total_unrealized_pnl += trade.unrealized_pnl
            if trade.option_pnl:
                total_option_pnl += trade.option_pnl
            if trade.stock_pnl:
                total_stock_pnl += trade.stock_pnl
            
            # Calculate position value
            if trade.current_price:
                positions_value += trade.current_price * 100 * trade.quantity
            
            # Add underlying stock value for covered calls
            if trade.strategy_type == "covered_call" and trade.underlying_current_price and trade.underlying_quantity:
                positions_value += trade.underlying_current_price * trade.underlying_quantity

        # Calculate cash (simplified: initial capital minus positions value)
        cash = user.initial_portfolio_value - positions_value
        total_value = cash + positions_value + total_unrealized_pnl

        return {
            "total_value": total_value,
            "cash": cash,
            "positions_value": positions_value,
            "total_unrealized_pnl": total_unrealized_pnl,
            "option_pnl": total_option_pnl,
            "stock_pnl": total_stock_pnl,
            "num_open_trades": len(open_trades),
        }
