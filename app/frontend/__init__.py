"""Frontend module for stock options dashboard.

Provides:
- API client for backend communication
- App shell for layout and state management
- Dashboard service for data aggregation
- Portfolio summary component
"""

from app.frontend.api_client import APIClient, get_api_client, APIError
from app.frontend.app_shell import AppShell
from app.frontend.portfolio_summary import (
    PortfolioSummaryComponent,
    format_currency,
    format_percentage,
    format_number,
)

__all__ = [
    "APIClient",
    "get_api_client",
    "APIError",
    "AppShell",
    "PortfolioSummaryComponent",
    "format_currency",
    "format_percentage",
    "format_number",
]
