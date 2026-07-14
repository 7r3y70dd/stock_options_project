"""Frontend app shell with basic layout and state management.

Provides the main application structure with header, main content area,
and status area. Handles loading, error, and empty states.
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class LoadingState(str, Enum):
    """Loading state enumeration."""

    IDLE = "idle"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class AppState:
    """Application state container."""

    loading_state: LoadingState = LoadingState.IDLE
    error_message: Optional[str] = None
    user_id: Optional[int] = None
    dashboard_data: Optional[Dict[str, Any]] = None

    def set_loading(self) -> None:
        """Set state to loading."""
        self.loading_state = LoadingState.LOADING
        self.error_message = None

    def set_success(self, data: Optional[Dict[str, Any]] = None) -> None:
        """Set state to success.
        
        Args:
            data: Optional data to store
        """
        self.loading_state = LoadingState.SUCCESS
        self.error_message = None
        if data is not None:
            self.dashboard_data = data

    def set_error(self, error_message: str) -> None:
        """Set state to error.
        
        Args:
            error_message: Error message to display
        """
        self.loading_state = LoadingState.ERROR
        self.error_message = error_message

    def set_idle(self) -> None:
        """Set state to idle."""
        self.loading_state = LoadingState.IDLE
        self.error_message = None

    def is_loading(self) -> bool:
        """Check if currently loading.
        
        Returns:
            True if loading state is LOADING
        """
        return self.loading_state == LoadingState.LOADING

    def is_error(self) -> bool:
        """Check if in error state.
        
        Returns:
            True if loading state is ERROR
        """
        return self.loading_state == LoadingState.ERROR

    def is_success(self) -> bool:
        """Check if in success state.
        
        Returns:
            True if loading state is SUCCESS
        """
        return self.loading_state == LoadingState.SUCCESS


class AppShell:
    """Main application shell with layout and state management.
    
    Provides:
    - Header with app title and user info
    - Main content area for dashboard sections
    - Status area for loading, error, and empty states
    - Centralized state management
    """

    def __init__(self, app_title: str = "Stock Options Dashboard"):
        """Initialize app shell.
        
        Args:
            app_title: Title to display in header
        """
        self.app_title = app_title
        self.state = AppState()

    def render_header(self) -> Dict[str, Any]:
        """Render header component.
        
        Returns:
            Header component data
        """
        return {
            "type": "header",
            "title": self.app_title,
            "user_id": self.state.user_id,
            "subtitle": "AI-powered options trading strategy analyzer",
        }

    def render_loading_state(self) -> Dict[str, Any]:
        """Render loading state component.
        
        Returns:
            Loading state component data
        """
        return {
            "type": "loading",
            "message": "Loading dashboard data...",
            "spinner": True,
        }

    def render_error_state(self) -> Dict[str, Any]:
        """Render error state component.
        
        Returns:
            Error state component data
        """
        return {
            "type": "error",
            "message": self.state.error_message or "An error occurred",
            "icon": "alert-circle",
            "action": {
                "label": "Retry",
                "callback": "retry_load_dashboard",
            },
        }

    def render_empty_state(self) -> Dict[str, Any]:
        """Render empty state component.
        
        Returns:
            Empty state component data
        """
        return {
            "type": "empty",
            "message": "No data available",
            "icon": "inbox",
            "action": {
                "label": "Add to Watchlist",
                "callback": "open_watchlist_modal",
            },
        }

    def render_status_area(self) -> Dict[str, Any]:
        """Render status area based on current state.
        
        Returns:
            Status area component data
        """
        if self.state.is_loading():
            return self.render_loading_state()
        elif self.state.is_error():
            return self.render_error_state()
        elif not self.state.dashboard_data:
            return self.render_empty_state()
        else:
            return {"type": "none"}  # No status area needed

    def render_portfolio_section(self) -> Dict[str, Any]:
        """Render portfolio summary section.
        
        Returns:
            Portfolio section component data
        """
        if not self.state.dashboard_data or "portfolio_summary" not in self.state.dashboard_data:
            return {"type": "portfolio", "data": None}
        
        portfolio = self.state.dashboard_data.get("portfolio_summary", {})
        
        # Import formatting utilities
        from app.frontend.portfolio_summary import format_currency, format_percentage
        
        return {
            "type": "portfolio",
            "title": "Portfolio Summary",
            "data": portfolio,
            "cards": [
                {"label": "Total Value", "value": format_currency(portfolio.get('total_value', 0))},
                {"label": "Cash", "value": format_currency(portfolio.get('cash', 0))},
                {"label": "Positions", "value": format_currency(portfolio.get('positions_value', 0))},
                {"label": "Open P/L", "value": f"{format_currency(portfolio.get('open_pl', 0))} ({format_percentage(portfolio.get('open_pl_pct', 0))})" },
                {"label": "Open Trades", "value": str(portfolio.get('num_open_trades', 0))},
                {"label": "Pending Signals", "value": str(portfolio.get('num_open_signals', 0))},
            ],
        }

    def render_watchlist_section(self) -> Dict[str, Any]:
        """Render watchlist preview section.
        
        Returns:
            Watchlist section component data
        """
        if not self.state.dashboard_data or "watchlist" not in self.state.dashboard_data:
            return {"type": "watchlist", "data": None, "items": []}
        
        watchlist = self.state.dashboard_data.get("watchlist", [])
        return {
            "type": "watchlist",
            "title": "Watchlist",
            "count": len(watchlist),
            "items": [
                {
                    "symbol": item.get("symbol"),
                    "price": item.get("current_price"),
                    "added_at": item.get("added_at"),
                }
                for item in watchlist[:5]  # Show top 5
            ],
            "has_more": len(watchlist) > 5,
        }

    def render_opportunities_section(self) -> Dict[str, Any]:
        """Render top opportunities section.
        
        Returns:
            Opportunities section component data
        """
        if not self.state.dashboard_data or "top_opportunities" not in self.state.dashboard_data:
            return {"type": "opportunities", "data": None, "items": []}
        
        opportunities = self.state.dashboard_data.get("top_opportunities", [])
        return {
            "type": "opportunities",
            "title": "Top Opportunities",
            "count": len(opportunities),
            "items": [
                {
                    "signal_id": item.get("signal_id"),
                    "symbol": item.get("symbol"),
                    "strategy": item.get("strategy_type"),
                    "score": item.get("score"),
                    "expected_profit": item.get("expected_profit"),
                    "max_loss": item.get("max_loss"),
                    "probability": item.get("probability_estimate"),
                }
                for item in opportunities[:5]  # Show top 5
            ],
            "has_more": len(opportunities) > 5,
        }

    def render_trades_section(self) -> Dict[str, Any]:
        """Render open trades section.
        
        Returns:
            Trades section component data
        """
        if not self.state.dashboard_data or "open_trades" not in self.state.dashboard_data:
            return {"type": "trades", "data": None, "items": []}
        
        trades = self.state.dashboard_data.get("open_trades", [])
        return {
            "type": "trades",
            "title": "Open Trades",
            "count": len(trades),
            "items": [
                {
                    "trade_id": item.get("trade_id"),
                    "symbol": item.get("symbol"),
                    "strategy": item.get("strategy_type"),
                    "entry_price": item.get("entry_price"),
                    "current_price": item.get("current_price"),
                    "quantity": item.get("quantity"),
                    "pl": item.get("current_pl"),
                    "pl_pct": item.get("current_pl_pct"),
                }
                for item in trades[:5]  # Show top 5
            ],
            "has_more": len(trades) > 5,
        }

    def render_news_section(self) -> Dict[str, Any]:
        """Render recent news section.
        
        Returns:
            News section component data
        """
        if not self.state.dashboard_data or "recent_news" not in self.state.dashboard_data:
            return {"type": "news", "data": None, "items": []}
        
        news = self.state.dashboard_data.get("recent_news", [])
        return {
            "type": "news",
            "title": "Recent News",
            "count": len(news),
            "items": [
                {
                    "article_id": item.get("article_id"),
                    "symbol": item.get("symbol"),
                    "title": item.get("title"),
                    "source": item.get("source"),
                    "sentiment": item.get("sentiment"),
                    "published_at": item.get("published_at"),
                }
                for item in news[:5]  # Show top 5
            ],
            "has_more": len(news) > 5,
        }

    def render_risk_settings_section(self) -> Dict[str, Any]:
        """Render risk settings section.
        
        Returns:
            Risk settings section component data
        """
        if not self.state.dashboard_data or "risk_settings" not in self.state.dashboard_data:
            return {"type": "risk-settings", "data": None}
        
        risk_settings = self.state.dashboard_data.get("risk_settings", {})
        return {
            "type": "risk-settings",
            "title": "Risk Settings",
            "data": {
                "risk_level": risk_settings.get("risk_level"),
                "paper_trading_enabled": risk_settings.get("paper_trading_enabled"),
                "live_trading_enabled": risk_settings.get("live_trading_enabled"),
                "live_trading_approved": risk_settings.get("live_trading_approved"),
            },
        }

    def render_main_content(self) -> Dict[str, Any]:
        """Render main content area.
        
        Returns:
            Main content component data
        """
        if self.state.is_success() and self.state.dashboard_data:
            return {
                "type": "dashboard",
                "sections": [
                    self.render_portfolio_section(),
                    self.render_watchlist_section(),
                    self.render_opportunities_section(),
                    self.render_trades_section(),
                    self.render_news_section(),
                    self.render_risk_settings_section(),
                ],
            }
        else:
            return {"type": "empty"}

    def render(self) -> Dict[str, Any]:
        """Render complete app shell.
        
        Returns:
            Complete app shell component data
        """
        return {
            "type": "app-shell",
            "header": self.render_header(),
            "status_area": self.render_status_area(),
            "main_content": self.render_main_content(),
        }
