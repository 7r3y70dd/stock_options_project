"""Application shell with layout, navigation, and state management.

Provides the main app container with header, navigation, content area,
and status display.
"""

import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class LoadingState(Enum):
    """Loading state enumeration."""
    IDLE = "idle"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"
    EMPTY = "empty"


class AppState:
    """Application state container."""
    
    def __init__(self, user_id: int = 1):
        """Initialize app state.
        
        Args:
            user_id: Current user ID
        """
        self.user_id = user_id
        self.current_page = "dashboard"
        self.loading_state = LoadingState.IDLE
        self.error_message: Optional[str] = None
        self.last_refresh: Optional[datetime] = None
        self.data: Dict[str, Any] = {}
    
    def set_loading(self):
        """Set state to loading."""
        self.loading_state = LoadingState.LOADING
        self.error_message = None
    
    def set_success(self):
        """Set state to success."""
        self.loading_state = LoadingState.SUCCESS
        self.error_message = None
        self.last_refresh = datetime.now()
    
    def set_error(self, message: str):
        """Set state to error.
        
        Args:
            message: Error message
        """
        self.loading_state = LoadingState.ERROR
        self.error_message = message
    
    def set_empty(self):
        """Set state to empty."""
        self.loading_state = LoadingState.EMPTY
        self.error_message = None


class AppShell:
    """Main application shell with layout and navigation."""
    
    # Available pages and routes
    PAGES = {
        "dashboard": "/dashboard",
        "opportunities": "/opportunities",
        "portfolio": "/portfolio",
        "trades": "/trades",
        "watchlist": "/watchlist",
        "risk-settings": "/risk-settings",
        "news": "/news",
        "status": "/status",
    }
    
    def __init__(self, user_id: int = 1):
        """Initialize app shell.
        
        Args:
            user_id: Current user ID
        """
        self.state = AppState(user_id=user_id)
    
    def render_header(self) -> str:
        """Render application header.
        
        Returns:
            Formatted header string
        """
        return f"""
╔════════════════════════════════════════════════════════════════╗
║           Options Tracker - Stock Options Dashboard            ║
║                    User ID: {self.state.user_id}                        ║
╚════════════════════════════════════════════════════════════════╝
"""
    
    def render_navigation(self) -> str:
        """Render navigation menu.
        
        Returns:
            Formatted navigation string
        """
        nav_items = []
        for page_name, route in self.PAGES.items():
            marker = "→" if page_name == self.state.current_page else " "
            nav_items.append(f"{marker} {page_name.replace('-', ' ').title():20} {route}")
        
        return f"""
┌─ Navigation ─────────────────────────────────────────────────────┐
│                                                                  │
{chr(10).join('│ ' + item.ljust(62) + '│' for item in nav_items)}
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
    
    def render_loading_state(self) -> str:
        """Render loading indicator.
        
        Returns:
            Formatted loading string
        """
        return """
┌─ Loading ────────────────────────────────────────────────────────┐
│                                                                  │
│                    ⟳ Loading data...                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
    
    def render_error_state(self, error_message: str) -> str:
        """Render error state.
        
        Args:
            error_message: Error message to display
            
        Returns:
            Formatted error string
        """
        return f"""
┌─ Error ──────────────────────────────────────────────────────────┐
│                                                                  │
│  ✗ {error_message[:58].ljust(58)}  │
│                                                                  │
│  [Retry]  [Go Back]                                              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
    
    def render_empty_state(self, message: str = "No data available") -> str:
        """Render empty state.
        
        Args:
            message: Empty state message
            
        Returns:
            Formatted empty state string
        """
        return f"""
┌─ Empty ──────────────────────────────────────────────────────────┐
│                                                                  │
│  ○ {message[:58].ljust(58)}  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
    
    def render_footer(self) -> str:
        """Render application footer.
        
        Returns:
            Formatted footer string
        """
        last_refresh = "Never" if not self.state.last_refresh else self.state.last_refresh.strftime("%H:%M:%S")
        return f"""
┌─ Status ─────────────────────────────────────────────────────────┐
│ Last Refresh: {last_refresh:20} | Page: {self.state.current_page:20} │
└──────────────────────────────────────────────────────────────────┘
"""
    
    def render_page(self, content: str) -> str:
        """Render complete page with shell.
        
        Args:
            content: Page content to render
            
        Returns:
            Complete rendered page
        """
        output = self.render_header()
        output += self.render_navigation()
        
        if self.state.loading_state == LoadingState.LOADING:
            output += self.render_loading_state()
        elif self.state.loading_state == LoadingState.ERROR:
            output += self.render_error_state(self.state.error_message or "Unknown error")
        elif self.state.loading_state == LoadingState.EMPTY:
            output += self.render_empty_state()
        else:
            output += content
        
        output += self.render_footer()
        return output
    
    def navigate_to(self, page_name: str) -> None:
        """Navigate to a page.
        
        Args:
            page_name: Page name to navigate to
        """
        if page_name in self.PAGES:
            self.state.current_page = page_name
            logger.info(f"Navigated to {page_name}")
        else:
            logger.warning(f"Unknown page: {page_name}")
