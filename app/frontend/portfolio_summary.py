"""Portfolio Summary component for displaying portfolio metrics.

Provides a reusable card-based component for displaying:
- Total portfolio value
- Available cash
- Positions value
- Open P/L and P/L percentage
- Number of open trades
- Number of pending signals

Includes loading and error states.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ComponentState(str, Enum):
    """Component state enumeration."""
    IDLE = "idle"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"


def format_currency(value: float) -> str:
    """Format a value as currency.
    
    Args:
        value: Numeric value to format
        
    Returns:
        Formatted currency string (e.g., "$1,234.56")
    """
    if value is None:
        return "$0.00"
    return f"${value:,.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format a value as percentage.
    
    Args:
        value: Numeric value to format (e.g., 5.5 for 5.5%)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string (e.g., "5.50%")
    """
    if value is None:
        return "0.00%"
    return f"{value:.{decimals}f}%"


def format_number(value: int) -> str:
    """Format a number with thousands separator.
    
    Args:
        value: Integer value to format
        
    Returns:
        Formatted number string (e.g., "1,234")
    """
    if value is None:
        return "0"
    return f"{value:,}"


@dataclass
class PortfolioCard:
    """Individual portfolio metric card."""
    label: str
    value: str
    icon: Optional[str] = None
    trend: Optional[str] = None  # "up", "down", or None
    color: Optional[str] = None  # "positive", "negative", or None


class PortfolioSummaryComponent:
    """Portfolio Summary component for displaying portfolio metrics.
    
    Renders portfolio data as a card group with formatted values.
    Supports loading and error states.
    """

    def __init__(self):
        """Initialize portfolio summary component."""
        self.state = ComponentState.IDLE
        self.error_message: Optional[str] = None
        self.data: Optional[Dict[str, Any]] = None

    def set_loading(self) -> None:
        """Set component to loading state."""
        self.state = ComponentState.LOADING
        self.error_message = None

    def set_success(self, data: Dict[str, Any]) -> None:
        """Set component to success state with data.
        
        Args:
            data: Portfolio data from API
        """
        self.state = ComponentState.SUCCESS
        self.error_message = None
        self.data = data

    def set_error(self, error_message: str) -> None:
        """Set component to error state.
        
        Args:
            error_message: Error message to display
        """
        self.state = ComponentState.ERROR
        self.error_message = error_message
        self.data = None

    def render_loading(self) -> Dict[str, Any]:
        """Render loading state.
        
        Returns:
            Loading state component data
        """
        return {
            "type": "portfolio-summary",
            "state": "loading",
            "message": "Loading portfolio data...",
            "cards": [],
        }

    def render_error(self) -> Dict[str, Any]:
        """Render error state.
        
        Returns:
            Error state component data
        """
        return {
            "type": "portfolio-summary",
            "state": "error",
            "message": self.error_message or "Failed to load portfolio data",
            "cards": [],
            "action": {
                "label": "Retry",
                "callback": "retry_portfolio_load",
            },
        }

    def render_empty(self) -> Dict[str, Any]:
        """Render empty state.
        
        Returns:
            Empty state component data
        """
        return {
            "type": "portfolio-summary",
            "state": "empty",
            "message": "No portfolio data available",
            "cards": [],
        }

    def _build_cards(self) -> list:
        """Build portfolio metric cards from data.
        
        Returns:
            List of PortfolioCard objects
        """
        if not self.data:
            return []

        total_value = self.data.get("total_value", 0.0)
        cash = self.data.get("cash", 0.0)
        positions_value = self.data.get("positions_value", 0.0)
        open_pl = self.data.get("open_pl", 0.0)
        open_pl_pct = self.data.get("open_pl_pct", 0.0)
        num_open_trades = self.data.get("num_open_trades", 0)
        num_open_signals = self.data.get("num_open_signals", 0)

        # Determine P/L color and trend
        pl_color = "positive" if open_pl >= 0 else "negative"
        pl_trend = "up" if open_pl >= 0 else "down"

        cards = [
            PortfolioCard(
                label="Total Value",
                value=format_currency(total_value),
                icon="briefcase",
            ),
            PortfolioCard(
                label="Cash",
                value=format_currency(cash),
                icon="dollar-sign",
            ),
            PortfolioCard(
                label="Positions",
                value=format_currency(positions_value),
                icon="trending-up",
            ),
            PortfolioCard(
                label="Open P/L",
                value=f"{format_currency(open_pl)} ({format_percentage(open_pl_pct)})",
                icon="activity",
                trend=pl_trend,
                color=pl_color,
            ),
            PortfolioCard(
                label="Open Trades",
                value=format_number(num_open_trades),
                icon="layers",
            ),
            PortfolioCard(
                label="Pending Signals",
                value=format_number(num_open_signals),
                icon="bell",
            ),
        ]

        return cards

    def render(self) -> Dict[str, Any]:
        """Render portfolio summary component.
        
        Returns:
            Component data based on current state
        """
        if self.state == ComponentState.LOADING:
            return self.render_loading()
        elif self.state == ComponentState.ERROR:
            return self.render_error()
        elif self.state == ComponentState.SUCCESS and self.data:
            cards = self._build_cards()
            return {
                "type": "portfolio-summary",
                "state": "success",
                "title": "Portfolio Summary",
                "cards": [
                    {
                        "label": card.label,
                        "value": card.value,
                        "icon": card.icon,
                        "trend": card.trend,
                        "color": card.color,
                    }
                    for card in cards
                ],
            }
        else:
            return self.render_empty()
