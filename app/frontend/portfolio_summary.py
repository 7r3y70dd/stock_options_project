"""Portfolio summary component for displaying portfolio metrics.

Provides a reusable component for displaying portfolio summary data
with proper formatting and state management.
"""

import logging
from typing import Any, Dict, Optional
from app.frontend.formatters import (
    format_currency,
    format_percentage,
    format_number,
)
from app.frontend.app_shell import LoadingState

logger = logging.getLogger(__name__)


class PortfolioSummaryComponent:
    """Component for displaying portfolio summary."""
    
    def __init__(self):
        """Initialize portfolio summary component."""
        self.loading_state = LoadingState.IDLE
        self.error_message: Optional[str] = None
        self.data: Dict[str, Any] = {}
    
    def set_data(self, data: Dict[str, Any]) -> None:
        """Set portfolio data.
        
        Args:
            data: Portfolio data dictionary
        """
        self.data = data
        self.loading_state = LoadingState.SUCCESS
        self.error_message = None
    
    def set_loading(self) -> None:
        """Set component to loading state."""
        self.loading_state = LoadingState.LOADING
        self.error_message = None
    
    def set_error(self, message: str) -> None:
        """Set component to error state.
        
        Args:
            message: Error message
        """
        self.loading_state = LoadingState.ERROR
        self.error_message = message
    
    def render(self) -> str:
        """Render portfolio summary component.
        
        Returns:
            Formatted portfolio summary string
        """
        if self.loading_state == LoadingState.LOADING:
            return self._render_loading()
        elif self.loading_state == LoadingState.ERROR:
            return self._render_error()
        elif not self.data:
            return self._render_empty()
        else:
            return self._render_success()
    
    def _render_loading(self) -> str:
        """Render loading state.
        
        Returns:
            Loading state string
        """
        return """
┌─ Portfolio Summary ──────────────────────────────────────────────┐
│                                                                  │
│                    ⟳ Loading portfolio...                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
    
    def _render_error(self) -> str:
        """Render error state.
        
        Returns:
            Error state string
        """
        return f"""
┌─ Portfolio Summary ──────────────────────────────────────────────┐
│                                                                  │
│  ✗ Error: {self.error_message[:50].ljust(50)}  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
    
    def _render_empty(self) -> str:
        """Render empty state.
        
        Returns:
            Empty state string
        """
        return """
┌─ Portfolio Summary ──────────────────────────────────────────────┐
│                                                                  │
│  ○ No portfolio data available                                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
    
    def _render_success(self) -> str:
        """Render success state with data.
        
        Returns:
            Formatted portfolio summary string
        """
        total_value = format_currency(self.data.get('total_value'))
        cash = format_currency(self.data.get('cash'))
        positions_value = format_currency(self.data.get('positions_value'))
        open_pl = format_currency(self.data.get('open_pl'))
        open_pl_pct = format_percentage(self.data.get('open_pl_pct'))
        num_trades = self.data.get('num_open_trades', 0)
        num_signals = self.data.get('num_open_signals', 0)
        
        return f"""
┌─ Portfolio Summary ──────────────────────────────────────────────┐
│                                                                  │
│  Total Value:        {total_value:>30}  │
│  Cash:               {cash:>30}  │
│  Positions Value:    {positions_value:>30}  │
│                                                                  │
│  Open P/L:           {open_pl:>30}  │
│  Open P/L %:         {open_pl_pct:>30}  │
│                                                                  │
│  Open Trades:        {str(num_trades):>30}  │
│  Open Signals:       {str(num_signals):>30}  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
