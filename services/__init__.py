"""Services module for Options Tracker.

Defines risk level configurations and helper functions for options analysis.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional


class RiskLevel(Enum):
    """Risk level enumeration for strategy filtering and position sizing."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RejectionReason(Enum):
    """Enumeration of rejection reasons for trade validation."""
    MAX_LOSS_EXCEEDED = "max_loss_exceeded"
    MAX_CONTRACTS_EXCEEDED = "max_contracts_exceeded"
    MAX_DAILY_LOSS_EXCEEDED = "max_daily_loss_exceeded"
    MAX_OPEN_POSITIONS_EXCEEDED = "max_open_positions_exceeded"
    BID_ASK_SPREAD_TOO_WIDE = "bid_ask_spread_too_wide"
    VOLUME_TOO_LOW = "volume_too_low"
    OPEN_INTEREST_TOO_LOW = "open_interest_too_low"
    EARNINGS_WINDOW_RESTRICTED = "earnings_window_restricted"
    LIVE_TRADING_NOT_APPROVED = "live_trading_not_approved"


@dataclass
class RiskGuardrail:
    """Result of a risk guardrail validation."""
    passed: bool
    reason: Optional[RejectionReason] = None
    message: str = ""


@dataclass
class RiskLevelConfig:
    """Configuration for a risk level."""
    risk_level: RiskLevel
    max_loss_per_trade_pct: float
    max_contracts_per_trade: int
    max_daily_loss_pct: float
    max_open_positions: int
    max_bid_ask_spread_pct: float
    min_volume: int
    min_open_interest: int
    earnings_window_days: int


# Risk level configurations
RISK_CONFIGS: Dict[RiskLevel, RiskLevelConfig] = {
    RiskLevel.LOW: RiskLevelConfig(
        risk_level=RiskLevel.LOW,
        max_loss_per_trade_pct=2.0,
        max_contracts_per_trade=5,
        max_daily_loss_pct=3.0,
        max_open_positions=5,
        max_bid_ask_spread_pct=0.05,  # 5%
        min_volume=50,
        min_open_interest=100,
        earnings_window_days=5,
    ),
    RiskLevel.MEDIUM: RiskLevelConfig(
        risk_level=RiskLevel.MEDIUM,
        max_loss_per_trade_pct=5.0,
        max_contracts_per_trade=10,
        max_daily_loss_pct=10.0,
        max_open_positions=10,
        max_bid_ask_spread_pct=0.10,  # 10%
        min_volume=20,
        min_open_interest=50,
        earnings_window_days=3,
    ),
    RiskLevel.HIGH: RiskLevelConfig(
        risk_level=RiskLevel.HIGH,
        max_loss_per_trade_pct=10.0,
        max_contracts_per_trade=20,
        max_daily_loss_pct=20.0,
        max_open_positions=20,
        max_bid_ask_spread_pct=0.20,  # 20%
        min_volume=5,
        min_open_interest=10,
        earnings_window_days=1,
    ),
}


def get_risk_config(risk_level: RiskLevel) -> RiskLevelConfig:
    """Get risk configuration for a risk level.
    
    Args:
        risk_level: Risk level to get configuration for
        
    Returns:
        RiskLevelConfig for the specified risk level
    """
    return RISK_CONFIGS.get(risk_level, RISK_CONFIGS[RiskLevel.MEDIUM])


__all__ = [
    "RiskLevel",
    "RejectionReason",
    "RiskGuardrail",
    "RiskLevelConfig",
    "get_risk_config",
]
