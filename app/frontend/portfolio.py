"""Portfolio page for Streamlit frontend.

Displays user's open and closed trades with detailed P/L breakdowns.
For covered calls, shows separate stock P/L, option P/L, premium captured %,
total return %, break-even, and maximum profit.
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


def render_covered_call_details(trade: Dict) -> None:
    """Render detailed breakdown for a covered call trade.
    
    Shows:
    - Underlying stock details (entry price, current price, quantity, stock P/L)
    - Short call option details (strike, expiration, premium, option P/L, premium captured %)
    - Combined position metrics (total P/L, total return %, break-even, max profit)
    """
    st.markdown("---")
    st.markdown(f"### {trade.get('symbol', 'N/A')} Covered Call Details")
    
    # Underlying Stock Section
    st.markdown("#### Underlying Stock")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        shares = trade.get('underlying_quantity', 100)
        st.metric("Shares", f"{shares}")
    
    with col2:
        entry_price = trade.get('underlying_entry_price')
        st.metric("Stock Entry Price", format_currency(entry_price))
    
    with col3:
        current_price = trade.get('underlying_current_price')
        st.metric("Current Stock Price", format_currency(current_price))
    
    # Stock P/L
    stock_pnl = trade.get('stock_pnl')
    if stock_pnl is not None:
        st.markdown(f"**Stock P/L:** :{'green' if stock_pnl >= 0 else 'red'}[{format_currency(stock_pnl)}]")
    
    # Short Call Option Section
    st.markdown("#### Short Call Option")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        strike = trade.get('strike_price')
        st.metric("Strike", format_currency(strike))
    
    with col2:
        expiration = trade.get('expiration_date', 'N/A')
        st.metric("Expiration", expiration)
    
    with col3:
        premium = trade.get('premium_received')
        st.metric("Premium Received", format_currency(premium))
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        entry_option_price = trade.get('entry_price')
        st.metric("Entry Option Price", format_currency(entry_option_price))
    
    with col2:
        current_option_price = trade.get('current_price')
        st.metric("Current Option Price", format_currency(current_option_price))
    
    with col3:
        option_pnl = trade.get('option_pnl')
        if option_pnl is not None:
            st.metric("Option P/L", format_currency(option_pnl), 
                     delta_color="normal" if option_pnl >= 0 else "inverse")
    
    # Premium Captured %
    premium_captured_pct = trade.get('premium_captured_pct')
    if premium_captured_pct is not None:
        st.markdown(f"**Premium Captured:** {format_percentage(premium_captured_pct)}")
    
    # Combined Position Section
    st.markdown("#### Combined Position")
    col1, col2 = st.columns(2)
    
    with col1:
        total_pnl = trade.get('pnl')
        if total_pnl is not None:
            st.metric("Total Position P/L", format_currency(total_pnl),
                     delta_color="normal" if total_pnl >= 0 else "inverse")
    
    with col2:
        total_return_pct = trade.get('total_return_pct')
        if total_return_pct is not None:
            st.metric("Total Return", format_percentage(total_return_pct),
                     delta_color="normal" if total_return_pct >= 0 else "inverse")
    
    col1, col2 = st.columns(2)
    
    with col1:
        break_even = trade.get('break_even')
        st.metric("Break-even", format_currency(break_even))
    
    with col2:
        max_profit = trade.get('max_profit')
        st.metric("Maximum Profit", format_currency(max_profit))
    
    st.markdown("---")


def render_trade_row(trade: Dict, show_details: bool = False) -> None:
    """Render a single trade row with optional expandable details.
    
    For covered calls, displays combined P/L prominently with option to expand
    and see detailed breakdown of stock P/L and option P/L components.
    """
    strategy = trade.get('strategy_type', 'Unknown')
    symbol = trade.get('symbol', 'N/A')
    status = trade.get('status', 'unknown')
    
    # Main trade info
    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
    
    with col1:
        st.write(f"**{symbol}**")
        st.caption(strategy.replace('_', ' ').title())
    
    with col2:
        st.write(f"Status: {status.title()}")
        opened_at = trade.get('opened_at', 'N/A')
        if opened_at != 'N/A':
            try:
                opened_dt = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
                st.caption(f"Opened: {opened_dt.strftime('%Y-%m-%d')}")
            except:
                st.caption(f"Opened: {opened_at}")
    
    with col3:
        # For covered calls, show combined P/L prominently
        total_pnl = trade.get('pnl')
        pnl_pct = trade.get('pnl_pct')
        
        if total_pnl is not None:
            pnl_color = get_pnl_color(total_pnl)
            st.markdown(f"**Total P/L:** :{pnl_color}[{format_currency(total_pnl)}]")
            if pnl_pct is not None:
                st.caption(f"Return: {format_percentage(pnl_pct)}")
    
    with col4:
        # For covered calls, show component P/L summary
        if strategy == 'covered_call':
            option_pnl = trade.get('option_pnl')
            stock_pnl = trade.get('stock_pnl')
            
            if option_pnl is not None:
                opt_color = get_pnl_color(option_pnl)
                st.caption(f"Option: :{opt_color}[{format_currency(option_pnl)}]")
            
            if stock_pnl is not None:
                stock_color = get_pnl_color(stock_pnl)
                st.caption(f"Stock: :{stock_color}[{format_currency(stock_pnl)}]")
        else:
            # For other strategies, show entry/current prices
            entry_price = trade.get('entry_price')
            current_price = trade.get('current_price')
            if entry_price is not None:
                st.caption(f"Entry: {format_currency(entry_price)}")
            if current_price is not None:
                st.caption(f"Current: {format_currency(current_price)}")
    
    with col5:
        # Expandable details button for covered calls
        if strategy == 'covered_call':
            if st.button("📊", key=f"details_{trade.get('id', 'unknown')}"):
                render_covered_call_details(trade)


def render_portfolio_page():
    """Render the portfolio page showing all trades."""
    st.title("📊 Portfolio")
    
    # Initialize API client
    api_client = APIClient()
    
    # Fetch trades
    try:
        trades_response = api_client.get_trades()
        trades = trades_response.get('trades', [])
    except Exception as e:
        st.error(f"Failed to fetch trades: {str(e)}")
        trades = []
    
    if not trades:
        st.info("No trades found. Start by generating signals from the Dashboard.")
        return
    
    # Separate open and closed trades
    open_trades = [t for t in trades if t.get('status') == 'open']
    closed_trades = [t for t in trades if t.get('status') in ['closed', 'expired']]
    
    # Display open trades
    st.header("Open Positions")
    if open_trades:
        for trade in open_trades:
            render_trade_row(trade)
            st.markdown("---")
    else:
        st.info("No open positions.")
    
    # Display closed trades
    st.header("Closed Positions")
    if closed_trades:
        for trade in closed_trades:
            render_trade_row(trade)
            st.markdown("---")
    else:
        st.info("No closed positions.")
    
    # Summary statistics
    st.header("Portfolio Summary")
    
    total_pnl = sum(t.get('pnl', 0) for t in open_trades if t.get('pnl') is not None)
    total_option_pnl = sum(t.get('option_pnl', 0) for t in open_trades 
                           if t.get('strategy_type') == 'covered_call' and t.get('option_pnl') is not None)
    total_stock_pnl = sum(t.get('stock_pnl', 0) for t in open_trades 
                          if t.get('strategy_type') == 'covered_call' and t.get('stock_pnl') is not None)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        pnl_color = get_pnl_color(total_pnl)
        st.metric("Total Unrealized P/L", format_currency(total_pnl))
    
    with col2:
        if total_option_pnl != 0:
            opt_color = get_pnl_color(total_option_pnl)
            st.metric("Options P/L", format_currency(total_option_pnl))
    
    with col3:
        if total_stock_pnl != 0:
            stock_color = get_pnl_color(total_stock_pnl)
            st.metric("Underlying Stock P/L", format_currency(total_stock_pnl))
    
    # Realized P/L from closed trades
    realized_pnl = sum(t.get('pnl', 0) for t in closed_trades if t.get('pnl') is not None)
    if realized_pnl != 0:
        st.metric("Total Realized P/L", format_currency(realized_pnl))


if __name__ == "__main__":
    render_portfolio_page()
