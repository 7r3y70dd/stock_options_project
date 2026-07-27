"""Dashboard view for portfolio summary and signal generation.

Displays portfolio-level P/L with separate tracking of options P/L
and underlying stock P/L to prevent double-counting and misleading displays.
"""

import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime

from app.frontend.api_client import APIClient


def format_currency(value: Optional[float]) -> str:
    """Format a value as currency."""
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def format_percentage(value: Optional[float]) -> str:
    """Format a value as percentage."""
    if value is None:
        return "N/A"
    return f"{value:.2f}%"


def get_pnl_color(pnl: Optional[float]) -> str:
    """Return color for P/L display."""
    if pnl is None:
        return "gray"
    return "green" if pnl >= 0 else "red"


def calculate_portfolio_summary(trades: List[Dict]) -> Dict:
    """Calculate portfolio-level summary with separate option and stock P/L.
    
    For covered calls, tracks option_pnl and stock_pnl separately to avoid
    double-counting underlying shares that may be tracked elsewhere.
    
    Returns:
        Dict with keys:
        - total_pnl: Combined unrealized P/L
        - options_pnl: P/L from all option positions
        - stock_pnl: P/L from underlying stock in covered calls
        - open_trades: Number of open trades
        - total_capital_at_risk: Total capital deployed
    """
    summary = {
        "total_pnl": 0.0,
        "options_pnl": 0.0,
        "stock_pnl": 0.0,
        "open_trades": 0,
        "total_capital_at_risk": 0.0,
    }
    
    for trade in trades:
        status = trade.get("status", "").lower()
        
        # Only include open trades in unrealized P/L
        if status != "open":
            continue
        
        summary["open_trades"] += 1
        
        strategy = trade.get("strategy_type", "")
        
        if strategy == "covered_call":
            # For covered calls, track option and stock P/L separately
            option_pnl = trade.get("option_pnl", 0.0)
            stock_pnl = trade.get("stock_pnl", 0.0)
            total_pnl = trade.get("pnl", 0.0)
            
            summary["options_pnl"] += option_pnl
            summary["stock_pnl"] += stock_pnl
            summary["total_pnl"] += total_pnl
            
            # Capital at risk: stock value minus premium received
            underlying_entry = trade.get("underlying_entry_price", 0.0)
            underlying_qty = trade.get("underlying_quantity", 100)
            premium = trade.get("premium_received", 0.0)
            
            capital = (underlying_entry * underlying_qty) - premium
            summary["total_capital_at_risk"] += capital
        
        elif strategy == "cash_secured_put":
            # Cash-secured puts: only option P/L (no stock until assignment)
            option_pnl = trade.get("pnl", 0.0)
            summary["options_pnl"] += option_pnl
            summary["total_pnl"] += option_pnl
            
            # Capital at risk: strike price * 100 (cash secured)
            strike = trade.get("strike_price", 0.0)
            quantity = trade.get("quantity", 1)
            capital = strike * 100 * quantity
            summary["total_capital_at_risk"] += capital
        
        else:
            # Other strategies: use total P/L
            pnl = trade.get("pnl", 0.0)
            summary["options_pnl"] += pnl
            summary["total_pnl"] += pnl
            
            # Estimate capital at risk from max_loss if available
            max_loss = trade.get("max_loss", 0.0)
            summary["total_capital_at_risk"] += abs(max_loss)
    
    return summary


def display_portfolio_summary(summary: Dict) -> None:
    """Display portfolio summary metrics.
    
    Shows:
    - Total unrealized P/L
    - Options P/L (separate)
    - Underlying stock P/L (separate)
    - Number of open trades
    - Total return %
    """
    st.markdown("### Portfolio Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_pnl = summary.get("total_pnl", 0.0)
        pnl_color = get_pnl_color(total_pnl)
        st.markdown(
            f"**Total Unrealized P/L**<br>"
            f"<span style='color:{pnl_color}; font-size:24px; font-weight:bold;'>{format_currency(total_pnl)}</span>",
            unsafe_allow_html=True
        )
    
    with col2:
        open_trades = summary.get("open_trades", 0)
        st.markdown(
            f"**Open Trades**<br>"
            f"<span style='font-size:24px; font-weight:bold;'>{open_trades}</span>",
            unsafe_allow_html=True
        )
    
    with col3:
        capital = summary.get("total_capital_at_risk", 0.0)
        st.markdown(
            f"**Capital at Risk**<br>"
            f"<span style='font-size:24px; font-weight:bold;'>{format_currency(capital)}</span>",
            unsafe_allow_html=True
        )
    
    with col4:
        if capital > 0:
            total_return_pct = (total_pnl / capital) * 100
            return_color = get_pnl_color(total_pnl)
            st.markdown(
                f"**Total Return**<br>"
                f"<span style='color:{return_color}; font-size:24px; font-weight:bold;'>{format_percentage(total_return_pct)}</span>",
                unsafe_allow_html=True
            )
    
    st.markdown("---")
    
    # Detailed P/L breakdown
    st.markdown("#### P/L Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        options_pnl = summary.get("options_pnl", 0.0)
        options_color = get_pnl_color(options_pnl)
        st.markdown(
            f"**Options P/L**<br>"
            f"<span style='color:{options_color}; font-size:20px; font-weight:bold;'>{format_currency(options_pnl)}</span>",
            unsafe_allow_html=True
        )
        st.caption("P/L from all option positions")
    
    with col2:
        stock_pnl = summary.get("stock_pnl", 0.0)
        stock_color = get_pnl_color(stock_pnl)
        st.markdown(
            f"**Underlying Stock P/L**<br>"
            f"<span style='color:{stock_color}; font-size:20px; font-weight:bold;'>{format_currency(stock_pnl)}</span>",
            unsafe_allow_html=True
        )
        st.caption("P/L from stock in covered calls")
    
    # Warning if profitable options are hiding stock losses
    if options_pnl > 0 and stock_pnl < 0 and abs(stock_pnl) > options_pnl:
        st.warning(
            f"⚠️ Note: While options show a profit of {format_currency(options_pnl)}, "
            f"underlying stock losses of {format_currency(stock_pnl)} result in a net loss. "
            f"Consider reviewing covered call positions."
        )


def display_recent_signals(signals: List[Dict]) -> None:
    """Display recent trading signals."""
    st.markdown("### Recent Signals")
    
    if not signals:
        st.info("No signals generated yet. Add symbols to your watchlist and run signal generation.")
        return
    
    # Show top 5 most recent signals
    recent = signals[:5]
    
    for signal in recent:
        symbol = signal.get("symbol", "N/A")
        strategy = signal.get("strategy_type", "N/A").replace("_", " ").title()
        score = signal.get("score", 0.0)
        status = signal.get("status", "N/A").title()
        expected_profit = signal.get("expected_profit", 0.0)
        max_loss = signal.get("max_loss", 0.0)
        
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        
        with col1:
            st.write(f"**{symbol}**")
            st.caption(strategy)
        
        with col2:
            st.write(f"Score: {score:.2f}")
            st.caption(f"Status: {status}")
        
        with col3:
            st.write(f"Expected: {format_currency(expected_profit)}")
            st.caption(f"Max Loss: {format_currency(max_loss)}")
        
        with col4:
            if status.lower() == "pending":
                if st.button("Review", key=f"review_{signal.get('id')}"):
                    st.info("Signal review functionality coming soon.")
        
        st.markdown("---")


def render_dashboard() -> None:
    """Render the main dashboard view."""
    st.title("📈 Dashboard")
    
    api_client = APIClient()
    
    # Fetch data
    try:
        trades = api_client.get_trades()
        signals = api_client.get_signals()
    except Exception as e:
        st.error(f"Failed to load dashboard data: {e}")
        return
    
    # Calculate and display portfolio summary
    summary = calculate_portfolio_summary(trades)
    display_portfolio_summary(summary)
    
    st.markdown("---")
    
    # Display recent signals
    display_recent_signals(signals)
    
    st.markdown("---")
    
    # Quick actions
    st.markdown("### Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh Prices", use_container_width=True):
            try:
                api_client.refresh_trade_prices()
                st.success("Prices refreshed successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to refresh prices: {e}")
    
    with col2:
        if st.button("🎯 Generate Signals", use_container_width=True):
            try:
                api_client.generate_signals()
                st.success("Signals generated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to generate signals: {e}")
    
    with col3:
        if st.button("📊 View Portfolio", use_container_width=True):
            st.switch_page("pages/portfolio.py")


if __name__ == "__main__":
    render_dashboard()
