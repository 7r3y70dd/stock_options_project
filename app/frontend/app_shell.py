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

    def render_main_content(self) -> Dict[str, Any]:
        """Render main content area.
        
        Returns:
            Main content component data
        """
        if self.state.is_success() and self.state.dashboard_data:
            return {
                "type": "dashboard",
                "sections": [
                    {"type": "portfolio", "data": self.state.dashboard_data.get("portfolio_summary")},
                    {"type": "watchlist", "data": self.state.dashboard_data.get("watchlist")},
                    {"type": "opportunities", "data": self.state.dashboard_data.get("opportunities")},
                    {"type": "risk-settings", "data": self.state.dashboard_data.get("risk_settings")},
                ],
            }
        else:
            return {"type": "empty"}

    def render(self) -> Dict[str, Any]:
        """Render complete app shell.
        
        Returns:
            Complete app layout
        """
        return {
            "type": "app-shell",
            "header": self.render_header(),
            "main_content": self.render_main_content(),
            "status_area": self.render_status_area(),
        }
