"""Dashboard frontend module."""
from typing import Any, Dict, Optional

from app.frontend.api_client import APIClient
from app.frontend.shared_states import UIState


class Dashboard:
    """Dashboard service for frontend."""

    def __init__(self, api_client: Optional[APIClient] = None):
        """Initialize dashboard.

        Args:
            api_client: API client instance (creates default if not provided)
        """
        self.api_client = api_client or APIClient()
        self.ui_state = UIState()

    async def load_dashboard(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Load complete dashboard data.

        Args:
            user_id: User ID (optional)

        Returns:
            Dashboard data
        """
        self.ui_state.reset()
        self.ui_state.loading.start("Loading dashboard...")
        try:
            data = await self.api_client.get_dashboard(user_id)
            return data
        except Exception as e:
            self.ui_state.error.set_error(
                str(e),
                getattr(e, "status_code", None),
                getattr(e, "details", None),
            )
            raise
        finally:
            self.ui_state.loading.stop()

    async def load_portfolio(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Load portfolio summary.

        Args:
            user_id: User ID (optional)

        Returns:
            Portfolio data
        """
        self.ui_state.reset()
        self.ui_state.loading.start("Loading portfolio...")
        try:
            data = await self.api_client.get_portfolio(user_id)
            return data
        except Exception as e:
            self.ui_state.error.set_error(
                str(e),
                getattr(e, "status_code", None),
                getattr(e, "details", None),
            )
            raise
        finally:
            self.ui_state.loading.stop()

    async def load_watchlist(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Load watchlist.

        Args:
            user_id: User ID (optional)

        Returns:
            Watchlist data
        """
        self.ui_state.reset()
        self.ui_state.loading.start("Loading watchlist...")
        try:
            data = await self.api_client.get_watchlist(user_id)
            return data
        except Exception as e:
            self.ui_state.error.set_error(
                str(e),
                getattr(e, "status_code", None),
                getattr(e, "details", None),
            )
            raise
        finally:
            self.ui_state.loading.stop()

    async def load_opportunities(
        self, user_id: Optional[str] = None, limit: int = 10
    ) -> Dict[str, Any]:
        """Load trading opportunities.

        Args:
            user_id: User ID (optional)
            limit: Maximum number of opportunities

        Returns:
            Opportunities data
        """
        self.ui_state.reset()
        self.ui_state.loading.start("Loading opportunities...")
        try:
            data = await self.api_client.get_opportunities(user_id, limit)
            return data
        except Exception as e:
            self.ui_state.error.set_error(
                str(e),
                getattr(e, "status_code", None),
                getattr(e, "details", None),
            )
            raise
        finally:
            self.ui_state.loading.stop()

    async def load_risk_settings(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Load risk settings.

        Args:
            user_id: User ID (optional)

        Returns:
            Risk settings data
        """
        self.ui_state.reset()
        self.ui_state.loading.start("Loading risk settings...")
        try:
            data = await self.api_client.get_risk_settings(user_id)
            return data
        except Exception as e:
            self.ui_state.error.set_error(
                str(e),
                getattr(e, "status_code", None),
                getattr(e, "details", None),
            )
            raise
        finally:
            self.ui_state.loading.stop()

    async def add_symbol(self, symbol: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Add symbol to watchlist.

        Args:
            symbol: Stock symbol
            user_id: User ID (optional)

        Returns:
            Response data
        """
        self.ui_state.reset()
        self.ui_state.loading.start(f"Adding {symbol}...")
        try:
            data = await self.api_client.add_watchlist_symbol(symbol, user_id)
            return data
        except Exception as e:
            self.ui_state.error.set_error(
                str(e),
                getattr(e, "status_code", None),
                getattr(e, "details", None),
            )
            raise
        finally:
            self.ui_state.loading.stop()

    async def remove_symbol(self, symbol: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Remove symbol from watchlist.

        Args:
            symbol: Stock symbol
            user_id: User ID (optional)

        Returns:
            Response data
        """
        self.ui_state.reset()
        self.ui_state.loading.start(f"Removing {symbol}...")
        try:
            data = await self.api_client.remove_watchlist_symbol(symbol, user_id)
            return data
        except Exception as e:
            self.ui_state.error.set_error(
                str(e),
                getattr(e, "status_code", None),
                getattr(e, "details", None),
            )
            raise
        finally:
            self.ui_state.loading.stop()

    async def validate_symbol(self, symbol: str) -> Dict[str, Any]:
        """Validate a stock symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Validation result
        """
        try:
            data = await self.api_client.validate_symbol(symbol)
            return data
        except Exception as e:
            self.ui_state.error.set_error(
                str(e),
                getattr(e, "status_code", None),
                getattr(e, "details", None),
            )
            raise

    async def update_risk_level(
        self,
        risk_level: str,
        confirmed: bool = False,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update risk level.

        Args:
            risk_level: Risk level (low, medium, high)
            confirmed: Whether user confirmed the change
            user_id: User ID (optional)

        Returns:
            Response data
        """
        self.ui_state.reset()
        self.ui_state.loading.start(f"Updating risk level to {risk_level}...")
        try:
            data = await self.api_client.update_risk_settings(risk_level, confirmed, user_id)
            return data
        except Exception as e:
            self.ui_state.error.set_error(
                str(e),
                getattr(e, "status_code", None),
                getattr(e, "details", None),
            )
            raise
        finally:
            self.ui_state.loading.stop()
