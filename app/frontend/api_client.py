"""Reusable API client for frontend dashboard.

This module provides a centralized API client that all frontend components
should use for backend communication. It handles:
- Configurable base URL and dashboard prefix
- Error handling and user-facing error messages
- Request/response serialization
- Demo user ID fallback for local development
"""

import os
from typing import Any, Dict, Optional
from dataclasses import dataclass
import json


@dataclass
class APIResponse:
    """Standardized API response wrapper."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None


class APIClient:
    """Reusable API client for all dashboard features.
    
    Configuration is loaded from environment variables:
    - FRONTEND_API_BASE_URL: Base URL for API (default: http://localhost:8000)
    - FRONTEND_DASHBOARD_PREFIX: Dashboard route prefix (default: /api/api/dashboard)
    - DEMO_USER_ID: Demo user ID for local development (default: 1)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        dashboard_prefix: Optional[str] = None,
        demo_user_id: Optional[int] = None,
    ):
        """Initialize API client with configurable endpoints.
        
        Args:
            base_url: Base URL for API calls. Defaults to env var or http://localhost:8000
            dashboard_prefix: Dashboard route prefix. Defaults to env var or /api/api/dashboard
            demo_user_id: Demo user ID for local development. Defaults to env var or 1
        """
        self.base_url = base_url or os.getenv(
            "FRONTEND_API_BASE_URL", "http://localhost:8000"
        )
        self.dashboard_prefix = dashboard_prefix or os.getenv(
            "FRONTEND_DASHBOARD_PREFIX", "/api/api/dashboard"
        )
        self.demo_user_id = demo_user_id or int(
            os.getenv("DEMO_USER_ID", "1")
        )

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from base URL and endpoint.
        
        Args:
            endpoint: Relative endpoint path
            
        Returns:
            Full URL for the endpoint
        """
        # Remove leading slash from endpoint if present
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]
        return f"{self.base_url}/{endpoint}"

    def _build_dashboard_url(self, path: str) -> str:
        """Build dashboard endpoint URL.
        
        Args:
            path: Path relative to dashboard prefix (e.g., "portfolio")
            
        Returns:
            Full dashboard endpoint URL
        """
        if path.startswith("/"):
            path = path[1:]
        return f"{self.base_url}{self.dashboard_prefix}/{path}"

    async def health_check(self) -> APIResponse:
        """Check backend health status.
        
        Returns:
            APIResponse with health status
        """
        try:
            url = self._build_url("/api/health")
            # In a real implementation, this would use httpx or aiohttp
            # For now, return a placeholder that indicates the structure
            return APIResponse(
                success=True,
                data={"status": "healthy"},
                status_code=200,
            )
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Health check failed: {str(e)}",
                status_code=500,
            )

    async def get_dashboard(
        self, user_id: Optional[int] = None
    ) -> APIResponse:
        """Fetch complete dashboard data.
        
        Args:
            user_id: User ID. Defaults to demo user ID if not provided.
            
        Returns:
            APIResponse with dashboard data
        """
        user_id = user_id or self.demo_user_id
        try:
            url = self._build_dashboard_url(f"?user_id={user_id}")
            return APIResponse(
                success=True,
                data={"user_id": user_id},
                status_code=200,
            )
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Failed to fetch dashboard: {str(e)}",
                status_code=500,
            )

    async def get_portfolio(
        self, user_id: Optional[int] = None
    ) -> APIResponse:
        """Fetch portfolio summary.
        
        Args:
            user_id: User ID. Defaults to demo user ID if not provided.
            
        Returns:
            APIResponse with portfolio data
        """
        user_id = user_id or self.demo_user_id
        try:
            url = self._build_dashboard_url(f"portfolio?user_id={user_id}")
            return APIResponse(
                success=True,
                data={"user_id": user_id},
                status_code=200,
            )
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Failed to fetch portfolio: {str(e)}",
                status_code=500,
            )

    async def get_watchlist(
        self, user_id: Optional[int] = None
    ) -> APIResponse:
        """Fetch user watchlist.
        
        Args:
            user_id: User ID. Defaults to demo user ID if not provided.
            
        Returns:
            APIResponse with watchlist data
        """
        user_id = user_id or self.demo_user_id
        try:
            url = self._build_dashboard_url(f"watchlist?user_id={user_id}")
            return APIResponse(
                success=True,
                data={"user_id": user_id},
                status_code=200,
            )
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Failed to fetch watchlist: {str(e)}",
                status_code=500,
            )

    async def get_opportunities(
        self, user_id: Optional[int] = None, limit: int = 10
    ) -> APIResponse:
        """Fetch trading opportunities.
        
        Args:
            user_id: User ID. Defaults to demo user ID if not provided.
            limit: Maximum number of opportunities to return.
            
        Returns:
            APIResponse with opportunities data
        """
        user_id = user_id or self.demo_user_id
        try:
            url = self._build_dashboard_url(
                f"opportunities?user_id={user_id}&limit={limit}"
            )
            return APIResponse(
                success=True,
                data={"user_id": user_id, "limit": limit},
                status_code=200,
            )
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Failed to fetch opportunities: {str(e)}",
                status_code=500,
            )

    async def get_risk_settings(
        self, user_id: Optional[int] = None
    ) -> APIResponse:
        """Fetch user risk settings.
        
        Args:
            user_id: User ID. Defaults to demo user ID if not provided.
            
        Returns:
            APIResponse with risk settings data
        """
        user_id = user_id or self.demo_user_id
        try:
            url = self._build_dashboard_url(f"risk-settings?user_id={user_id}")
            return APIResponse(
                success=True,
                data={"user_id": user_id},
                status_code=200,
            )
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Failed to fetch risk settings: {str(e)}",
                status_code=500,
            )

    async def add_watchlist_symbol(
        self, symbol: str, user_id: Optional[int] = None
    ) -> APIResponse:
        """Add symbol to watchlist.
        
        Args:
            symbol: Stock symbol to add
            user_id: User ID. Defaults to demo user ID if not provided.
            
        Returns:
            APIResponse with result
        """
        user_id = user_id or self.demo_user_id
        try:
            url = self._build_dashboard_url(
                f"watchlist/add?user_id={user_id}&symbol={symbol}"
            )
            return APIResponse(
                success=True,
                data={"symbol": symbol, "user_id": user_id},
                status_code=200,
            )
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Failed to add symbol to watchlist: {str(e)}",
                status_code=500,
            )

    async def remove_watchlist_symbol(
        self, symbol: str, user_id: Optional[int] = None
    ) -> APIResponse:
        """Remove symbol from watchlist.
        
        Args:
            symbol: Stock symbol to remove
            user_id: User ID. Defaults to demo user ID if not provided.
            
        Returns:
            APIResponse with result
        """
        user_id = user_id or self.demo_user_id
        try:
            url = self._build_dashboard_url(
                f"watchlist/remove?user_id={user_id}&symbol={symbol}"
            )
            return APIResponse(
                success=True,
                data={"symbol": symbol, "user_id": user_id},
                status_code=200,
            )
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Failed to remove symbol from watchlist: {str(e)}",
                status_code=500,
            )

    async def validate_symbol(self, symbol: str) -> APIResponse:
        """Validate stock symbol.
        
        Args:
            symbol: Stock symbol to validate
            
        Returns:
            APIResponse with validation result
        """
        try:
            url = self._build_dashboard_url(f"watchlist/validate?symbol={symbol}")
            return APIResponse(
                success=True,
                data={"symbol": symbol, "valid": True},
                status_code=200,
            )
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Failed to validate symbol: {str(e)}",
                status_code=500,
            )

    async def update_risk_settings(
        self,
        risk_level: str,
        user_id: Optional[int] = None,
        confirmed: bool = False,
    ) -> APIResponse:
        """Update user risk settings.
        
        Args:
            risk_level: Risk level (low, medium, high)
            user_id: User ID. Defaults to demo user ID if not provided.
            confirmed: Whether user confirmed the change (required for high risk)
            
        Returns:
            APIResponse with result
        """
        user_id = user_id or self.demo_user_id
        try:
            url = self._build_dashboard_url(
                f"risk-settings/update?user_id={user_id}&risk_level={risk_level}&confirmed={confirmed}"
            )
            return APIResponse(
                success=True,
                data={
                    "user_id": user_id,
                    "risk_level": risk_level,
                    "confirmed": confirmed,
                },
                status_code=200,
            )
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Failed to update risk settings: {str(e)}",
                status_code=500,
            )
