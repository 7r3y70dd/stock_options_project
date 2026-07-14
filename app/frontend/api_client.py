"""Reusable API client for frontend dashboard.

Provides a centralized, configurable client for all dashboard API calls.
Handles base URL and dashboard prefix configuration to support backend changes.
"""

import logging
from typing import Optional, Dict, Any
import os

logger = logging.getLogger(__name__)


class APIClient:
    """Reusable API client for dashboard endpoints.
    
    Centralizes all API calls with configurable base URL and dashboard prefix.
    Supports environment variable configuration for easy backend URL changes.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        dashboard_prefix: Optional[str] = None,
    ):
        """Initialize API client with configurable endpoints.
        
        Args:
            base_url: Base URL for API (e.g., 'http://localhost:8000/api')
                     Defaults to env var API_BASE_URL or 'http://localhost:8000/api'
            dashboard_prefix: Prefix for dashboard routes (e.g., '/api/dashboard')
                             Defaults to env var DASHBOARD_PREFIX or '/api/dashboard'
        """
        self.base_url = base_url or os.getenv(
            "API_BASE_URL", "http://localhost:8000/api"
        )
        self.dashboard_prefix = dashboard_prefix or os.getenv(
            "DASHBOARD_PREFIX", "/api/dashboard"
        )
        
        # Remove trailing slashes for consistent URL building
        self.base_url = self.base_url.rstrip("/")
        self.dashboard_prefix = self.dashboard_prefix.rstrip("/")

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint path.
        
        Args:
            endpoint: Endpoint path (e.g., '/' or '/watchlist')
            
        Returns:
            Full URL for the endpoint
        """
        return f"{self.base_url}{self.dashboard_prefix}{endpoint}"

    async def health_check(self) -> Dict[str, Any]:
        """Check API health status.
        
        Returns:
            Health check response
            
        Raises:
            APIError: If request fails
        """
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/health"
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise APIError(f"Health check failed: {str(e)}")

    async def get_dashboard(
        self, user_id: int, watchlist_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get complete dashboard data for user.
        
        Args:
            user_id: User ID
            watchlist_id: Optional specific watchlist ID
            
        Returns:
            Dashboard data with all sections
            
        Raises:
            APIError: If request fails
        """
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                url = self._build_url("/")
                params = {"user_id": user_id}
                if watchlist_id is not None:
                    params["watchlist_id"] = watchlist_id
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            raise APIError(f"Failed to get dashboard data: {str(e)}")

    async def get_portfolio(
        self, user_id: int
    ) -> Dict[str, Any]:
        """Get portfolio summary for user.
        
        Args:
            user_id: User ID
            
        Returns:
            Portfolio summary data
            
        Raises:
            APIError: If request fails
        """
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                url = self._build_url("/portfolio")
                response = await client.get(
                    url, params={"user_id": user_id}, timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get portfolio: {e}")
            raise APIError(f"Failed to get portfolio: {str(e)}")

    async def get_watchlist(
        self, user_id: int, watchlist_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get watchlist for user with current prices.
        
        Args:
            user_id: User ID
            watchlist_id: Optional specific watchlist ID
            
        Returns:
            Watchlist with symbols and prices
            
        Raises:
            APIError: If request fails
        """
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                url = self._build_url("/watchlist")
                params = {"user_id": user_id}
                if watchlist_id is not None:
                    params["watchlist_id"] = watchlist_id
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get watchlist: {e}")
            raise APIError(f"Failed to get watchlist: {str(e)}")

    async def add_watchlist_symbol(
        self, user_id: int, symbol: str, watchlist_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add a symbol to user's watchlist.
        
        Args:
            user_id: User ID
            symbol: Stock symbol to add
            watchlist_id: Optional specific watchlist ID
            
        Returns:
            Updated watchlist
            
        Raises:
            APIError: If request fails
        """
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                url = self._build_url("/watchlist/add")
                params = {"user_id": user_id, "symbol": symbol}
                if watchlist_id is not None:
                    params["watchlist_id"] = watchlist_id
                response = await client.post(url, params=params, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to add watchlist symbol: {e}")
            raise APIError(f"Failed to add watchlist symbol: {str(e)}")

    async def remove_watchlist_symbol(
        self, user_id: int, symbol: str, watchlist_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Remove a symbol from user's watchlist.
        
        Args:
            user_id: User ID
            symbol: Stock symbol to remove
            watchlist_id: Optional specific watchlist ID
            
        Returns:
            Updated watchlist
            
        Raises:
            APIError: If request fails
        """
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                url = self._build_url("/watchlist/remove")
                params = {"user_id": user_id, "symbol": symbol}
                if watchlist_id is not None:
                    params["watchlist_id"] = watchlist_id
                response = await client.post(url, params=params, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to remove watchlist symbol: {e}")
            raise APIError(f"Failed to remove watchlist symbol: {str(e)}")

    async def validate_symbol(self, symbol: str) -> Dict[str, Any]:
        """Validate a stock symbol.
        
        Args:
            symbol: Stock symbol to validate
            
        Returns:
            Validation result
            
        Raises:
            APIError: If request fails
        """
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                url = self._build_url("/watchlist/validate")
                response = await client.post(
                    url, params={"symbol": symbol}, timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to validate symbol: {e}")
            raise APIError(f"Failed to validate symbol: {str(e)}")

    async def get_opportunities(
        self, user_id: int, limit: int = 10
    ) -> Dict[str, Any]:
        """Get top opportunities for user.
        
        Args:
            user_id: User ID
            limit: Maximum number of opportunities to return
            
        Returns:
            List of top opportunities
            
        Raises:
            APIError: If request fails
        """
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                url = self._build_url("/opportunities")
                response = await client.get(
                    url, params={"user_id": user_id, "limit": limit}, timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get opportunities: {e}")
            raise APIError(f"Failed to get opportunities: {str(e)}")

    async def get_risk_settings(self, user_id: int) -> Dict[str, Any]:
        """Get risk settings for user.
        
        Args:
            user_id: User ID
            
        Returns:
            Risk settings
            
        Raises:
            APIError: If request fails
        """
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                url = self._build_url("/risk-settings")
                response = await client.get(
                    url, params={"user_id": user_id}, timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get risk settings: {e}")
            raise APIError(f"Failed to get risk settings: {str(e)}")

    async def update_risk_settings(
        self,
        user_id: int,
        risk_level: str,
        confirmed: bool = False,
    ) -> Dict[str, Any]:
        """Update risk settings for user.
        
        Args:
            user_id: User ID
            risk_level: Risk level (low, medium, high)
            confirmed: Whether user confirmed the change
            
        Returns:
            Updated risk settings
            
        Raises:
            APIError: If request fails
        """
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                url = self._build_url("/risk-settings/update")
                params = {
                    "user_id": user_id,
                    "risk_level": risk_level,
                    "confirmed": confirmed,
                }
                response = await client.post(url, params=params, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to update risk settings: {e}")
            raise APIError(f"Failed to update risk settings: {str(e)}")


class APIError(Exception):
    """Exception raised for API client errors."""

    pass


# Global API client instance
_api_client: Optional[APIClient] = None


def get_api_client(
    base_url: Optional[str] = None,
    dashboard_prefix: Optional[str] = None,
) -> APIClient:
    """Get or create global API client instance.
    
    Args:
        base_url: Optional base URL override
        dashboard_prefix: Optional dashboard prefix override
        
    Returns:
        APIClient instance
    """
    global _api_client
    if _api_client is None:
        _api_client = APIClient(base_url=base_url, dashboard_prefix=dashboard_prefix)
    return _api_client
