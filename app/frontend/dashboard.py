"""Dashboard page for Streamlit frontend.

Displays portfolio summary, recent signals, and market overview.
For covered calls, shows portfolio-level P/L with clear separation between
options P/L and underlying stock P/L to prevent misleading displays.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

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


def get_pnl_color(value: Optional[float]) -> str:
    """Get color for P/L display (green for positive, red for negative)."""
    if value is None:
        return "gray"
    return "green" if value >= 0 else "red"


def render_portfolio_summary(api_client: APIClient):
    """Render portfolio summary with detailed P/L breakdown.
    
    For covered calls, displays:
    - Total Unrealized P/L (combined)
    - Options P/L (separate)
    - Underlying Stock P/L (separate)
    
    This prevents profitable option premiums from hiding losses in underlying shares.
    """
    st.header("Portfolio Summary")
    
    try:
        # Fetch portfolio summary
        summary = api_client.get_portfolio_summary()
        
        # Fetch trades for detailed breakdown
        trades_response = api_client.get_trades()
        trades = trades_response.get('trades', [])
        open_trades = [t for t in trades if t.get('status') == 'open']
        
        # Calculate total P/L
        total_pnl = summary.get('total_pnl', 0.0)
        
        # Calculate separate option and stock P/L for covered calls
        total_option_pnl = 0.0
        total_stock_pnl = 0.0
        other_pnl = 0.0
        
        for trade in open_trades:
            strategy = trade.get('strategy_type', '')
            if strategy == 'covered_call':
                # For covered calls, separate option and stock P/L
                option_pnl = trade.get('option_pnl', 0.0)
                stock_pnl = trade.get('stock_pnl', 0.0)
                if option_pnl is not None:
                    total_option_pnl += option_pnl
                if stock_pnl is not None:
                    total_stock_pnl += stock_pnl
            else:
                # For other strategies, add to other P/L
                trade_pnl = trade.get('pnl', 0.0)
                if trade_pnl is not None:
                    other_pnl += trade_pnl
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            portfolio_value = summary.get('portfolio_value', 0.0)
            st.metric("Portfolio Value", format_currency(portfolio_value))
        
        with col2:
            cash_balance = summary.get('cash_balance', 0.0)
            st.metric("Cash Balance", format_currency(cash_balance))
        
        with col3:
            total_return_pct = summary.get('total_return_pct', 0.0)
            st.metric("Total Return", format_percentage(total_return_pct))
        
        with col4:
            open_positions = len(open_trades)
            st.metric("Open Positions", f"{open_positions}")
        
        # Detailed P/L breakdown
        st.subheader("Unrealized P/L Breakdown")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            pnl_color = get_pnl_color(total_pnl)
            st.markdown(f"### Total Unrealized P/L")
            st.markdown(f"## :{pnl_color}[{format_currency(total_pnl)}]")
        
        # Show breakdown if there are covered calls
        if total_option_pnl != 0 or total_stock_pnl != 0:
            with col2:
                opt_color = get_pnl_color(total_option_pnl)
                st.markdown(f"### Options P/L")
                st.markdown(f"## :{opt_color}[{format_currency(total_option_pnl)}]")
                st.caption("From covered call premiums")
            
            with col3:
                stock_color = get_pnl_color(total_stock_pnl)
                st.markdown(f"### Underlying Stock P/L")
                st.markdown(f"## :{stock_color}[{format_currency(total_stock_pnl)}]")
                st.caption("From covered call stock holdings")
            
            # Show warning if option P/L is positive but total is negative
            if total_option_pnl > 0 and total_pnl < 0:
                st.warning(
                    "⚠️ Note: While option premiums show a profit, the underlying stock losses "
                    "result in an overall negative position. Consider your exit strategy."
                )
        
        # Show other strategies P/L if present
        if other_pnl != 0:
            st.markdown(f"**Other Strategies P/L:** :{get_pnl_color(other_pnl)}[{format_currency(other_pnl)}]")
        
        # Risk metrics
        st.subheader("Risk Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            buying_power = summary.get('buying_power', 0.0)
            st.metric("Buying Power", format_currency(buying_power))
        
        with col2:
            margin_used = summary.get('margin_used', 0.0)
            st.metric("Margin Used", format_currency(margin_used))
        
        with col3:
            max_loss = summary.get('max_loss', 0.0)
            st.metric("Max Loss (Open Positions)", format_currency(max_loss))
        
    except Exception as e:
        st.error(f"Failed to fetch portfolio summary: {str(e)}")


def render_recent_signals(api_client: APIClient):
    """Render recent trading signals."""
    st.header("Recent Signals")
    
    try:
        signals_response = api_client.get_signals(limit=5)
        signals = signals_response.get('signals', [])
        
        if not signals:
            st.info("No recent signals. Generate new signals to see recommendations.")
            return
        
        for signal in signals:
            with st.expander(f"{signal.get('symbol', 'N/A')} - {signal.get('strategy_type', 'Unknown').replace('_', ' ').title()}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    score = signal.get('score', 0.0)
                    st.metric("Score", f"{score:.2f}")
                
                with col2:
                    expected_profit = signal.get('expected_profit', 0.0)
                    st.metric("Expected Profit", format_currency(expected_profit))
                
                with col3:
                    max_loss = signal.get('max_loss', 0.0)
                    st.metric("Max Loss", format_currency(max_loss))
                
                reason = signal.get('reason', 'No reason provided')
                st.write(f"**Reason:** {reason}")
                
                status = signal.get('status', 'pending')
                st.write(f"**Status:** {status.title()}")
                
                # Action buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Approve", key=f"approve_{signal.get('id')}"):
                        try:
                            api_client.update_signal_status(signal.get('id'), 'approved')
                            st.success("Signal approved!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to approve signal: {str(e)}")
                
                with col2:
                    if st.button("❌ Reject", key=f"reject_{signal.get('id')}"):
                        try:
                            api_client.update_signal_status(signal.get('id'), 'rejected')
                            st.success("Signal rejected!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to reject signal: {str(e)}")
    
    except Exception as e:
        st.error(f"Failed to fetch signals: {str(e)}")


def render_market_overview(api_client: APIClient):
    """Render market overview with key indices."""
    st.header("Market Overview")
    
    try:
        # Fetch market data for major indices
        indices = ['SPY', 'QQQ', 'IWM']  # S&P 500, Nasdaq, Russell 2000
        
        cols = st.columns(len(indices))
        
        for idx, symbol in enumerate(indices):
            with cols[idx]:
                try:
                    quote = api_client.get_quote(symbol)
                    price = quote.get('price', 0.0)
                    change = quote.get('change', 0.0)
                    change_pct = quote.get('change_pct', 0.0)
                    
                    st.metric(
                        symbol,
                        format_currency(price),
                        f"{change:+.2f} ({change_pct:+.2f}%)"
                    )
                except:
                    st.metric(symbol, "N/A")
        
    except Exception as e:
        st.error(f"Failed to fetch market data: {str(e)}")


def render_dashboard():
    """Render the main dashboard page."""
    st.title("📈 Options Trading Dashboard")
    
    # Initialize API client
    api_client = APIClient()
    
    # Render sections
    render_portfolio_summary(api_client)
    st.markdown("---")
    
    render_recent_signals(api_client)
    st.markdown("---")
    
    render_market_overview(api_client)
    
    # Quick actions
    st.header("Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Generate New Signals", use_container_width=True):
            try:
                api_client.generate_signals()
                st.success("Signal generation started! Check back in a few moments.")
            except Exception as e:
                st.error(f"Failed to generate signals: {str(e)}")
    
    with col2:
        if st.button("📊 View Portfolio", use_container_width=True):
            st.switch_page("pages/portfolio.py")
    
    with col3:
        if st.button("👁️ Manage Watchlist", use_container_width=True):
            st.switch_page("pages/watchlist.py")


if __name__ == "__main__":
    render_dashboard()
