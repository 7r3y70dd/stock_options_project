"""Frontend dashboard implementation.

Provides the main dashboard view and data aggregation for the stock options
trading platform. Integrates with the backend API via the APIClient.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.frontend.api_client import APIClient, APIResponse
from app.frontend.shared_states import LoadingState, ErrorState, EmptyState, UIStateManager


@dataclass
class PortfolioSummary:
    """Portfolio summary data."""
    total_value: float
    cash: float
    positions_value: float
    open_pl: float
    open_pl_percent: float
    buying_power: float


@dataclass
class WatchlistItem:
    """Watchlist item data."""
    symbol: str
    current_price: float
    change_percent: float
    last_updated: datetime
    data_freshness_seconds: int


@dataclass
class Opportunity:
    """Trading opportunity data."""
    symbol: str
    strategy: str
    score: float
    expected_return: float
    risk_level: str
    expiration: Optional[str]


@dataclass
class OpenTrade:
    """Open trade data."""
    id: str
    symbol: str
    strategy: str
    entry_price: float
    current_price: float
    pl: float
    pl_percent: float
    entry_date: datetime


@dataclass
class NewsItem:
    """News item data."""
    symbol: str
    headline: str
    source: str
    published_at: datetime
    sentiment: str


@dataclass
class RiskLevelInfo:
    """Information about a risk level."""
    level: str
    max_position_size: float
    allowed_strategies: List[str]
    max_loss_per_trade: float
    requires_confirmation: bool


@dataclass
class RiskSettings:
    """Risk settings data."""
    current_level: str
    risk_levels_info: List[RiskLevelInfo]


@dataclass
class DashboardData:
    """Complete dashboard data."""
    portfolio_summary: Optional[PortfolioSummary]
    watchlist: List[WatchlistItem]
    top_opportunities: List[Opportunity]
    open_trades: List[OpenTrade]
    recent_news: List[NewsItem]
    risk_settings: Optional[RiskSettings]


class Dashboard:
    """Dashboard service for aggregating and managing dashboard data.
    
    Uses APIClient to fetch data from backend and manages UI state.
    """

    def __init__(
        self,
        api_client: Optional[APIClient] = None,
        user_id: Optional[int] = None,
    ):
        """Initialize dashboard.
        
        Args:
            api_client: API client instance. Creates new one if not provided.
            user_id: User ID. Uses demo user ID if not provided.
        """
        self.api_client = api_client or APIClient()
        self.user_id = user_id or self.api_client.demo_user_id
        self.state_manager = UIStateManager()

    async def load_dashboard(self) -> APIResponse:
        """Load complete dashboard data.
        
        Returns:
            APIResponse with dashboard data
        """
        self.state_manager.set_loading()
        try:
            response = await self.api_client.get_dashboard(user_id=self.user_id)
            if response.success:
                self.state_manager.set_success(response.data)
            else:
                self.state_manager.set_error(
                    response.error or "Failed to load dashboard"
                )
            return response
        except Exception as e:
            error_msg = f"Dashboard load error: {str(e)}"
            self.state_manager.set_error(error_msg)
            return APIResponse(
                success=False,
                error=error_msg,
                status_code=500,
            )

    async def get_portfolio(self) -> APIResponse:
        """Fetch portfolio summary.
        
        Returns:
            APIResponse with portfolio data
        """
        self.state_manager.set_loading()
        try:
            response = await self.api_client.get_portfolio(user_id=self.user_id)
            if response.success:
                self.state_manager.set_success(response.data)
            else:
                self.state_manager.set_error(
                    response.error or "Failed to fetch portfolio"
                )
            return response
        except Exception as e:
            error_msg = f"Portfolio fetch error: {str(e)}"
            self.state_manager.set_error(error_msg)
            return APIResponse(
                success=False,
                error=error_msg,
                status_code=500,
            )

    async def get_watchlist(self) -> APIResponse:
        """Fetch watchlist.
        
        Returns:
            APIResponse with watchlist data
        """
        self.state_manager.set_loading()
        try:
            response = await self.api_client.get_watchlist(user_id=self.user_id)
            if response.success:
                self.state_manager.set_success(response.data)
            else:
                self.state_manager.set_error(
                    response.error or "Failed to fetch watchlist"
                )
            return response
        except Exception as e:
            error_msg = f"Watchlist fetch error: {str(e)}"
            self.state_manager.set_error(error_msg)
            return APIResponse(
                success=False,
                error=error_msg,
                status_code=500,
            )

    async def get_opportunities(
        self, limit: int = 10
    ) -> APIResponse:
        """Fetch trading opportunities.
        
        Args:
            limit: Maximum number of opportunities
            
        Returns:
            APIResponse with opportunities data
        """
        self.state_manager.set_loading()
        try:
            response = await self.api_client.get_opportunities(
                user_id=self.user_id,
                limit=limit,
            )
            if response.success:
                self.state_manager.set_success(response.data)
            else:
                self.state_manager.set_error(
                    response.error or "Failed to fetch opportunities"
                )
            return response
        except Exception as e:
            error_msg = f"Opportunities fetch error: {str(e)}"
            self.state_manager.set_error(error_msg)
            return APIResponse(
                success=False,
                error=error_msg,
                status_code=500,
            )

    async def get_risk_settings(self) -> APIResponse:
        """Fetch risk settings.
        
        Returns:
            APIResponse with risk settings data
        """
        self.state_manager.set_loading()
        try:
            response = await self.api_client.get_risk_settings(
                user_id=self.user_id
            )
            if response.success:
                self.state_manager.set_success(response.data)
            else:
                self.state_manager.set_error(
                    response.error or "Failed to fetch risk settings"
                )
            return response
        except Exception as e:
            error_msg = f"Risk settings fetch error: {str(e)}"
            self.state_manager.set_error(error_msg)
            return APIResponse(
                success=False,
                error=error_msg,
                status_code=500,
            )

    async def add_watchlist_symbol(self, symbol: str) -> APIResponse:
        """Add symbol to watchlist.
        
        Args:
            symbol: Stock symbol to add
            
        Returns:
            APIResponse with result
        """
        try:
            response = await self.api_client.add_watchlist_symbol(
                symbol=symbol,
                user_id=self.user_id,
            )
            if response.success:
                self.state_manager.set_success(response.data)
            else:
                self.state_manager.set_error(
                    response.error or f"Failed to add {symbol} to watchlist"
                )
            return response
        except Exception as e:
            error_msg = f"Add watchlist error: {str(e)}"
            self.state_manager.set_error(error_msg)
            return APIResponse(
                success=False,
                error=error_msg,
                status_code=500,
            )

    async def remove_watchlist_symbol(self, symbol: str) -> APIResponse:
        """Remove symbol from watchlist.
        
        Args:
            symbol: Stock symbol to remove
            
        Returns:
            APIResponse with result
        """
        try:
            response = await self.api_client.remove_watchlist_symbol(
                symbol=symbol,
                user_id=self.user_id,
            )
            if response.success:
                self.state_manager.set_success(response.data)
            else:
                self.state_manager.set_error(
                    response.error or f"Failed to remove {symbol} from watchlist"
                )
            return response
        except Exception as e:
            error_msg = f"Remove watchlist error: {str(e)}"
            self.state_manager.set_error(error_msg)
            return APIResponse(
                success=False,
                error=error_msg,
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
            response = await self.api_client.validate_symbol(symbol=symbol)
            return response
        except Exception as e:
            error_msg = f"Symbol validation error: {str(e)}"
            return APIResponse(
                success=False,
                error=error_msg,
                status_code=500,
            )

    async def update_risk_settings(
        self,
        risk_level: str,
        confirmed: bool = False,
    ) -> APIResponse:
        """Update risk settings.
        
        Args:
            risk_level: Risk level (low, medium, high)
            confirmed: Whether user confirmed the change
            
        Returns:
            APIResponse with result
        """
        try:
            response = await self.api_client.update_risk_settings(
                risk_level=risk_level,
                user_id=self.user_id,
                confirmed=confirmed,
            )
            if response.success:
                self.state_manager.set_success(response.data)
            else:
                self.state_manager.set_error(
                    response.error or "Failed to update risk settings"
                )
            return response
        except Exception as e:
            error_msg = f"Risk settings update error: {str(e)}"
            self.state_manager.set_error(error_msg)
            return APIResponse(
                success=False,
                error=error_msg,
                status_code=500,
            )
