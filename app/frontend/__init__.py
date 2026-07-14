"""Frontend assets, templates, and components."""

from app.frontend.dashboard import (
    Dashboard,
    DashboardData,
    PortfolioSummary,
    WatchlistItem,
    OpportunityItem,
    TradeItem,
    NewsItem,
    RiskSettings,
)
from app.frontend.api_client import APIClient, APIError, get_api_client
from app.frontend.app_shell import AppShell, AppState, LoadingState

__all__ = [
    "Dashboard",
    "DashboardData",
    "PortfolioSummary",
    "WatchlistItem",
    "OpportunityItem",
    "TradeItem",
    "NewsItem",
    "RiskSettings",
    "APIClient",
    "APIError",
    "get_api_client",
    "AppShell",
    "AppState",
    "LoadingState",
]
