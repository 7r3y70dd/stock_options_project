"""Trade lifecycle management for paper and live trading.

Provides TradeManager class for managing trade approval, execution, and closure.
Handles signal-to-trade conversion with validation and error handling.
"""

import logging
from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.database import Signal, Trade, OptionContract, User
from app.risk.guardrails import RiskGuardrails, RiskDecision

logger = logging.getLogger(__name__)


class TradeManager:
    """Manages paper and live trade lifecycle operations.
    
    Responsible for:
    - Converting approved signals into trades
    - Validating signal ownership and status
    - Calculating entry prices from option contracts
    - Managing trade closure and P/L calculation
    - Enforcing risk guardrails before trade approval
    """

    def __init__(self):
        """Initialize trade manager with risk guardrails."""
        self.guardrails = RiskGuardrails()

    def approve_signal_as_paper_trade(
        self,
        user_id: int,
        signal_id: int,
        db: Session,
        quantity: int = 1,
    ) -> Trade:
        """Approve a pending signal as a paper trade.
        
        Converts a pending signal into an open paper trade with entry price
        calculated from the option contract mid-price. Validates signal and
        enforces risk guardrails before approval.
        
        Args:
            user_id: User ID (must match signal owner)
            signal_id: Signal ID to approve
            db: Database session
            quantity: Number of contracts (default 1)
            
        Returns:
            Created Trade object
            
        Raises:
            ValueError: If signal not found, belongs to different user, already traded,
                       has no option contract, or fails risk validation
        """
        try:
            # Load the signal
            signal = db.query(Signal).filter(
                Signal.id == signal_id,
            ).first()
            
            if not signal:
                raise ValueError(f"Signal {signal_id} not found")
            
            # Ensure it belongs to user_id
            if signal.user_id != user_id:
                raise ValueError(
                    f"Signal {signal_id} belongs to user {signal.user_id}, "
                    f"not user {user_id}"
                )
            
            # Ensure signal status is pending or open
            if signal.status not in ("pending", "open"):
                raise ValueError(
                    f"Signal {signal_id} has status '{signal.status}', "
                    f"cannot approve (must be 'pending' or 'open')"
                )
            
            # Ensure option_contract_id exists
            if not signal.option_contract_id:
                raise ValueError(
                    f"Signal {signal_id} has no linked option contract"
                )
            
            # Load the related option contract
            contract = db.query(OptionContract).filter(
                OptionContract.id == signal.option_contract_id,
            ).first()
            
            if not contract:
                raise ValueError(
                    f"Option contract {signal.option_contract_id} not found"
                )
            
            # Load user for risk validation
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Validate against risk guardrails
            risk_decision = self.guardrails.validate_signal(
                user, signal, contract
            )
            if not risk_decision.approved:
                raise ValueError(
                    f"Signal {signal_id} failed risk validation: "
                    f"{'; '.join(risk_decision.messages)}"
                )
            
            # Check kill switch
            if self.guardrails.is_kill_switch_active(db):
                raise ValueError(
                    f"Cannot approve signal {signal_id}: kill switch is active"
                )
            
            # Calculate entry price from option contract mid price
            entry_price = (contract.bid + contract.ask) / 2
            
            # Create trade row
            trade = Trade(
                user_id=user_id,
                signal_id=signal_id,
                option_contract_id=signal.option_contract_id,
                status="open",
                order_status="filled",
                entry_price=entry_price,
                quantity=quantity,
                opened_at=datetime.utcnow(),
                is_paper_trading=True,
                exit_rules=signal.exit_rules,
            )
            
            # Update signal status to prevent duplicate approvals
            signal.status = "approved"
            signal.updated_at = datetime.utcnow()
            
            # Add and commit
            db.add(trade)
            db.commit()
            db.refresh(trade)
            
            logger.info(
                f"Signal {signal_id} approved as paper trade {trade.id} "
                f"for user {user_id} at entry price {entry_price}"
            )
            
            return trade
            
        except ValueError as e:
            logger.warning(f"Validation error approving signal {signal_id}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Error approving signal {signal_id} as paper trade: {e}",
                exc_info=True,
            )
            db.rollback()
            raise ValueError(f"Failed to approve signal as paper trade: {str(e)}")

    def get_open_trades(
        self,
        user_id: int,
        db: Session,
    ) -> List[Trade]:
        """Get all open trades for a user.
        
        Args:
            user_id: User ID
            db: Database session
            
        Returns:
            List of open Trade objects
        """
        try:
            trades = db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.status == "open",
            ).order_by(Trade.opened_at.desc()).all()
            
            return trades
            
        except Exception as e:
            logger.error(
                f"Error getting open trades for user {user_id}: {e}",
                exc_info=True,
            )
            return []

    def close_trade(
        self,
        user_id: int,
        trade_id: int,
        db: Session,
        exit_price: float,
        exit_reason: str = "manual",
    ) -> Trade:
        """Close an open trade with exit price and P/L calculation.
        
        Args:
            user_id: User ID (must match trade owner)
            trade_id: Trade ID to close
            db: Database session
            exit_price: Price at which to exit the trade
            exit_reason: Reason for closing (default "manual")
            
        Returns:
            Closed Trade object with realized P/L
            
        Raises:
            ValueError: If trade not found, belongs to different user,
                       or is not open
        """
        try:
            # Load trade by user_id and trade_id
            trade = db.query(Trade).filter(
                Trade.id == trade_id,
                Trade.user_id == user_id,
            ).first()
            
            if not trade:
                raise ValueError(
                    f"Trade {trade_id} not found for user {user_id}"
                )
            
            # Require status == "open"
            if trade.status != "open":
                raise ValueError(
                    f"Trade {trade_id} has status '{trade.status}', "
                    f"cannot close (must be 'open')"
                )
            
            # Calculate approximate realized P/L
            # For options: (exit_price - entry_price) * quantity * 100
            # (multiplier of 100 for standard option contract)
            realized_pnl = round(
                (float(exit_price) - float(trade.entry_price))
                * int(trade.quantity)
                * 100,
                2,
            )
            
            # Set exit fields
            trade.status = "closed"
            trade.closed_at = datetime.utcnow()
            trade.exit_price = exit_price
            trade.exit_reason = exit_reason
            trade.realized_pnl = realized_pnl
            
            # Commit
            db.commit()
            db.refresh(trade)
            
            logger.info(
                f"Trade {trade_id} closed for user {user_id} "
                f"at exit price {exit_price} with realized P/L {realized_pnl}"
            )
            
            return trade
            
        except ValueError as e:
            logger.warning(f"Validation error closing trade {trade_id}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Error closing trade {trade_id}: {e}",
                exc_info=True,
            )
            db.rollback()
            raise ValueError(f"Failed to close trade: {str(e)}")
