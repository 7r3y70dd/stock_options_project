"""Reusable API client for backend communication."""
import os
from typing import Any, Dict, Optional


class APIError(Exception):
    """Raised when an API request fails."""

    def __init__(self, status_code: int, message: str, details: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(f"API Error {status_code}: {message}")


class APIClient:
    """Centralized API client for all backend communication."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        dashboard_prefix: Optional[str] = None,
        demo_user_id: Optional[str] = None,
    ):
        """Initialize API client with configurable endpoints.

        Args:
            base_url: Backend base URL (defaults to env var FRONTEND_API_BASE_URL or http://localhost:8000)
            dashboard_prefix: Dashboard route prefix (defaults to env var FRONTEND_DASHBOARD_PREFIX or /api/api/dashboard)
            demo_user_id: Demo user ID for local development (defaults to env var DEMO_USER_ID or "1")
        """
        self.base_url = base_url or os.getenv("FRONTEND_API_BASE_URL", "http://localhost:8000")
        self.dashboard_prefix = dashboard_prefix or os.getenv(
            "FRONTEND_DASHBOARD_PREFIX", "/api/api/dashboard"
        )
        self.demo_user_id = demo_user_id or os.getenv("DEMO_USER_ID", "1")

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the backend.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON request body

        Returns:
            Response JSON data

        Raises:
            APIError: If the request fails
        """
        import aiohttp

        url = f"{self.base_url}{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, url, params=params, json=json_data
                ) as response:
                    data = await response.json()
                    if response.status >= 400:
                        raise APIError(
                            response.status,
                            data.get("detail", "Unknown error"),
                            data,
                        )
                    return data
        except aiohttp.ClientError as e:
            raise APIError(0, f"Network error: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """Check backend health.

        Returns:
            Health status response
        """
        return await self._request("GET", "/api/health")

    async def get_dashboard(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get complete dashboard data.

        Args:
            user_id: User ID (defaults to demo_user_id)

        Returns:
            Dashboard data
        """
        user_id = user_id or self.demo_user_id
        return await self._request(
            "GET", f"{self.dashboard_prefix}/", params={"user_id": user_id}
        )

    async def get_portfolio(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get portfolio summary.

        Args:
            user_id: User ID (defaults to demo_user_id)

        Returns:
            Portfolio data
        """
        user_id = user_id or self.demo_user_id
        return await self._request(
            "GET", f"{self.dashboard_prefix}/portfolio", params={"user_id": user_id}
        )

    async def get_watchlist(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get user watchlist.

        Args:
            user_id: User ID (defaults to demo_user_id)

        Returns:
            Watchlist data
        """
        user_id = user_id or self.demo_user_id
        return await self._request(
            "GET", f"{self.dashboard_prefix}/watchlist", params={"user_id": user_id}
        )

    async def get_opportunities(
        self, user_id: Optional[str] = None, limit: int = 10
    ) -> Dict[str, Any]:
        """Get top trading opportunities.

        Args:
            user_id: User ID (defaults to demo_user_id)
            limit: Maximum number of opportunities to return

        Returns:
            Opportunities data
        """
        user_id = user_id or self.demo_user_id
        return await self._request(
            "GET",
            f"{self.dashboard_prefix}/opportunities",
            params={"user_id": user_id, "limit": limit},
        )

    async def get_risk_settings(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get risk settings.

        Args:
            user_id: User ID (defaults to demo_user_id)

        Returns:
            Risk settings data
        """
        user_id = user_id or self.demo_user_id
        return await self._request(
            "GET", f"{self.dashboard_prefix}/risk-settings", params={"user_id": user_id}
        )

    async def add_watchlist_symbol(
        self, symbol: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add symbol to watchlist.

        Args:
            symbol: Stock symbol
            user_id: User ID (defaults to demo_user_id)

        Returns:
            Response data
        """
        user_id = user_id or self.demo_user_id
        return await self._request(
            "POST",
            f"{self.dashboard_prefix}/watchlist/add",
            params={"user_id": user_id, "symbol": symbol},
        )

    async def remove_watchlist_symbol(
        self, symbol: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Remove symbol from watchlist.

        Args:
            symbol: Stock symbol
            user_id: User ID (defaults to demo_user_id)

        Returns:
            Response data
        """
        user_id = user_id or self.demo_user_id
        return await self._request(
            "POST",
            f"{self.dashboard_prefix}/watchlist/remove",
            params={"user_id": user_id, "symbol": symbol},
        )

    async def validate_symbol(self, symbol: str) -> Dict[str, Any]:
        """Validate a stock symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Validation result
        """
        return await self._request(
            "POST",
            f"{self.dashboard_prefix}/watchlist/validate",
            params={"symbol": symbol},
        )

    async def update_risk_settings(
        self,
        risk_level: str,
        confirmed: bool = False,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update risk settings.

        Args:
            risk_level: Risk level (low, medium, high)
            confirmed: Whether user confirmed the change
            user_id: User ID (defaults to demo_user_id)

        Returns:
            Response data
        """
        user_id = user_id or self.demo_user_id
        return await self._request(
            "POST",
            f"{self.dashboard_prefix}/risk-settings/update",
            params={
                "user_id": user_id,
                "risk_level": risk_level,
                "confirmed": confirmed,
            },
        )
