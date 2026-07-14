"""Application shell with layout, navigation, and state management.

Provides the main app container with header, navigation, content area,
and status display.
"""

import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime
from app.frontend.formatters import (
    format_currency,
    format_percentage,
    format_number,
    format_date,
    format_price,
)

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
    
    def render_portfolio_section(self, portfolio_data: Dict[str, Any]) -> str:
        """Render portfolio summary section.
        
        Args:
            portfolio_data: Portfolio data dictionary
            
        Returns:
            Formatted portfolio section
        """
        if not portfolio_data:
            return self.render_empty_state("No portfolio data available")
        
        total_value = format_currency(portfolio_data.get('total_value'))
        cash = format_currency(portfolio_data.get('cash'))
        positions_value = format_currency(portfolio_data.get('positions_value'))
        open_pl = format_currency(portfolio_data.get('open_pl'))
        open_pl_pct = format_percentage(portfolio_data.get('open_pl_pct'))
        num_trades = format_number(portfolio_data.get('num_open_trades', 0))
        num_signals = format_number(portfolio_data.get('num_open_signals', 0))
        
        return f"""
┌─ Portfolio Summary ──────────────────────────────────────────────┐
│                                                                  │
│  Total Value:        {total_value:>30}  │
│  Cash:               {cash:>30}  │
│  Positions Value:    {positions_value:>30}  │
│                                                                  │
│  Open P/L:           {open_pl:>30}  │
│  Open P/L %:         {open_pl_pct:>30}  │
│                                                                  │
│  Open Trades:        {num_trades:>30}  │
│  Open Signals:       {num_signals:>30}  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
    
    def render_watchlist_section(self, watchlist_data: Any) -> str:
        """Render watchlist section.
        
        Args:
            watchlist_data: Watchlist data (list or dict)
            
        Returns:
            Formatted watchlist section
        """
        # Handle both list and dict formats
        if isinstance(watchlist_data, dict):
            symbols = watchlist_data.get('symbols', [])
        elif isinstance(watchlist_data, list):
            symbols = watchlist_data
        else:
            symbols = []
        
        if not symbols:
            return """
┌─ Watchlist ──────────────────────────────────────────────────────┐
│                                                                  │
│  ○ No symbols in watchlist                                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
        
        lines = ["┌─ Watchlist ──────────────────────────────────────────────────────┐", "│                                                                  │"]
        
        for symbol_data in symbols[:5]:  # Show first 5
            if isinstance(symbol_data, dict):
                symbol = symbol_data.get('symbol', 'N/A')
                price = format_price(symbol_data.get('current_price'))
                added_at = format_date(symbol_data.get('added_at'))
            else:
                symbol = str(symbol_data)
                price = "Price unavailable"
                added_at = "Not available"
            
            lines.append(f"│  {symbol:8} {price:20} Added: {added_at:20} │")
        
        if len(symbols) > 5:
            lines.append(f"│  ... and {len(symbols) - 5} more symbols                                    │")
        
        lines.append("│                                                                  │")
        lines.append("└──────────────────────────────────────────────────────────────────┘")
        
        return "\n".join(lines) + "\n"
    
    def render_opportunities_section(self, opportunities_data: List[Dict[str, Any]]) -> str:
        """Render top opportunities section.
        
        Args:
            opportunities_data: List of opportunity dictionaries
            
        Returns:
            Formatted opportunities section
        """
        if not opportunities_data:
            return """
┌─ Top Opportunities ──────────────────────────────────────────────┐
│                                                                  │
│  ○ No opportunities available                                    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
        
        lines = ["┌─ Top Opportunities ──────────────────────────────────────────────┐", "│                                                                  │"]
        
        for opp in opportunities_data[:3]:  # Show top 3
            symbol = opp.get('symbol', 'N/A')
            strategy = opp.get('strategy_type', 'N/A').replace('_', ' ').title()
            score = format_number(opp.get('score', 0))
            profit = format_currency(opp.get('expected_profit', 0))
            signal_id = opp.get('signal_id', 'N/A')
            
            lines.append(f"│  [{signal_id}] {symbol:8} {strategy:20} Score: {score:5}  │")
            lines.append(f"│      Expected Profit: {profit:40}  │")
        
        if len(opportunities_data) > 3:
            lines.append(f"│  ... and {len(opportunities_data) - 3} more opportunities                      │")
        
        lines.append("│                                                                  │")
        lines.append("└──────────────────────────────────────────────────────────────────┘")
        
        return "\n".join(lines) + "\n"
    
    def render_trades_section(self, trades_data: List[Dict[str, Any]]) -> str:
        """Render open trades section.
        
        Args:
            trades_data: List of trade dictionaries
            
        Returns:
            Formatted trades section
        """
        if not trades_data:
            return """
┌─ Open Trades ────────────────────────────────────────────────────┐
│                                                                  │
│  ○ No open trades yet.                                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
        
        lines = ["┌─ Open Trades ────────────────────────────────────────────────────┐", "│                                                                  │"]
        
        for trade in trades_data[:3]:  # Show first 3
            symbol = trade.get('symbol', 'N/A')
            entry_price = format_currency(trade.get('entry_price', 0))
            current_price = format_currency(trade.get('current_price', 0))
            pl = format_currency(trade.get('pl', 0))
            
            lines.append(f"│  {symbol:8} Entry: {entry_price:15} Current: {current_price:15}  │")
            lines.append(f"│      P/L: {pl:50}  │")
        
        if len(trades_data) > 3:
            lines.append(f"│  ... and {len(trades_data) - 3} more trades                              │")
        
        lines.append("│                                                                  │")
        lines.append("└──────────────────────────────────────────────────────────────────┘")
        
        return "\n".join(lines) + "\n"
    
    def render_news_section(self, news_data: List[Dict[str, Any]]) -> str:
        """Render recent news section.
        
        Args:
            news_data: List of news dictionaries
            
        Returns:
            Formatted news section
        """
        if not news_data:
            return """
┌─ Recent News ────────────────────────────────────────────────────┐
│                                                                  │
│  ○ No recent news.                                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
        
        lines = ["┌─ Recent News ────────────────────────────────────────────────────┐", "│                                                                  │"]
        
        for news in news_data[:3]:  # Show first 3
            symbol = news.get('symbol', 'N/A')
            headline = news.get('headline', 'N/A')[:50]
            published = format_date(news.get('published_at'))
            
            lines.append(f"│  [{symbol}] {headline:50}  │")
            lines.append(f"│      {published:60}  │")
        
        if len(news_data) > 3:
            lines.append(f"│  ... and {len(news_data) - 3} more news items                            │")
        
        lines.append("│                                                                  │")
        lines.append("└──────────────────────────────────────────────────────────────────┘")
        
        return "\n".join(lines) + "\n"
    
    def render_risk_settings_section(self, risk_settings: Dict[str, Any]) -> str:
        """Render risk settings section.
        
        Args:
            risk_settings: Risk settings dictionary
            
        Returns:
            Formatted risk settings section
        """
        if not risk_settings:
            return self.render_empty_state("No risk settings available")
        
        risk_level = risk_settings.get('risk_level', 'N/A').upper()
        paper_trading = "Enabled" if risk_settings.get('paper_trading_enabled') else "Disabled"
        live_trading = "Enabled" if risk_settings.get('live_trading_enabled') else "Disabled"
        live_approved = "Yes" if risk_settings.get('live_trading_approved') else "No"
        
        return f"""
┌─ Risk Settings ──────────────────────────────────────────────────┐
│                                                                  │
│  Risk Level:         {risk_level:>30}  │
│  Paper Trading:      {paper_trading:>30}  │
│  Live Trading:       {live_trading:>30}  │
│  Live Approved:      {live_approved:>30}  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""
    
    def render_dashboard_page(self, dashboard_data: Dict[str, Any]) -> str:
        """Render complete dashboard page.
        
        Args:
            dashboard_data: Full dashboard data from API
            
        Returns:
            Formatted dashboard page
        """
        if not dashboard_data:
            return self.render_empty_state("No dashboard data available")
        
        content = ""
        
        # Portfolio section
        portfolio = dashboard_data.get('portfolio_summary', {})
        content += self.render_portfolio_section(portfolio)
        content += "\n"
        
        # Watchlist section
        watchlist = dashboard_data.get('watchlist', [])
        content += self.render_watchlist_section(watchlist)
        content += "\n"
        
        # Top opportunities section
        opportunities = dashboard_data.get('top_opportunities', [])
        content += self.render_opportunities_section(opportunities)
        content += "\n"
        
        # Open trades section
        trades = dashboard_data.get('open_trades', [])
        content += self.render_trades_section(trades)
        content += "\n"
        
        # Recent news section
        news = dashboard_data.get('recent_news', [])
        content += self.render_news_section(news)
        content += "\n"
        
        # Risk settings section
        risk_settings = dashboard_data.get('risk_settings', {})
        content += self.render_risk_settings_section(risk_settings)
        content += "\n"
        
        # Timestamp
        timestamp = dashboard_data.get('timestamp')
        if timestamp:
            formatted_time = format_date(timestamp)
            content += f"\nLast Updated: {formatted_time}\n"
        
        return content
