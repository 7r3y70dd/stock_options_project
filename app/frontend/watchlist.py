"""Watchlist component for managing watched symbols.

Provides a component for displaying, adding, and removing symbols
from the user's watchlist.
"""

import logging
from typing import Any, Dict, List, Optional
from app.frontend.formatters import format_currency, format_date
from app.frontend.app_shell import LoadingState

logger = logging.getLogger(__name__)


class WatchlistComponent:
    """Component for managing watchlist."""
    
    def __init__(self):
        """Initialize watchlist component."""
        self.loading_state = LoadingState.IDLE
        self.error_message: Optional[str] = None
        self.symbols: List[Dict[str, Any]] = []
        self.validation_error: Optional[str] = None
        self.add_in_progress = False
    
    def set_symbols(self, symbols: List[Dict[str, Any]]) -> None:
        """Set watchlist symbols.
        
        Args:
            symbols: List of symbol data dictionaries
        """
        self.symbols = symbols
        self.loading_state = LoadingState.SUCCESS if symbols else LoadingState.EMPTY
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
    
    def set_validation_error(self, message: str) -> None:
        """Set validation error.
        
        Args:
            message: Validation error message
        """
        self.validation_error = message
    
    def clear_validation_error(self) -> None:
        """Clear validation error."""
        self.validation_error = None
    
    def render(self) -> str:
        """Render watchlist component.
        
        Returns:
            Formatted watchlist string
        """
        if self.loading_state == LoadingState.LOADING:
            return self._render_loading()
        elif self.loading_state == LoadingState.ERROR:
            return self._render_error()
        elif self.loading_state == LoadingState.EMPTY:
            return self._render_empty()
        else:
            return self._render_success()
    
    def _render_loading(self) -> str:
        """Render loading state.
        
        Returns:
            Loading state string
        """
        return """
┌─ Watchlist ──────────────────────────────────────────────────────┐
│                                                                  │
│                    ⟳ Loading watchlist...                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
    
    def _render_error(self) -> str:
        """Render error state.
        
        Returns:
            Error state string
        """
        return f"""
┌─ Watchlist ──────────────────────────────────────────────────────┐
│                                                                  │
│  ✗ Error: {self.error_message[:50].ljust(50)}  │
│                                                                  │
│  [Retry]                                                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
    
    def _render_empty(self) -> str:
        """Render empty state.
        
        Returns:
            Empty state string
        """
        return """
┌─ Watchlist ──────────────────────────────────────────────────────┐
│                                                                  │
│  ○ No symbols in watchlist                                       │
│                                                                  │
│  Add Symbol: [________]  [Validate]  [Add]                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
    
    def _render_success(self) -> str:
        """Render success state with symbols.
        
        Returns:
            Formatted watchlist string
        """
        lines = ["┌─ Watchlist ──────────────────────────────────────────────────────┐"]
        lines.append("│                                                                  │")
        lines.append(f"│  Symbols: {len(self.symbols):2}                                                    │")
        lines.append("│                                                                  │")
        
        for symbol_data in self.symbols[:10]:  # Show top 10
            symbol = symbol_data.get('symbol', 'UNKNOWN')
            price = format_currency(symbol_data.get('current_price'))
            added_at = format_date(symbol_data.get('added_at'), "%Y-%m-%d")
            freshness = symbol_data.get('data_freshness_seconds')
            freshness_str = f"{freshness}s ago" if freshness else "N/A"
            
            lines.append(f"│  {symbol:6} | Price: {price:12} | Added: {added_at} | {freshness_str:10} │")
        
        lines.append("│                                                                  │")
        
        if self.validation_error:
            lines.append(f"│  ✗ {self.validation_error[:56].ljust(56)}  │")
            lines.append("│                                                                  │")
        
        lines.append("│  Add Symbol: [________]  [Validate]  [Add]                       │")
        lines.append("│                                                                  │")
        lines.append("└──────────────────────────────────────────────────────────────────┘")
        
        return "\n".join(lines)
