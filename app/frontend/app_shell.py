"""Frontend app shell with layout and state management.

Provides the main application structure including:
- Header with title and status
- Main content area for dashboard sections
- Status area for messages and errors
- Shared loading, error, and empty states
- Layout utilities
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


def format_currency(value: Optional[float]) -> str:
    """Format a value as currency.

    Args:
        value: Value to format

    Returns:
        Formatted currency string
    """
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def format_percentage(value: Optional[float], decimals: int = 2) -> str:
    """Format a value as percentage.

    Args:
        value: Value to format (0-100)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string
    """
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}%"


def format_number(value: Optional[float], decimals: int = 2) -> str:
    """Format a number with thousands separator.

    Args:
        value: Value to format
        decimals: Number of decimal places

    Returns:
        Formatted number string
    """
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def render_loading_state() -> Dict[str, Any]:
    """Render loading state.

    Returns:
        Loading state dictionary
    """
    return {
        "state": "loading",
        "message": "Loading...",
    }


def render_error_state(error: str, retry_callback: Optional[str] = None) -> Dict[str, Any]:
    """Render error state.

    Args:
        error: Error message
        retry_callback: Optional callback name for retry button

    Returns:
        Error state dictionary
    """
    return {
        "state": "error",
        "message": error,
        "retry_callback": retry_callback,
    }


def render_empty_state(message: str = "No data available") -> Dict[str, Any]:
    """Render empty state.

    Args:
        message: Empty state message

    Returns:
        Empty state dictionary
    """
    return {
        "state": "empty",
        "message": message,
    }


def render_portfolio_section(portfolio_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Render portfolio summary section.

    Args:
        portfolio_data: Portfolio data from API

    Returns:
        Rendered portfolio section
    """
    if portfolio_data is None:
        return render_empty_state("Portfolio data not available")
    
    return {
        "section": "portfolio",
        "title": "Portfolio Summary",
        "cards": [
            {
                "label": "Total Value",
                "value": format_currency(portfolio_data.get("total_value")),
                "type": "currency",
            },
            {
                "label": "Cash",
                "value": format_currency(portfolio_data.get("cash")),
                "type": "currency",
            },
            {
                "label": "Positions Value",
                "value": format_currency(portfolio_data.get("positions_value")),
                "type": "currency",
            },
            {
                "label": "Open P/L",
                "value": format_currency(portfolio_data.get("open_pl")),
                "type": "currency",
                "highlight": portfolio_data.get("open_pl", 0) >= 0,
            },
            {
                "label": "Open P/L %",
                "value": format_percentage(portfolio_data.get("open_pl_pct")),
                "type": "percentage",
                "highlight": portfolio_data.get("open_pl_pct", 0) >= 0,
            },
            {
                "label": "Open Trades",
                "value": str(portfolio_data.get("num_open_trades", 0)),
                "type": "number",
            },
            {
                "label": "Open Signals",
                "value": str(portfolio_data.get("num_open_signals", 0)),
                "type": "number",
            },
        ],
    }


def render_watchlist_section(watchlist_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Render watchlist section.

    Args:
        watchlist_data: Watchlist data from API

    Returns:
        Rendered watchlist section
    """
    if watchlist_data is None:
        return render_empty_state("Watchlist not available")
    
    symbols = watchlist_data.get("symbols", [])
    
    if not symbols:
        return render_empty_state("No symbols in watchlist")
    
    return {
        "section": "watchlist",
        "title": "Watchlist",
        "count": watchlist_data.get("count", 0),
        "symbols": [
            {
                "symbol": s["symbol"],
                "current_price": format_currency(s.get("current_price")),
                "added_at": s.get("added_at"),
                "last_updated": s.get("last_updated"),
                "data_freshness_seconds": s.get("data_freshness_seconds"),
            }
            for s in symbols
        ],
    }


def render_opportunities_section(opportunities_data: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Render top opportunities section.

    Args:
        opportunities_data: Opportunities data from API

    Returns:
        Rendered opportunities section
    """
    if opportunities_data is None:
        return render_empty_state("Opportunities not available")
    
    if not opportunities_data:
        return render_empty_state("No opportunities available")
    
    return {
        "section": "opportunities",
        "title": "Top Opportunities",
        "count": len(opportunities_data),
        "opportunities": [
            {
                "signal_id": opp.get("signal_id"),
                "symbol": opp.get("symbol"),
                "strategy_type": opp.get("strategy_type"),
                "score": format_number(opp.get("score"), 1),
                "expected_profit": format_currency(opp.get("expected_profit")),
                "max_loss": format_currency(opp.get("max_loss")),
                "probability_estimate": format_percentage(opp.get("probability_estimate") * 100, 1),
                "reason": opp.get("reason"),
                "status": opp.get("status"),
            }
            for opp in opportunities_data
        ],
    }


def render_trades_section(trades_data: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Render open trades section.

    Args:
        trades_data: Trades data from API

    Returns:
        Rendered trades section
    """
    if trades_data is None:
        return render_empty_state("Trades not available")
    
    if not trades_data:
        return render_empty_state("No open trades")
    
    return {
        "section": "trades",
        "title": "Open Trades",
        "count": len(trades_data),
        "trades": [
            {
                "trade_id": trade.get("trade_id"),
                "symbol": trade.get("symbol"),
                "strategy_type": trade.get("strategy_type"),
                "entry_price": format_currency(trade.get("entry_price")),
                "current_price": format_currency(trade.get("current_price")),
                "quantity": str(trade.get("quantity", 0)),
                "entry_date": trade.get("entry_date"),
                "current_pl": format_currency(trade.get("current_pl")),
                "current_pl_pct": format_percentage(trade.get("current_pl_pct")),
                "status": trade.get("status"),
            }
            for trade in trades_data
        ],
    }


def render_news_section(news_data: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Render recent news section.

    Args:
        news_data: News data from API

    Returns:
        Rendered news section
    """
    if news_data is None:
        return render_empty_state("News not available")
    
    if not news_data:
        return render_empty_state("No recent news")
    
    return {
        "section": "news",
        "title": "Recent News",
        "count": len(news_data),
        "articles": [
            {
                "article_id": article.get("article_id"),
                "symbol": article.get("symbol"),
                "title": article.get("title"),
                "description": article.get("description"),
                "url": article.get("url"),
                "source": article.get("source"),
                "published_at": article.get("published_at"),
                "sentiment": article.get("sentiment"),
                "sentiment_score": format_number(article.get("sentiment_score"), 2) if article.get("sentiment_score") else "N/A",
                "event_type": article.get("event_type"),
            }
            for article in news_data
        ],
    }


def render_risk_settings_section(risk_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Render risk settings section.

    Args:
        risk_data: Risk settings data from API

    Returns:
        Rendered risk settings section
    """
    if risk_data is None:
        return render_empty_state("Risk settings not available")
    
    return {
        "section": "risk_settings",
        "title": "Risk Settings",
        "risk_level": risk_data.get("risk_level"),
        "paper_trading_enabled": risk_data.get("paper_trading_enabled"),
        "live_trading_enabled": risk_data.get("live_trading_enabled"),
        "live_trading_approved": risk_data.get("live_trading_approved"),
        "risk_levels_info": risk_data.get("risk_levels_info", []),
    }


class AppShell:
    """Main application shell."""

    def __init__(self, api_client: Any, user_id: int = 1):
        """Initialize app shell.

        Args:
            api_client: API client instance
            user_id: User ID for demo
        """
        self.api_client = api_client
        self.user_id = user_id
        self.dashboard_data: Optional[Dict[str, Any]] = None
        self.loading = False
        self.error: Optional[str] = None
        self.last_refresh: Optional[datetime] = None

    async def load_dashboard(self) -> None:
        """Load dashboard data from API."""
        try:
            self.loading = True
            self.error = None
            
            self.dashboard_data = await self.api_client.get_dashboard(self.user_id)
            self.last_refresh = datetime.now()
        except Exception as e:
            logger.error(f"Error loading dashboard: {e}")
            self.error = f"Failed to load dashboard: {str(e)}"
            self.dashboard_data = None
        finally:
            self.loading = False

    def render(self) -> Dict[str, Any]:
        """Render app shell.

        Returns:
            Rendered app shell state
        """
        if self.loading:
            return {
                "state": "loading",
                "message": "Loading dashboard...",
            }
        
        if self.error:
            return {
                "state": "error",
                "message": self.error,
                "retry_callback": "load_dashboard",
            }
        
        if not self.dashboard_data:
            return {
                "state": "empty",
                "message": "No dashboard data available",
            }
        
        return {
            "state": "success",
            "header": {
                "title": "Stock Options Dashboard",
                "user_id": self.user_id,
                "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None,
            },
            "sections": {
                "portfolio": render_portfolio_section(self.dashboard_data.get("portfolio_summary")),
                "watchlist": render_watchlist_section(self.dashboard_data.get("watchlist")),
                "opportunities": render_opportunities_section(self.dashboard_data.get("top_opportunities")),
                "trades": render_trades_section(self.dashboard_data.get("open_trades")),
                "news": render_news_section(self.dashboard_data.get("recent_news")),
                "risk_settings": render_risk_settings_section(self.dashboard_data.get("risk_settings")),
            },
            "timestamp": self.dashboard_data.get("timestamp"),
        }
