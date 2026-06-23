"""Services module for business logic."""

from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass


class RiskLevel(str, Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RejectionReason(str, Enum):
    """Reason for rejecting an option contract."""
    PASSED = "passed"
    EXPIRED = "expired"
    MISSING_BID_ASK = "missing_bid_ask"
    VOLUME_TOO_LOW = "volume_too_low"
    OPEN_INTEREST_TOO_LOW = "open_interest_too_low"
    BID_ASK_SPREAD_TOO_WIDE = "bid_ask_spread_too_wide"
    OUTSIDE_EXPIRATION_WINDOW = "outside_expiration_window"
    UNACCEPTABLE_GREEKS = "unacceptable_greeks"
    MAX_LOSS_EXCEEDED = "max_loss_exceeded"
    MAX_CONTRACTS_EXCEEDED = "max_contracts_exceeded"
    MAX_DAILY_LOSS_EXCEEDED = "max_daily_loss_exceeded"
    MAX_OPEN_POSITIONS_EXCEEDED = "max_open_positions_exceeded"
    EARNINGS_WINDOW_RESTRICTED = "earnings_window_restricted"
    LIVE_TRADING_NOT_APPROVED = "live_trading_not_approved"


@dataclass
class RiskGuardrail:
    """Base class for risk guardrails."""
    pass


class RiskConfig:
    """Configuration for a risk level."""
    def __init__(
        self,
        risk_level: RiskLevel,
        min_volume: int = 100,
        min_open_interest: int = 50,
        max_bid_ask_spread_pct: float = 5.0,
        min_days_to_expiration: int = 7,
        max_days_to_expiration: int = 60,
    ):
        self.risk_level = risk_level
        self.min_volume = min_volume
        self.min_open_interest = min_open_interest
        self.max_bid_ask_spread_pct = max_bid_ask_spread_pct
        self.min_days_to_expiration = min_days_to_expiration
        self.max_days_to_expiration = max_days_to_expiration


def get_risk_config(risk_level: RiskLevel) -> RiskConfig:
    """Get risk configuration for a risk level.
    
    Args:
        risk_level: The RiskLevel to get config for
        
    Returns:
        RiskConfig with appropriate thresholds
    """
    configs = {
        RiskLevel.LOW: RiskConfig(
            risk_level=RiskLevel.LOW,
            min_volume=500,
            min_open_interest=200,
            max_bid_ask_spread_pct=2.0,
            min_days_to_expiration=14,
            max_days_to_expiration=45,
        ),
        RiskLevel.MEDIUM: RiskConfig(
            risk_level=RiskLevel.MEDIUM,
            min_volume=100,
            min_open_interest=50,
            max_bid_ask_spread_pct=5.0,
            min_days_to_expiration=7,
            max_days_to_expiration=60,
        ),
        RiskLevel.HIGH: RiskConfig(
            risk_level=RiskLevel.HIGH,
            min_volume=10,
            min_open_interest=5,
            max_bid_ask_spread_pct=10.0,
            min_days_to_expiration=1,
            max_days_to_expiration=90,
        ),
    }
    return configs.get(risk_level, configs[RiskLevel.MEDIUM])


# Export commonly used classes for convenience
__all__ = [
    "RiskLevel",
    "RejectionReason",
    "RiskGuardrail",
    "RiskConfig",
    "get_risk_config",
]
