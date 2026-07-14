"""Frontend module for dashboard UI components and utilities."""

from app.frontend.dashboard import Dashboard
from app.frontend.api_client import APIClient, APIError, get_api_client
from app.frontend.app_shell import AppShell, AppState, LoadingState
from app.frontend.portfolio_summary import PortfolioSummaryComponent
from app.frontend.formatters import (
    format_currency,
    format_percentage,
    format_number,
    format_date,
    format_price,
)

__all__ = [
    "Dashboard",
    "APIClient",
    "APIError",
    "get_api_client",
    "AppShell",
    "AppState",
    "LoadingState",
    "PortfolioSummaryComponent",
    "format_currency",
    "format_percentage",
    "format_number",
    "format_date",
    "format_price",
]
