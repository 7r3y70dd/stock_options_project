"""Frontend module for stock options dashboard.

Provides:
- API client for backend communication
- App shell for layout and state management
- Dashboard service for data aggregation
- Portfolio summary component
- Watchlist component
- Shared formatting utilities
"""

from app.frontend.api_client import APIClient, get_api_client, APIError
from app.frontend.app_shell import AppShell, AppState, LoadingState
from app.frontend.dashboard import Dashboard
from app.frontend.portfolio_summary import PortfolioSummaryComponent
from app.frontend.watchlist import WatchlistComponent
from app.frontend.formatters import (
    format_currency,
    format_percentage,
    format_number,
    format_date,
    format_score,
    format_null_value,
    format_change,
)

__all__ = [
    # API Client
    "APIClient",
    "get_api_client",
    "APIError",
    # App Shell
    "AppShell",
    "AppState",
    "LoadingState",
    # Dashboard Service
    "Dashboard",
    # Components
    "PortfolioSummaryComponent",
    "WatchlistComponent",
    # Formatters
    "format_currency",
    "format_percentage",
    "format_number",
    "format_date",
    "format_score",
    "format_null_value",
    "format_change",
]
