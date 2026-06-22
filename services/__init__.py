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
    """Enumeration of reasons a trade may be rejected by guardrails."""
    MAX_LOSS_EXCEEDED = "max_loss_exceeded"
    MAX_CONTRACTS_EXCEEDED = "max_contracts_exceeded"
    MAX_DAILY_LOSS_EXCEEDED = "max_daily_loss_exceeded"
    MAX_OPEN_POSITIONS_EXCEEDED = "max_open_positions_exceeded"
    BID_ASK_SPREAD_TOO_WIDE = "bid_ask_spread_too_wide"
    VOLUME_TOO_LOW = "volume_too_low"
    OPEN_INTEREST_TOO_LOW = "open_interest_too_low"
    EARNINGS_WINDOW_RESTRICTED = "earnings_window_restricted"
    LIVE_TRADING_NOT_APPROVED = "live_trading_not_approved"
    PASSED = "passed"


@dataclass
class RiskGuardrail:
    """Result of a trade validation against guardrails.
    
    Attributes:
        passed: Whether the trade passed all guardrails.
        reason: RejectionReason enum value.
        message: Human-readable explanation of the result.
    """
    passed: bool
    reason: RejectionReason
    message: str


@dataclass
class RiskLevelConfig:
    """Configuration for each risk level defining concrete behaviors.
    
    Attributes:
        risk_level: The RiskLevel enum value.
        allowed_strategies: List of allowed strategy types.
        max_position_size_pct: Maximum position size as % of portfolio.
        max_loss_per_trade_pct: Maximum loss per trade as % of portfolio.
        min_days_to_expiration: Minimum days to expiration for contracts.
        max_days_to_expiration: Maximum days to expiration for contracts.
        moneyness_range: Tuple of (min_moneyness, max_moneyness) for strikes.
        min_liquidity_score: Minimum liquidity score (0-100).
        scoring_weights: Dict of factor weights for scoring calculation.
        warning_thresholds: Dict of thresholds for warning flags.
        max_daily_loss_pct: Maximum daily loss as % of portfolio.
        max_open_positions: Maximum number of open positions.
        min_volume: Minimum contract volume required.
        min_open_interest: Minimum open interest required.
        max_bid_ask_spread_pct: Maximum bid-ask spread as % of mid price.
        earnings_buffer_days: Days before/after earnings to restrict trading.
    """
    risk_level: RiskLevel
    allowed_strategies: List[str]
    max_position_size_pct: float
    max_loss_per_trade_pct: float
    min_days_to_expiration: int
    max_days_to_expiration: int
    moneyness_range: tuple  # (min, max) e.g., (0.95, 1.05) for ATM
    min_liquidity_score: float
    scoring_weights: Dict[str, float]
    warning_thresholds: Dict[str, float]
    max_daily_loss_pct: float = 5.0
    max_open_positions: int = 10
    min_volume: int = 10
    min_open_interest: int = 10
    max_bid_ask_spread_pct: float = 0.10
    earnings_buffer_days: int = 3


# Risk level configurations defining concrete behaviors
RISK_CONFIGS = {
    RiskLevel.LOW: RiskLevelConfig(
        risk_level=RiskLevel.LOW,
        allowed_strategies=[
            "covered_call",
            "cash_secured_put",
            "bull_call_spread",
            "bear_call_spread",
            "bull_put_spread",
            "bear_put_spread",
        ],
        max_position_size_pct=5.0,
        max_loss_per_trade_pct=2.0,
        min_days_to_expiration=7,
        max_days_to_expiration=60,
        moneyness_range=(0.95, 1.05),  # Near-the-money only
        min_liquidity_score=70.0,
        scoring_weights={
            "liquidity": 0.30,
            "spread": 0.25,
            "moneyness": 0.20,
            "volatility": 0.15,
            "time_decay": 0.10,
        },
        warning_thresholds={
            "wide_spread": 0.05,  # Warn if spread > 5% of mid
            "low_volume": 50,
            "low_open_interest": 100,
            "high_iv_rank": 0.80,
        },
        max_daily_loss_pct=3.0,
        max_open_positions=5,
        min_volume=50,
        min_open_interest=100,
        max_bid_ask_spread_pct=0.05,
        earnings_buffer_days=5,
    ),
    RiskLevel.MEDIUM: RiskLevelConfig(
        risk_level=RiskLevel.MEDIUM,
        allowed_strategies=[
            "covered_call",
            "cash_secured_put",
            "bull_call_spread",
            "bear_call_spread",
            "bull_put_spread",
            "bear_put_spread",
            "debit_spread",
            "credit_spread",
            "earnings_aware_call",
            "earnings_aware_put",
        ],
        max_position_size_pct=10.0,
        max_loss_per_trade_pct=5.0,
        min_days_to_expiration=3,
        max_days_to_expiration=90,
        moneyness_range=(0.90, 1.10),  # Slightly wider range
        min_liquidity_score=50.0,
        scoring_weights={
            "liquidity": 0.25,
            "spread": 0.20,
            "moneyness": 0.20,
            "volatility": 0.20,
            "time_decay": 0.15,
        },
        warning_thresholds={
            "wide_spread": 0.08,
            "low_volume": 20,
            "low_open_interest": 50,
            "high_iv_rank": 0.90,
        },
        max_daily_loss_pct=5.0,
        max_open_positions=10,
        min_volume=20,
        min_open_interest=50,
        max_bid_ask_spread_pct=0.08,
        earnings_buffer_days=3,
    ),
    RiskLevel.HIGH: RiskLevelConfig(
        risk_level=RiskLevel.HIGH,
        allowed_strategies=[
            "long_call",
            "long_put",
            "short_call",  # Short-duration only
            "short_put",   # Short-duration only
            "bull_call_spread",
            "bear_call_spread",
            "bull_put_spread",
            "bear_put_spread",
            "debit_spread",
            "credit_spread",
            "earnings_aware_call",
            "earnings_aware_put",
            "high_iv_call",
            "high_iv_put",
        ],
        max_position_size_pct=15.0,
        max_loss_per_trade_pct=10.0,
        min_days_to_expiration=1,
        max_days_to_expiration=120,
        moneyness_range=(0.80, 1.20),  # Wider range for directional plays
        min_liquidity_score=30.0,
        scoring_weights={
            "liquidity": 0.15,
            "spread": 0.10,
            "moneyness": 0.15,
            "volatility": 0.30,
            "time_decay": 0.30,
        },
        warning_thresholds={
            "wide_spread": 0.12,
            "low_volume": 5,
            "low_open_interest": 10,
            "high_iv_rank": 0.95,
        },
        max_daily_loss_pct=10.0,
        max_open_positions=15,
        min_volume=5,
        min_open_interest=10,
        max_bid_ask_spread_pct=0.12,
        earnings_buffer_days=1,
    ),
}


def get_risk_config(risk_level: RiskLevel) -> RiskLevelConfig:
    """Retrieve configuration for a given risk level.
    
    Args:
        risk_level: The RiskLevel enum value.
    
    Returns:
        RiskLevelConfig for the specified risk level.
    
    Raises:
        ValueError: If risk_level is not recognized.
    """
    if risk_level not in RISK_CONFIGS:
        raise ValueError(f"Unknown risk level: {risk_level}")
    return RISK_CONFIGS[risk_level]
