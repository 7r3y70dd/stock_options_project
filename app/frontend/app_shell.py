"""Frontend app shell for rendering dashboard sections.

Provides reusable rendering functions for dashboard components including
portfolio summary, watchlist, opportunities, trades, news, and risk settings.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def format_currency(value: Optional[float]) -> str:
    """Format a value as currency.
    
    Args:
        value: Numeric value to format
        
    Returns:
        Formatted currency string
    """
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def format_percentage(value: Optional[float], decimals: int = 2) -> str:
    """Format a value as percentage.
    
    Args:
        value: Numeric value to format (0-100 or 0-1)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    if value is None:
        return "N/A"
    # If value is between 0 and 1, assume it's a decimal percentage
    if -1 <= value <= 1:
        value = value * 100
    return f"{value:.{decimals}f}%"


def format_number(value: Optional[float], decimals: int = 2) -> str:
    """Format a number with thousand separators.
    
    Args:
        value: Numeric value to format
        decimals: Number of decimal places
        
    Returns:
        Formatted number string
    """
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def render_portfolio_section(portfolio_data: Dict[str, Any]) -> str:
    """Render portfolio summary section.
    
    Args:
        portfolio_data: Portfolio summary data
        
    Returns:
        Formatted portfolio section string
    """
    try:
        if not portfolio_data:
            return "Portfolio: No data available"
        
        total_value = portfolio_data.get("total_value", 0)
        cash = portfolio_data.get("cash", 0)
        positions_value = portfolio_data.get("positions_value", 0)
        open_pl = portfolio_data.get("open_pl", 0)
        open_pl_pct = portfolio_data.get("open_pl_pct", 0)
        num_open_trades = portfolio_data.get("num_open_trades", 0)
        num_open_signals = portfolio_data.get("num_open_signals", 0)
        
        return f"""
Portfolio Summary:
  Total Value: {format_currency(total_value)}
  Cash: {format_currency(cash)}
  Positions Value: {format_currency(positions_value)}
  Open P/L: {format_currency(open_pl)} ({format_percentage(open_pl_pct)})
  Open Trades: {num_open_trades}
  Pending Signals: {num_open_signals}
"""
    except Exception as e:
        logger.error(f"Error rendering portfolio section: {e}", exc_info=True)
        return f"Portfolio: Error rendering data - {e}"


def render_watchlist_section(watchlist_data: Any) -> str:
    """Render watchlist section.
    
    Handles both list and dict input formats for watchlist data.
    
    Args:
        watchlist_data: Watchlist data (list of items or dict with symbols key)
        
    Returns:
        Formatted watchlist section string
    """
    try:
        # Handle different input formats
        if isinstance(watchlist_data, list):
            items = watchlist_data
        elif isinstance(watchlist_data, dict):
            items = watchlist_data.get("symbols", [])
            if not isinstance(items, list):
                items = []
        else:
            items = []
        
        if not items:
            return "Watchlist: No symbols"
        
        lines = ["Watchlist:"]
        for item in items:
            if isinstance(item, dict):
                symbol = item.get("symbol", "UNKNOWN")
                current_price = item.get("current_price")
                last_updated = item.get("last_updated")
                data_freshness = item.get("data_freshness_seconds")
                
                price_str = format_currency(current_price) if current_price else "N/A"
                freshness_str = f"{data_freshness}s ago" if data_freshness else "N/A"
                
                lines.append(f"  {symbol}: {price_str} (updated {freshness_str})")
            else:
                # Handle non-dict items gracefully
                lines.append(f"  {item}")
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error rendering watchlist section: {e}", exc_info=True)
        return f"Watchlist: Error rendering data - {e}"


def render_opportunities_section(opportunities_data: List[Dict[str, Any]]) -> str:
    """Render top opportunities section.
    
    Args:
        opportunities_data: List of opportunity items
        
    Returns:
        Formatted opportunities section string
    """
    try:
        if not opportunities_data:
            return "Top Opportunities: None"
        
        lines = ["Top Opportunities:"]
        for opp in opportunities_data[:5]:  # Show top 5
            symbol = opp.get("symbol", "UNKNOWN")
            strategy = opp.get("strategy_type", "UNKNOWN")
            score = opp.get("score", 0)
            expected_profit = opp.get("expected_profit", 0)
            max_loss = opp.get("max_loss", 0)
            
            lines.append(
                f"  {symbol} ({strategy}): Score {format_percentage(score/100)} | "
                f"Profit {format_currency(expected_profit)} | Loss {format_currency(max_loss)}"
            )
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error rendering opportunities section: {e}", exc_info=True)
        return f"Top Opportunities: Error rendering data - {e}"


def render_trades_section(trades_data: List[Dict[str, Any]]) -> str:
    """Render open trades section.
    
    Args:
        trades_data: List of trade items
        
    Returns:
        Formatted trades section string
    """
    try:
        if not trades_data:
            return "Open Trades: None"
        
        lines = ["Open Trades:"]
        for trade in trades_data[:5]:  # Show top 5
            symbol = trade.get("symbol", "UNKNOWN")
            strategy = trade.get("strategy_type", "UNKNOWN")
            entry_price = trade.get("entry_price", 0)
            current_price = trade.get("current_price")
            quantity = trade.get("quantity", 0)
            current_pl = trade.get("current_pl")
            current_pl_pct = trade.get("current_pl_pct")
            
            current_price_str = format_currency(current_price) if current_price else "N/A"
            pl_str = format_currency(current_pl) if current_pl else "N/A"
            pl_pct_str = format_percentage(current_pl_pct) if current_pl_pct else "N/A"
            
            lines.append(
                f"  {symbol} ({strategy}): {quantity} @ {format_currency(entry_price)} | "
                f"Current {current_price_str} | P/L {pl_str} ({pl_pct_str})"
            )
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error rendering trades section: {e}", exc_info=True)
        return f"Open Trades: Error rendering data - {e}"


def render_news_section(news_data: List[Dict[str, Any]]) -> str:
    """Render recent news section.
    
    Args:
        news_data: List of news items
        
    Returns:
        Formatted news section string
    """
    try:
        if not news_data:
            return "Recent News: None"
        
        lines = ["Recent News:"]
        for article in news_data[:5]:  # Show top 5
            symbol = article.get("symbol", "UNKNOWN")
            title = article.get("title", "No title")
            sentiment = article.get("sentiment", "neutral")
            source = article.get("source", "Unknown")
            
            lines.append(f"  [{symbol}] {title} ({sentiment}) - {source}")
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error rendering news section: {e}", exc_info=True)
        return f"Recent News: Error rendering data - {e}"


def render_risk_settings_section(risk_settings_data: Dict[str, Any]) -> str:
    """Render risk settings section.
    
    Args:
        risk_settings_data: Risk settings data
        
    Returns:
        Formatted risk settings section string
    """
    try:
        if not risk_settings_data:
            return "Risk Settings: No data available"
        
        risk_level = risk_settings_data.get("risk_level", "medium")
        paper_trading = risk_settings_data.get("paper_trading_enabled", True)
        live_trading = risk_settings_data.get("live_trading_enabled", False)
        live_approved = risk_settings_data.get("live_trading_approved", False)
        
        return f"""
Risk Settings:
  Risk Level: {risk_level.upper()}
  Paper Trading: {'Enabled' if paper_trading else 'Disabled'}
  Live Trading: {'Enabled' if live_trading else 'Disabled'}
  Live Trading Approved: {'Yes' if live_approved else 'No'}
"""
    except Exception as e:
        logger.error(f"Error rendering risk settings section: {e}", exc_info=True)
        return f"Risk Settings: Error rendering data - {e}"


def render_dashboard(
    dashboard_data: Dict[str, Any],
) -> str:
    """Render complete dashboard.
    
    Args:
        dashboard_data: Complete dashboard data
        
    Returns:
        Formatted dashboard string
    """
    try:
        if not dashboard_data:
            return "Dashboard: No data available"
        
        timestamp = dashboard_data.get("timestamp", datetime.utcnow().isoformat())
        
        sections = [
            f"\n=== Dashboard ({timestamp}) ===",
            render_portfolio_section(dashboard_data.get("portfolio_summary", {})),
            render_watchlist_section(dashboard_data.get("watchlist", [])),
            render_opportunities_section(dashboard_data.get("top_opportunities", [])),
            render_trades_section(dashboard_data.get("open_trades", [])),
            render_news_section(dashboard_data.get("recent_news", [])),
            render_risk_settings_section(dashboard_data.get("risk_settings", {})),
        ]
        
        return "\n".join(sections)
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}", exc_info=True)
        return f"Dashboard: Error rendering - {e}"
