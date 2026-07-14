"""Portfolio page helper module."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PortfolioSummary:
    """Portfolio summary data."""

    total_value: float
    cash: float
    positions_value: float
    open_pl: float
    open_pl_pct: float
    num_open_trades: int
    num_open_signals: int

    @classmethod
    def from_dict(cls, data: dict) -> "PortfolioSummary":
        """Create from dictionary."""
        return cls(
            total_value=data.get("total_value", 0.0),
            cash=data.get("cash", 0.0),
            positions_value=data.get("positions_value", 0.0),
            open_pl=data.get("open_pl", 0.0),
            open_pl_pct=data.get("open_pl_pct", 0.0),
            num_open_trades=data.get("num_open_trades", 0),
            num_open_signals=data.get("num_open_signals", 0),
        )

    def has_positions(self) -> bool:
        """Check if portfolio has open positions."""
        return self.positions_value > 0 or self.num_open_trades > 0
