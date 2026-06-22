"""Services module for options analysis and risk management.

Provides risk-level-aware configuration, rejection reasons, and guardrail validation.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class RiskLevel(str, Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RejectionReason(str, Enum):
    """Reasons for rejecting option contracts or trades."""
    PASSED = "passed"
    EXPIRED = "expired"
    MISSING_BID_ASK = "missing_bid_ask"
    VOLUME_TOO_LOW = "volume_too_low"
    OPEN_INTEREST_TOO_LOW = "open_interest_too_low"
    BID_ASK_SPREAD_TOO_WIDE = "bid_ask_spread_too_wide"
    OUTSIDE_EXPIRATION_WINDOW = "outside_expiration_window"
    EARNINGS_WINDOW_RESTRICTED = "earnings_window_restricted"
    MAX_LOSS_EXCEEDED = "max_loss_exceeded"
    MAX_CONTRACTS_EXCEEDED = "max_contracts_exceeded"
    MAX_DAILY_LOSS_EXCEEDED = "max_daily_loss_exceeded"
    MAX_OPEN_POSITIONS_EXCEEDED = "max_open_positions_exceeded"
    LIVE_TRADING_NOT_APPROVED = "live_trading_not_approved"


@dataclass
class RiskGuardrail:
    """Result of a risk guardrail validation."""
    passed: bool
    reason: RejectionReason
    message: str


@dataclass
class RiskConfig:
    """Risk configuration for a specific risk level."""
    max_loss_per_trade_pct: float
    max_daily_loss_pct: float
    max_open_positions: int
    max_bid_ask_spread_pct: float
    min_volume: int
    min_open_interest: int
    min_days_to_expiration: int
    max_days_to_expiration: int
    earnings_buffer_days: int
    allowed_strategies: list
    moneyness_range: tuple
    scoring_weights: dict


def get_risk_config(risk_level: RiskLevel) -> RiskConfig:
    """Get risk configuration for a specific risk level.
    
    Args:
        risk_level: The RiskLevel to get configuration for.
    
    Returns:
        RiskConfig with guardrails and parameters for the risk level.
    """
    configs = {
        RiskLevel.LOW: RiskConfig(
            max_loss_per_trade_pct=2.0,
            max_daily_loss_pct=3.0,
            max_open_positions=5,
            max_bid_ask_spread_pct=0.05,  # 5%
            min_volume=50,
            min_open_interest=100,
            min_days_to_expiration=7,
            max_days_to_expiration=60,
            earnings_buffer_days=5,
            allowed_strategies=["covered_call", "cash_secured_put"],
            moneyness_range=(0.95, 1.05),
            scoring_weights={
                "liquidity": 0.25,
                "spread": 0.25,
                "moneyness": 0.20,
                "volatility": 0.15,
                "time_decay": 0.15,
            },
        ),
        RiskLevel.MEDIUM: RiskConfig(
            max_loss_per_trade_pct=5.0,
            max_daily_loss_pct=7.0,
            max_open_positions=10,
            max_bid_ask_spread_pct=0.10,  # 10%
            min_volume=20,
            min_open_interest=50,
            min_days_to_expiration=5,
            max_days_to_expiration=90,
            earnings_buffer_days=3,
            allowed_strategies=[
                "covered_call",
                "cash_secured_put",
                "bull_call_spread",
                "bear_put_spread",
            ],
            moneyness_range=(0.90, 1.10),
            scoring_weights={
                "liquidity": 0.20,
                "spread": 0.20,
                "moneyness": 0.25,
                "volatility": 0.20,
                "time_decay": 0.15,
            },
        ),
        RiskLevel.HIGH: RiskConfig(
            max_loss_per_trade_pct=10.0,
            max_daily_loss_pct=15.0,
            max_open_positions=20,
            max_bid_ask_spread_pct=0.20,  # 20%
            min_volume=5,
            min_open_interest=10,
            min_days_to_expiration=3,
            max_days_to_expiration=180,
            earnings_buffer_days=1,
            allowed_strategies=[
                "covered_call",
                "cash_secured_put",
                "bull_call_spread",
                "bear_put_spread",
                "iron_condor",
                "butterfly",
                "straddle",
                "strangle",
            ],
            moneyness_range=(0.80, 1.20),
            scoring_weights={
                "liquidity": 0.15,
                "spread": 0.15,
                "moneyness": 0.30,
                "volatility": 0.25,
                "time_decay": 0.15,
            },
        ),
    }
    return configs.get(risk_level, configs[RiskLevel.MEDIUM])


__all__ = [
    "RiskLevel",
    "RejectionReason",
    "RiskGuardrail",
    "RiskConfig",
    "get_risk_config",
]
