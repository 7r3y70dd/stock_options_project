"""Application shell for rendering dashboard sections.

Provides rendering functions for dashboard components including
portfolio summary, watchlist, opportunities, trades, news, and risk settings.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


def format_currency(value: Optional[float]) -> str:
    """Format value as currency.
    
    Args:
        value: Numeric value
        
    Returns:
        Formatted currency string
    """
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def format_percentage(value: Optional[float]) -> str:
    """Format value as percentage.
    
    Args:
        value: Numeric value (0-100 or 0-1)
        
    Returns:
        Formatted percentage string
    """
    if value is None:
        return "N/A"
    # Handle both 0-100 and 0-1 ranges
    if abs(value) <= 1:
        value = value * 100
    return f"{value:.2f}%"


def format_number(value: Optional[float], decimals: int = 2) -> str:
    """Format value as number.
    
    Args:
        value: Numeric value
        decimals: Number of decimal places
        
    Returns:
        Formatted number string
    """
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def render_portfolio_section(portfolio_data: Optional[Dict[str, Any]]) -> str:
    """Render portfolio summary section.
    
    Args:
        portfolio_data: Portfolio summary data
        
    Returns:
        Rendered HTML/text representation
    """
    if not portfolio_data:
        return "<div class='portfolio-section'><p>No portfolio data available</p></div>"
    
    try:
        total_value = portfolio_data.get("total_value", 0)
        cash = portfolio_data.get("cash", 0)
        positions_value = portfolio_data.get("positions_value", 0)
        open_pl = portfolio_data.get("open_pl", 0)
        open_pl_pct = portfolio_data.get("open_pl_pct", 0)
        num_open_trades = portfolio_data.get("num_open_trades", 0)
        num_open_signals = portfolio_data.get("num_open_signals", 0)
        
        html = f"""
        <div class='portfolio-section'>
            <h2>Portfolio Summary</h2>
            <div class='portfolio-cards'>
                <div class='card'>
                    <label>Total Value</label>
                    <value>{format_currency(total_value)}</value>
                </div>
                <div class='card'>
                    <label>Cash</label>
                    <value>{format_currency(cash)}</value>
                </div>
                <div class='card'>
                    <label>Positions Value</label>
                    <value>{format_currency(positions_value)}</value>
                </div>
                <div class='card'>
                    <label>Open P/L</label>
                    <value>{format_currency(open_pl)}</value>
                </div>
                <div class='card'>
                    <label>Open P/L %</label>
                    <value>{format_percentage(open_pl_pct)}</value>
                </div>
                <div class='card'>
                    <label>Open Trades</label>
                    <value>{num_open_trades}</value>
                </div>
                <div class='card'>
                    <label>Pending Signals</label>
                    <value>{num_open_signals}</value>
                </div>
            </div>
        </div>
        """
        return html
    except Exception as e:
        logger.error(f"Error rendering portfolio section: {e}")
        return f"<div class='portfolio-section'><p>Error rendering portfolio: {str(e)}</p></div>"


def render_watchlist_section(watchlist_data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]) -> str:
    """Render watchlist section.
    
    Handles both list and dict input formats:
    - List: [{"symbol": "AAPL", ...}, ...]
    - Dict: {"symbols": [{"symbol": "AAPL", ...}, ...], "count": 1}
    
    Args:
        watchlist_data: Watchlist data (list or dict)
        
    Returns:
        Rendered HTML/text representation
    """
    if not watchlist_data:
        return "<div class='watchlist-section'><p>No watchlist data available</p></div>"
    
    try:
        # Handle both list and dict formats
        if isinstance(watchlist_data, list):
            symbols = watchlist_data
        elif isinstance(watchlist_data, dict):
            symbols = watchlist_data.get("symbols", [])
        else:
            symbols = []
        
        if not symbols:
            return "<div class='watchlist-section'><p>Watchlist is empty</p></div>"
        
        rows = []
        for item in symbols:
            symbol = item.get("symbol", "N/A")
            current_price = item.get("current_price")
            added_at = item.get("added_at", "N/A")
            last_updated = item.get("last_updated")
            data_freshness = item.get("data_freshness_seconds")
            
            price_str = format_currency(current_price) if current_price else "Price unavailable"
            updated_str = last_updated if last_updated else "Not yet updated"
            freshness_str = f"{data_freshness}s ago" if data_freshness is not None else "N/A"
            
            row = f"""
            <tr>
                <td>{symbol}</td>
                <td>{price_str}</td>
                <td>{added_at}</td>
                <td>{updated_str}</td>
                <td>{freshness_str}</td>
            </tr>
            """
            rows.append(row)
        
        html = f"""
        <div class='watchlist-section'>
            <h2>Watchlist ({len(symbols)})</h2>
            <table class='watchlist-table'>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Current Price</th>
                        <th>Added At</th>
                        <th>Last Updated</th>
                        <th>Data Freshness</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """
        return html
    except Exception as e:
        logger.error(f"Error rendering watchlist section: {e}")
        return f"<div class='watchlist-section'><p>Error rendering watchlist: {str(e)}</p></div>"


def render_opportunities_section(opportunities_data: Optional[Dict[str, Any]]) -> str:
    """Render top opportunities section.
    
    Args:
        opportunities_data: Opportunities data
        
    Returns:
        Rendered HTML/text representation
    """
    if not opportunities_data:
        return "<div class='opportunities-section'><p>No opportunities available</p></div>"
    
    try:
        opportunities = opportunities_data.get("opportunities", [])
        
        if not opportunities:
            return "<div class='opportunities-section'><p>No opportunities available</p></div>"
        
        rows = []
        for opp in opportunities[:5]:  # Show top 5
            signal_id = opp.get("signal_id", "N/A")
            symbol = opp.get("symbol", "N/A")
            strategy = opp.get("strategy_type", "N/A")
            score = opp.get("score", 0)
            expected_profit = opp.get("expected_profit", 0)
            
            row = f"""
            <tr>
                <td><a href='/opportunities/{signal_id}'>{symbol}</a></td>
                <td>{strategy}</td>
                <td>{format_number(score, 1)}</td>
                <td>{format_currency(expected_profit)}</td>
            </tr>
            """
            rows.append(row)
        
        html = f"""
        <div class='opportunities-section'>
            <h2>Top Opportunities</h2>
            <table class='opportunities-table'>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Strategy</th>
                        <th>Score</th>
                        <th>Expected Profit</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """
        return html
    except Exception as e:
        logger.error(f"Error rendering opportunities section: {e}")
        return f"<div class='opportunities-section'><p>Error rendering opportunities: {str(e)}</p></div>"


def render_trades_section(trades_data: Optional[Dict[str, Any]]) -> str:
    """Render open trades section.
    
    Args:
        trades_data: Trades data
        
    Returns:
        Rendered HTML/text representation
    """
    if not trades_data:
        return "<div class='trades-section'><p>No open trades yet.</p></div>"
    
    try:
        trades = trades_data.get("trades", [])
        
        if not trades:
            return "<div class='trades-section'><p>No open trades yet.</p></div>"
        
        rows = []
        for trade in trades:
            symbol = trade.get("symbol", "N/A")
            strategy = trade.get("strategy_type", "N/A")
            entry_price = trade.get("entry_price")
            profit_loss = trade.get("profit_loss")
            
            row = f"""
            <tr>
                <td>{symbol}</td>
                <td>{strategy}</td>
                <td>{format_currency(entry_price)}</td>
                <td>{format_currency(profit_loss)}</td>
            </tr>
            """
            rows.append(row)
        
        html = f"""
        <div class='trades-section'>
            <h2>Open Trades ({len(trades)})</h2>
            <table class='trades-table'>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Strategy</th>
                        <th>Entry Price</th>
                        <th>P/L</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """
        return html
    except Exception as e:
        logger.error(f"Error rendering trades section: {e}")
        return f"<div class='trades-section'><p>Error rendering trades: {str(e)}</p></div>"


def render_news_section(news_data: Optional[Dict[str, Any]]) -> str:
    """Render recent news section.
    
    Args:
        news_data: News data
        
    Returns:
        Rendered HTML/text representation
    """
    if not news_data:
        return "<div class='news-section'><p>No recent news.</p></div>"
    
    try:
        articles = news_data.get("articles", [])
        
        if not articles:
            return "<div class='news-section'><p>No recent news.</p></div>"
        
        items = []
        for article in articles[:5]:  # Show top 5
            title = article.get("title", "N/A")
            source = article.get("source", "N/A")
            published_at = article.get("published_at", "N/A")
            url = article.get("url", "#")
            
            item = f"""
            <div class='news-item'>
                <a href='{url}' target='_blank'>{title}</a>
                <p class='news-meta'>{source} - {published_at}</p>
            </div>
            """
            items.append(item)
        
        html = f"""
        <div class='news-section'>
            <h2>Recent News</h2>
            {''.join(items)}
        </div>
        """
        return html
    except Exception as e:
        logger.error(f"Error rendering news section: {e}")
        return f"<div class='news-section'><p>Error rendering news: {str(e)}</p></div>"


def render_risk_settings_section(risk_settings_data: Optional[Dict[str, Any]]) -> str:
    """Render risk settings section.
    
    Args:
        risk_settings_data: Risk settings data
        
    Returns:
        Rendered HTML/text representation
    """
    if not risk_settings_data:
        return "<div class='risk-settings-section'><p>No risk settings available</p></div>"
    
    try:
        risk_level = risk_settings_data.get("risk_level", "N/A")
        paper_trading = risk_settings_data.get("paper_trading_enabled", False)
        live_trading = risk_settings_data.get("live_trading_enabled", False)
        live_approved = risk_settings_data.get("live_trading_approved", False)
        
        html = f"""
        <div class='risk-settings-section'>
            <h2>Risk Settings</h2>
            <div class='risk-settings-cards'>
                <div class='card'>
                    <label>Risk Level</label>
                    <value>{risk_level.upper()}</value>
                </div>
                <div class='card'>
                    <label>Paper Trading</label>
                    <value>{'Enabled' if paper_trading else 'Disabled'}</value>
                </div>
                <div class='card'>
                    <label>Live Trading</label>
                    <value>{'Enabled' if live_trading else 'Disabled'}</value>
                </div>
                <div class='card'>
                    <label>Live Trading Approved</label>
                    <value>{'Yes' if live_approved else 'No'}</value>
                </div>
            </div>
        </div>
        """
        return html
    except Exception as e:
        logger.error(f"Error rendering risk settings section: {e}")
        return f"<div class='risk-settings-section'><p>Error rendering risk settings: {str(e)}</p></div>"


def render_dashboard(dashboard_data: Optional[Dict[str, Any]]) -> str:
    """Render complete dashboard.
    
    Args:
        dashboard_data: Full dashboard data
        
    Returns:
        Rendered HTML/text representation
    """
    if not dashboard_data:
        return "<div class='dashboard'><p>No dashboard data available</p></div>"
    
    try:
        timestamp = dashboard_data.get("timestamp", "N/A")
        
        portfolio_section = render_portfolio_section(dashboard_data.get("portfolio_summary"))
        watchlist_section = render_watchlist_section(dashboard_data.get("watchlist"))
        opportunities_section = render_opportunities_section({"opportunities": dashboard_data.get("top_opportunities", [])})
        trades_section = render_trades_section({"trades": dashboard_data.get("open_trades", [])})
        news_section = render_news_section({"articles": dashboard_data.get("recent_news", [])})
        risk_section = render_risk_settings_section(dashboard_data.get("risk_settings"))
        
        html = f"""
        <div class='dashboard'>
            <div class='dashboard-header'>
                <h1>Dashboard</h1>
                <p class='timestamp'>Last updated: {timestamp}</p>
            </div>
            {portfolio_section}
            {watchlist_section}
            {opportunities_section}
            {trades_section}
            {news_section}
            {risk_section}
        </div>
        """
        return html
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        return f"<div class='dashboard'><p>Error rendering dashboard: {str(e)}</p></div>"
