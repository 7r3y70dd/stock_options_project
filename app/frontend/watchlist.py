"""Watchlist UI component for managing user's watched symbols.

Provides a reusable watchlist panel with:
- Display of current watchlist symbols
- Add symbol functionality with validation
- Remove symbol functionality
- Current price display (when available)
- Data freshness indicators
- Loading and error states
"""

import logging
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WatchlistSymbolDisplay:
    """Display data for a watchlist symbol."""
    symbol: str
    current_price: Optional[float]
    added_at: str
    last_updated: Optional[str]
    data_freshness_seconds: Optional[int]


class WatchlistComponent:
    """Watchlist UI component."""

    def __init__(
        self,
        user_id: int,
        api_client: Any,  # APIClient instance
    ):
        """Initialize watchlist component.

        Args:
            user_id: User ID
            api_client: API client for backend calls
        """
        self.user_id = user_id
        self.api_client = api_client
        self.symbols: List[WatchlistSymbolDisplay] = []
        self.loading = False
        self.error: Optional[str] = None
        self.validation_error: Optional[str] = None
        self.add_input_value = ""
        self.pending_add: Optional[str] = None  # Symbol being added
        self.pending_remove: Optional[str] = None  # Symbol being removed

    async def load_watchlist(self) -> None:
        """Load watchlist from API."""
        try:
            self.loading = True
            self.error = None
            
            watchlist_data = await self.api_client.get_watchlist(self.user_id)
            
            self.symbols = [
                WatchlistSymbolDisplay(
                    symbol=item["symbol"],
                    current_price=item["current_price"],
                    added_at=item["added_at"],
                    last_updated=item["last_updated"],
                    data_freshness_seconds=item["data_freshness_seconds"],
                )
                for item in watchlist_data.get("symbols", [])
            ]
        except Exception as e:
            logger.error(f"Error loading watchlist: {e}")
            self.error = "Failed to load watchlist"
            self.symbols = []
        finally:
            self.loading = False

    async def validate_symbol(self, symbol: str) -> bool:
        """Validate a symbol before adding.

        Args:
            symbol: Symbol to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            self.validation_error = None
            
            if not symbol or not symbol.strip():
                self.validation_error = "Symbol cannot be empty"
                return False
            
            result = await self.api_client.validate_symbol(symbol)
            
            if not result.get("valid", False):
                self.validation_error = result.get("message", "Invalid symbol")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating symbol: {e}")
            self.validation_error = "Error validating symbol"
            return False

    async def add_symbol(self, symbol: str) -> bool:
        """Add a symbol to watchlist.

        Args:
            symbol: Symbol to add

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate first
            if not await self.validate_symbol(symbol):
                return False
            
            # Check for duplicates in UI
            symbol_upper = symbol.upper().strip()
            if any(s.symbol == symbol_upper for s in self.symbols):
                self.validation_error = f"Symbol {symbol_upper} already in watchlist"
                return False
            
            self.pending_add = symbol_upper
            self.error = None
            
            result = await self.api_client.add_watchlist_symbol(self.user_id, symbol_upper)
            
            if result.get("status") == "success":
                # Reload watchlist to get fresh data
                await self.load_watchlist()
                self.add_input_value = ""  # Clear input
                self.validation_error = None
                return True
            else:
                self.error = result.get("message", "Failed to add symbol")
                return False
        except Exception as e:
            logger.error(f"Error adding symbol: {e}")
            self.error = "Failed to add symbol"
            return False
        finally:
            self.pending_add = None

    async def remove_symbol(self, symbol: str) -> bool:
        """Remove a symbol from watchlist.

        Args:
            symbol: Symbol to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            self.pending_remove = symbol
            self.error = None
            
            result = await self.api_client.remove_watchlist_symbol(self.user_id, symbol)
            
            if result.get("status") == "success":
                # Reload watchlist to get fresh data
                await self.load_watchlist()
                return True
            else:
                self.error = result.get("message", "Failed to remove symbol")
                return False
        except Exception as e:
            logger.error(f"Error removing symbol: {e}")
            self.error = "Failed to remove symbol"
            return False
        finally:
            self.pending_remove = None

    def render(self) -> Dict[str, Any]:
        """Render watchlist component state.

        Returns:
            Dictionary with component state for rendering
        """
        return {
            "symbols": [
                {
                    "symbol": s.symbol,
                    "current_price": s.current_price,
                    "added_at": s.added_at,
                    "last_updated": s.last_updated,
                    "data_freshness_seconds": s.data_freshness_seconds,
                }
                for s in self.symbols
            ],
            "count": len(self.symbols),
            "loading": self.loading,
            "error": self.error,
            "validation_error": self.validation_error,
            "add_input_value": self.add_input_value,
            "pending_add": self.pending_add,
            "pending_remove": self.pending_remove,
        }
