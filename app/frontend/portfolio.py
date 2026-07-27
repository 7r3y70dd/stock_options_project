"""Portfolio view for displaying user trades and positions.

Displays active and closed trades with detailed P/L breakdowns,
especially for covered calls showing separate stock and option P/L.
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


def display_covered_call_details(trade: Dict) -> None:
    """Display detailed breakdown for a covered call position.
    
    Shows:
    - Underlying stock P/L
    - Option P/L
    - Premium captured %
    - Total position P/L
    - Total return %
    - Break-even price
    - Maximum profit
    """
    st.markdown("### Covered Call Details")
    
    # Underlying section
    st.markdown("#### Underlying Stock")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        shares = trade.get("underlying_quantity", 100)
        st.metric("Shares", f"{shares}")
    
    with col2:
        entry_price = trade.get("underlying_entry_price")
        st.metric("Entry Price", format_currency(entry_price))
    
    with col3:
        current_price = trade.get("underlying_current_price")
        st.metric("Current Price", format_currency(current_price))
    
    # Stock P/L
    stock_pnl = trade.get("stock_pnl", 0.0)
    st.metric(
        "Stock P/L",
        format_currency(stock_pnl),
        delta=format_currency(stock_pnl),
        delta_color="normal"
    )
    
    st.markdown("---")
    
    # Option section
    st.markdown("#### Short Call Option")
    col1, col2 = st.columns(2)
    
    with col1:
        strike = trade.get("strike_price")
        st.metric("Strike", format_currency(strike))
        
        entry_option_price = trade.get("entry_price")
        st.metric("Entry Option Price", format_currency(entry_option_price))
    
    with col2:
        expiration = trade.get("expiration_date", "N/A")
        st.metric("Expiration", expiration)
        
        current_option_price = trade.get("current_price")
        st.metric("Current Option Price", format_currency(current_option_price))
    
    # Premium and option P/L
    col1, col2 = st.columns(2)
    
    with col1:
        premium_received = trade.get("premium_received", 0.0)
        st.metric("Premium Received", format_currency(premium_received))
    
    with col2:
        option_pnl = trade.get("option_pnl", 0.0)
        st.metric(
            "Option P/L",
            format_currency(option_pnl),
            delta=format_currency(option_pnl),
            delta_color="normal"
        )
    
    # Premium captured percentage
    if premium_received and premium_received > 0:
        premium_captured_pct = (option_pnl / premium_received) * 100
        st.metric("Premium Captured %", format_percentage(premium_captured_pct))
    
    st.markdown("---")
    
    # Combined position section
    st.markdown("#### Combined Position")
    
    total_pnl = trade.get("pnl", 0.0)
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Total Position P/L",
            format_currency(total_pnl),
            delta=format_currency(total_pnl),
            delta_color="normal"
        )
    
    with col2:
        # Calculate total return %
        if entry_price and shares:
            net_capital = (entry_price * shares) - premium_received
            if net_capital > 0:
                total_return_pct = (total_pnl / net_capital) * 100
                st.metric("Total Return %", format_percentage(total_return_pct))
    
    # Break-even and max profit
    col1, col2 = st.columns(2)
    
    with col1:
        if entry_price and entry_option_price:
            break_even = entry_price - entry_option_price
            st.metric("Break-even", format_currency(break_even))
    
    with col2:
        if entry_price and strike and entry_option_price and shares:
            stock_appreciation = (strike - entry_price) * shares
            max_profit = stock_appreciation + premium_received
            st.metric("Maximum Profit", format_currency(max_profit))


def display_trade_row(trade: Dict) -> None:
    """Display a single trade row in the main table.
    
    For covered calls, shows combined P/L with expandable details.
    """
    symbol = trade.get("symbol", "N/A")
    strategy = trade.get("strategy_type", "N/A")
    status = trade.get("status", "N/A")
    
    # Main columns
    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
    
    with col1:
        st.write(f"**{symbol}**")
    
    with col2:
        st.write(strategy.replace("_", " ").title())
    
    with col3:
        st.write(status.title())
    
    with col4:
        # For covered calls, show combined P/L
        if strategy == "covered_call":
            total_pnl = trade.get("pnl", 0.0)
            option_pnl = trade.get("option_pnl", 0.0)
            stock_pnl = trade.get("stock_pnl", 0.0)
            
            pnl_color = get_pnl_color(total_pnl)
            st.markdown(
                f"<span style='color:{pnl_color}; font-weight:bold;'>{format_currency(total_pnl)}</span>",
                unsafe_allow_html=True
            )
            st.caption(f"Option: {format_currency(option_pnl)} | Stock: {format_currency(stock_pnl)}")
        else:
            pnl = trade.get("pnl", 0.0)
            pnl_color = get_pnl_color(pnl)
            st.markdown(
                f"<span style='color:{pnl_color}; font-weight:bold;'>{format_currency(pnl)}</span>",
                unsafe_allow_html=True
            )
    
    with col5:
        if strategy == "covered_call":
            if st.button("Details", key=f"details_{trade.get('id')}"):
                with st.expander(f"{symbol} Covered Call Details", expanded=True):
                    display_covered_call_details(trade)


def render_portfolio() -> None:
    """Render the portfolio view with all trades."""
    st.title("📊 Portfolio")
    
    api_client = APIClient()
    
    # Fetch trades
    try:
        trades = api_client.get_trades()
    except Exception as e:
        st.error(f"Failed to load trades: {e}")
        return
    
    if not trades:
        st.info("No trades found. Start by generating signals from the dashboard.")
        return
    
    # Filter controls
    col1, col2 = st.columns(2)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "Open", "Closed", "Pending"],
            index=0
        )
    
    with col2:
        strategy_filter = st.selectbox(
            "Strategy",
            ["All", "Covered Call", "Cash Secured Put", "Credit Spread", "Debit Spread"],
            index=0
        )
    
    # Apply filters
    filtered_trades = trades
    
    if status_filter != "All":
        filtered_trades = [
            t for t in filtered_trades
            if t.get("status", "").lower() == status_filter.lower()
        ]
    
    if strategy_filter != "All":
        strategy_key = strategy_filter.lower().replace(" ", "_")
        filtered_trades = [
            t for t in filtered_trades
            if t.get("strategy_type", "") == strategy_key
        ]
    
    # Display trades table
    st.markdown("### Active Trades")
    
    if not filtered_trades:
        st.info("No trades match the selected filters.")
        return
    
    # Table header
    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
    
    with col1:
        st.markdown("**Symbol**")
    with col2:
        st.markdown("**Strategy**")
    with col3:
        st.markdown("**Status**")
    with col4:
        st.markdown("**P/L**")
    with col5:
        st.markdown("**Actions**")
    
    st.markdown("---")
    
    # Display each trade
    for trade in filtered_trades:
        display_trade_row(trade)
        st.markdown("---")


if __name__ == "__main__":
    render_portfolio()
