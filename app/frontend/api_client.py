"""API client for backend communication.

Provides a centralized interface for all backend API calls with error handling,
loading states, and configurable base URL.
"""

import logging
from typing import Any, Dict, List, Optional
import os

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Custom exception for API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class APIClient:
    """Client for backend API communication.
    
    Centralizes all API calls and provides error handling, loading states,
    and configurable base URL.
    """
    
    def __init__(self, base_url: str = None, dashboard_prefix: str = None):
        """Initialize API client.
        
        Args:
            base_url: Base URL for API (defaults to env var or localhost)
            dashboard_prefix: Prefix for dashboard routes (defaults to /api/api/dashboard)
        """
        self.base_url = base_url or os.getenv('API_BASE_URL', 'http://localhost:8000')
        self.dashboard_prefix = dashboard_prefix or os.getenv('DASHBOARD_PREFIX', '/api/api/dashboard')
        self.demo_user_id = int(os.getenv('DEMO_USER_ID', '1'))
    
    def _make_request(self, method: str, endpoint: str, params: Dict[str, Any] = None, 
                     json_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make HTTP request to backend.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON request body
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            APIError: If request fails
        """
        try:
            import requests
            
            url = f"{self.base_url}{endpoint}"
            headers = {'Content-Type': 'application/json'}
            
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('detail', response.text)
                except:
                    error_msg = response.text
                
                raise APIError(
                    f"API request failed: {error_msg}",
                    status_code=response.status_code,
                    response=error_data if 'error_data' in locals() else None
                )
            
            return response.json()
        except APIError:
            raise
        except Exception as e:
            logger.error(f"API request error: {e}", exc_info=True)
            raise APIError(f"API request failed: {str(e)}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health.
        
        Returns:
            Health status response
        """
        return self._make_request('GET', '/api/health')
    
    def get_dashboard(self, user_id: int = None) -> Dict[str, Any]:
        """Get full dashboard data.
        
        Args:
            user_id: User ID (defaults to demo user)
            
        Returns:
            Dashboard data including portfolio, watchlist, opportunities, etc.
        """
        user_id = user_id or self.demo_user_id
        return self._make_request(
            'GET',
            f"{self.dashboard_prefix}/",
            params={'user_id': user_id}
        )
    
    def get_portfolio(self, user_id: int = None) -> Dict[str, Any]:
        """Get portfolio summary.
        
        Args:
            user_id: User ID (defaults to demo user)
            
        Returns:
            Portfolio summary data
        """
        user_id = user_id or self.demo_user_id
        return self._make_request(
            'GET',
            f"{self.dashboard_prefix}/portfolio",
            params={'user_id': user_id}
        )
    
    def get_watchlist(self, user_id: int = None) -> Dict[str, Any]:
        """Get watchlist.
        
        Args:
            user_id: User ID (defaults to demo user)
            
        Returns:
            Watchlist data with symbols and prices
        """
        user_id = user_id or self.demo_user_id
        return self._make_request(
            'GET',
            f"{self.dashboard_prefix}/watchlist",
            params={'user_id': user_id}
        )
    
    def get_opportunities(self, user_id: int = None, limit: int = 10) -> Dict[str, Any]:
        """Get trading opportunities.
        
        Args:
            user_id: User ID (defaults to demo user)
            limit: Maximum number of opportunities to return
            
        Returns:
            Opportunities data
        """
        user_id = user_id or self.demo_user_id
        return self._make_request(
            'GET',
            f"{self.dashboard_prefix}/opportunities",
            params={'user_id': user_id, 'limit': limit}
        )
    
    def get_opportunity_detail(self, signal_id: str, user_id: int = None) -> Dict[str, Any]:
        """Get detailed opportunity data.
        
        Args:
            signal_id: Signal ID
            user_id: User ID (defaults to demo user)
            
        Returns:
            Detailed opportunity data
        """
        user_id = user_id or self.demo_user_id
        return self._make_request(
            'GET',
            f"{self.dashboard_prefix}/opportunities/{signal_id}",
            params={'user_id': user_id}
        )
    
    def get_trades(self, user_id: int = None) -> Dict[str, Any]:
        """Get open trades.
        
        Args:
            user_id: User ID (defaults to demo user)
            
        Returns:
            Trades data
        """
        user_id = user_id or self.demo_user_id
        return self._make_request(
            'GET',
            f"{self.dashboard_prefix}/trades",
            params={'user_id': user_id}
        )
    
    def get_news(self, user_id: int = None, limit: int = 20) -> Dict[str, Any]:
        """Get recent news.
        
        Args:
            user_id: User ID (defaults to demo user)
            limit: Maximum number of news items
            
        Returns:
            News data
        """
        user_id = user_id or self.demo_user_id
        return self._make_request(
            'GET',
            f"{self.dashboard_prefix}/news",
            params={'user_id': user_id, 'limit': limit}
        )
    
    def get_risk_settings(self, user_id: int = None) -> Dict[str, Any]:
        """Get risk settings.
        
        Args:
            user_id: User ID (defaults to demo user)
            
        Returns:
            Risk settings data
        """
        user_id = user_id or self.demo_user_id
        return self._make_request(
            'GET',
            f"{self.dashboard_prefix}/risk-settings",
            params={'user_id': user_id}
        )
    
    def validate_symbol(self, symbol: str) -> Dict[str, Any]:
        """Validate a stock symbol.
        
        Args:
            symbol: Stock symbol to validate
            
        Returns:
            Validation result
        """
        return self._make_request(
            'POST',
            f"{self.dashboard_prefix}/watchlist/validate",
            params={'symbol': symbol}
        )
    
    def add_watchlist_symbol(self, symbol: str, user_id: int = None) -> Dict[str, Any]:
        """Add symbol to watchlist.
        
        Args:
            symbol: Stock symbol to add
            user_id: User ID (defaults to demo user)
            
        Returns:
            Add result
        """
        user_id = user_id or self.demo_user_id
        return self._make_request(
            'POST',
            f"{self.dashboard_prefix}/watchlist/add",
            params={'user_id': user_id, 'symbol': symbol}
        )
    
    def remove_watchlist_symbol(self, symbol: str, user_id: int = None) -> Dict[str, Any]:
        """Remove symbol from watchlist.
        
        Args:
            symbol: Stock symbol to remove
            user_id: User ID (defaults to demo user)
            
        Returns:
            Remove result
        """
        user_id = user_id or self.demo_user_id
        return self._make_request(
            'POST',
            f"{self.dashboard_prefix}/watchlist/remove",
            params={'user_id': user_id, 'symbol': symbol}
        )
    
    def update_risk_settings(self, risk_level: str, confirmed: bool = False, 
                            user_id: int = None) -> Dict[str, Any]:
        """Update risk settings.
        
        Args:
            risk_level: Risk level (low, medium, high)
            confirmed: Whether user confirmed the change
            user_id: User ID (defaults to demo user)
            
        Returns:
            Update result
        """
        user_id = user_id or self.demo_user_id
        return self._make_request(
            'POST',
            f"{self.dashboard_prefix}/risk-settings/update",
            params={
                'user_id': user_id,
                'risk_level': risk_level,
                'confirmed': confirmed
            }
        )


_api_client_instance: Optional[APIClient] = None


def get_api_client(base_url: str = None, dashboard_prefix: str = None) -> APIClient:
    """Get or create API client singleton.
    
    Args:
        base_url: Optional base URL override
        dashboard_prefix: Optional dashboard prefix override
        
    Returns:
        APIClient instance
    """
    global _api_client_instance
    
    if base_url or dashboard_prefix:
        return APIClient(base_url=base_url, dashboard_prefix=dashboard_prefix)
    
    if _api_client_instance is None:
        _api_client_instance = APIClient()
    
    return _api_client_instance
