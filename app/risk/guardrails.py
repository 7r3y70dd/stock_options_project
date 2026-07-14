"""Risk guardrails and limits for signal validation and trade approval.

Provides centralized risk validation logic used by signal generation,
paper-trade approval, and recommendation filtering.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RejectionReason(str, Enum):
    """Reason for rejecting a signal or trade."""
    STRATEGY_NOT_ALLOWED = "strategy_not_allowed"
    MAX_LOSS_EXCEEDED = "max_loss_exceeded"
    LOW_VOLUME = "low_volume"
    LOW_OPEN_INTEREST = "low_open_interest"
    WIDE_BID_ASK_SPREAD = "wide_bid_ask_spread"
    KILL_SWITCH_ACTIVE = "kill_switch_active"
    INVALID_CONTRACT = "invalid_contract"


@dataclass
class RiskDecision:
    """Result of risk guardrail validation."""
    approved: bool
    reasons: List[RejectionReason] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)


class RiskGuardrails:
    """Centralized risk validation for signals and trades.
    
    Enforces:
    - Strategy allowed by risk level
    - Max loss per trade as percentage of portfolio
    - Option liquidity thresholds
    - Kill switch activation
    """

    # Strategy allowlist by risk level
    ALLOWED_STRATEGIES = {
        RiskLevel.LOW: ["covered_call", "cash_secured_put"],
        RiskLevel.MEDIUM: [
            "covered_call",
            "cash_secured_put",
            "debit_spread",
            "credit_spread",
        ],
        RiskLevel.HIGH: [
            "covered_call",
            "cash_secured_put",
            "debit_spread",
            "credit_spread",
            "long_call",
            "long_put",
        ],
    }

    # Max loss per trade as percentage of initial portfolio value
    MAX_LOSS_PCT = {
        RiskLevel.LOW: 0.01,      # 1%
        RiskLevel.MEDIUM: 0.02,   # 2%
        RiskLevel.HIGH: 0.05,     # 5%
    }

    # Liquidity thresholds by risk level
    LIQUIDITY_THRESHOLDS = {
        RiskLevel.LOW: {
            "min_volume": 100,
            "min_open_interest": 500,
            "max_bid_ask_spread_pct": 0.10,
        },
        RiskLevel.MEDIUM: {
            "min_volume": 50,
            "min_open_interest": 250,
            "max_bid_ask_spread_pct": 0.20,
        },
        RiskLevel.HIGH: {
            "min_volume": 10,
            "min_open_interest": 100,
            "max_bid_ask_spread_pct": 0.35,
        },
    }

    def __init__(self):
        """Initialize risk guardrails."""
        pass

    def allowed_strategies_for_level(self, risk_level: str) -> List[str]:
        """Get list of allowed strategies for a risk level.
        
        Args:
            risk_level: Risk level string ("low", "medium", "high")
            
        Returns:
            List of allowed strategy names
        """
        try:
            level = RiskLevel(risk_level)
            return self.ALLOWED_STRATEGIES.get(level, [])
        except ValueError:
            logger.warning(f"Unknown risk level: {risk_level}")
            return []

    def validate_signal(self, user, signal, contract=None) -> RiskDecision:
        """Validate a signal against risk guardrails.
        
        Args:
            user: User object with risk_level and initial_portfolio_value
            signal: Signal object with strategy_type and max_loss
            contract: Optional OptionContract for liquidity checks
            
        Returns:
            RiskDecision with approval status and rejection reasons
        """
        decision = RiskDecision(approved=True)

        # Validate strategy is allowed for risk level
        try:
            risk_level = RiskLevel(user.risk_level)
        except ValueError:
            decision.approved = False
            decision.reasons.append(RejectionReason.INVALID_CONTRACT)
            decision.messages.append(f"Invalid risk level: {user.risk_level}")
            return decision

        allowed_strategies = self.ALLOWED_STRATEGIES.get(risk_level, [])
        if signal.strategy_type not in allowed_strategies:
            decision.approved = False
            decision.reasons.append(RejectionReason.STRATEGY_NOT_ALLOWED)
            decision.messages.append(
                f"Strategy '{signal.strategy_type}' not allowed for {risk_level.value} risk level. "
                f"Allowed: {', '.join(allowed_strategies)}"
            )

        # Validate max loss per trade
        max_loss_pct = self.MAX_LOSS_PCT.get(risk_level, 0.02)
        max_loss_allowed = user.initial_portfolio_value * max_loss_pct
        if signal.max_loss > max_loss_allowed:
            decision.approved = False
            decision.reasons.append(RejectionReason.MAX_LOSS_EXCEEDED)
            decision.messages.append(
                f"Max loss ${signal.max_loss:.2f} exceeds limit of ${max_loss_allowed:.2f} "
                f"({max_loss_pct*100:.1f}% of ${user.initial_portfolio_value:.2f})"
            )

        # Validate contract liquidity if provided
        if contract:
            liquidity_decision = self.validate_contract(
                user, contract, signal.strategy_type
            )
            if not liquidity_decision.approved:
                decision.approved = False
                decision.reasons.extend(liquidity_decision.reasons)
                decision.messages.extend(liquidity_decision.messages)

        return decision

    def validate_contract(
        self, user, contract, strategy_type: str
    ) -> RiskDecision:
        """Validate an option contract against liquidity guardrails.
        
        Args:
            user: User object with risk_level
            contract: OptionContract to validate
            strategy_type: Strategy type for context
            
        Returns:
            RiskDecision with approval status and rejection reasons
        """
        decision = RiskDecision(approved=True)

        try:
            risk_level = RiskLevel(user.risk_level)
        except ValueError:
            decision.approved = False
            decision.reasons.append(RejectionReason.INVALID_CONTRACT)
            decision.messages.append(f"Invalid risk level: {user.risk_level}")
            return decision

        thresholds = self.LIQUIDITY_THRESHOLDS.get(risk_level, {})

        # Check bid/ask validity
        if contract.bid is None or contract.ask is None:
            decision.approved = False
            decision.reasons.append(RejectionReason.INVALID_CONTRACT)
            decision.messages.append("Contract missing bid or ask price")
            return decision

        if contract.bid <= 0 or contract.ask <= 0:
            decision.approved = False
            decision.reasons.append(RejectionReason.INVALID_CONTRACT)
            decision.messages.append("Contract bid or ask price is not positive")
            return decision

        if contract.ask < contract.bid:
            decision.approved = False
            decision.reasons.append(RejectionReason.INVALID_CONTRACT)
            decision.messages.append(
                f"Contract ask (${contract.ask}) is less than bid (${contract.bid})"
            )
            return decision

        # Check volume
        min_volume = thresholds.get("min_volume", 50)
        if contract.volume is not None and contract.volume < min_volume:
            decision.approved = False
            decision.reasons.append(RejectionReason.LOW_VOLUME)
            decision.messages.append(
                f"Volume {contract.volume} below minimum {min_volume}"
            )

        # Check open interest
        min_open_interest = thresholds.get("min_open_interest", 250)
        if (
            contract.open_interest is not None
            and contract.open_interest < min_open_interest
        ):
            decision.approved = False
            decision.reasons.append(RejectionReason.LOW_OPEN_INTEREST)
            decision.messages.append(
                f"Open interest {contract.open_interest} below minimum {min_open_interest}"
            )

        # Check bid-ask spread
        max_spread_pct = thresholds.get("max_bid_ask_spread_pct", 0.20)
        mid_price = (contract.bid + contract.ask) / 2
        spread_pct = (contract.ask - contract.bid) / mid_price if mid_price > 0 else 0
        if spread_pct > max_spread_pct:
            decision.approved = False
            decision.reasons.append(RejectionReason.WIDE_BID_ASK_SPREAD)
            decision.messages.append(
                f"Bid-ask spread {spread_pct*100:.2f}% exceeds maximum {max_spread_pct*100:.2f}%"
            )

        return decision

    def is_kill_switch_active(self, db: Session) -> bool:
        """Check if kill switch is active.
        
        Args:
            db: Database session
            
        Returns:
            True if kill switch is active, False otherwise
        """
        try:
            # Import here to avoid circular imports
            from app.models.database import KillSwitch

            kill_switch = db.query(KillSwitch).filter(
                KillSwitch.is_active == True
            ).first()
            return kill_switch is not None
        except Exception as e:
            logger.warning(f"Error checking kill switch: {e}")
            return False
