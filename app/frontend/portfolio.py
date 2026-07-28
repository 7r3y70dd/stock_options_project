"""Portfolio view for displaying user trades and positions.

Displays active and closed trades with P/L calculations, strategy details,
and expandable information. For covered calls, shows combined P/L including
both underlying stock and option components.
"""

import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime


def format_currency(value: float) -> str:
    """Format a float as currency with color."""
    if value >= 0:
        return f"<span style='color: green;'>+${value:,.2f}</span>"
    else:
        return f"<span style='color: red;'>-${abs(value):,.2f}</span>"


def format_percentage(value: float) -> str:
    """Format a float as percentage with color."""
    if value >= 0:
        return f"<span style='color: green;'>+{value:.2f}%</span>"
    else:
        return f"<span style='color: red;'>{value:.2f}%</span>"


def render_covered_call_details(trade: Dict) -> None:
    """Render detailed breakdown for covered call positions.
    
    Shows:
    - Underlying stock P/L
    - Option P/L
    - Premium captured %
    - Total position P/L
    - Total return %
    - Break-even price
    - Maximum profit
    """
    # Extract trade details
    underlying_entry = trade.get('underlying_entry_price', 0.0)
    underlying_current = trade.get('underlying_current_price', 0.0)
    option_entry = trade.get('entry_price', 0.0)
    option_current = trade.get('current_price', 0.0)
    quantity = trade.get('quantity', 1)
    strike = trade.get('strike_price', 0.0)
    stock_pnl = trade.get('stock_pnl', 0.0)
    option_pnl = trade.get('option_pnl', 0.0)
    total_pnl = trade.get('pnl', 0.0)
    
    # Calculate metrics
    premium_received = option_entry * 100 * quantity
    premium_captured_pct = 0.0
    if premium_received > 0:
        premium_captured_pct = (option_pnl / premium_received) * 100
    
    # Total return % based on net capital at risk
    net_capital = (underlying_entry * 100 * quantity) - premium_received
    total_return_pct = 0.0
    if net_capital > 0:
        total_return_pct = (total_pnl / net_capital) * 100
    
    # Break-even
    break_even = underlying_entry - option_entry
    
    # Maximum profit
    stock_appreciation = (strike - underlying_entry) * 100 * quantity
    max_profit = stock_appreciation + premium_received
    
    # Display breakdown
    st.markdown("### Covered Call Position Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Underlying Stock**")
        st.markdown(f"Shares: {100 * quantity}")
        st.markdown(f"Entry Price: ${underlying_entry:.2f}")
        st.markdown(f"Current Price: ${underlying_current:.2f}")
        st.markdown(f"Stock P/L: {format_currency(stock_pnl)}", unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown("**Short Call Option**")
        st.markdown(f"Strike: ${strike:.2f}")
        st.markdown(f"Premium Received: ${premium_received:.2f}")
        st.markdown(f"Entry Option Price: ${option_entry:.2f}")
        st.markdown(f"Current Option Price: ${option_current:.2f}")
        st.markdown(f"Option P/L: {format_currency(option_pnl)}", unsafe_allow_html=True)
        st.markdown(f"Premium Captured: {format_percentage(premium_captured_pct)}", unsafe_allow_html=True)
    
    with col2:
        st.markdown("**Combined Position**")
        st.markdown(f"Total Position P/L: {format_currency(total_pnl)}", unsafe_allow_html=True)
        st.markdown(f"Total Return: {format_percentage(total_return_pct)}", unsafe_allow_html=True)
        st.markdown(f"Break-even: ${break_even:.2f}")
        st.markdown(f"Maximum Profit: ${max_profit:.2f}")
        
        # Warning if option is profitable but total position is losing
        if option_pnl > 0 and total_pnl < 0:
            st.warning(
                f"⚠️ While the option leg shows a profit of ${option_pnl:.2f}, "
                f"the underlying stock has declined by ${abs(stock_pnl):.2f}, "
                f"resulting in a net loss of ${abs(total_pnl):.2f}."
            )


def render_trade_row(trade: Dict, show_details: bool = False) -> None:
    """Render a single trade row with expandable details.
    
    For covered calls, displays combined P/L as primary metric with
    separate stock and option P/L components.
    """
    strategy_type = trade.get('strategy_type', 'Unknown')
    symbol = trade.get('symbol', 'N/A')
    status = trade.get('status', 'unknown')
    pnl = trade.get('pnl', 0.0)
    pnl_pct = trade.get('pnl_pct', 0.0)
    
    # For covered calls, extract component P/L
    is_covered_call = strategy_type.lower() == 'covered_call'
    stock_pnl = trade.get('stock_pnl', 0.0) if is_covered_call else None
    option_pnl = trade.get('option_pnl', 0.0) if is_covered_call else None
    
    # Display main row
    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
    
    with col1:
        st.markdown(f"**{symbol}**")
        st.caption(strategy_type.replace('_', ' ').title())
    
    with col2:
        st.markdown(f"Status: {status.title()}")
    
    with col3:
        if is_covered_call and stock_pnl is not None and option_pnl is not None:
            st.markdown(f"Stock P/L: {format_currency(stock_pnl)}", unsafe_allow_html=True)
            st.markdown(f"Option P/L: {format_currency(option_pnl)}", unsafe_allow_html=True)
        else:
            st.markdown(f"P/L: {format_currency(pnl)}", unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"**Total P/L: {format_currency(pnl)}**", unsafe_allow_html=True)
        st.markdown(f"Return: {format_percentage(pnl_pct)}", unsafe_allow_html=True)
    
    with col5:
        if is_covered_call:
            if st.button("Details", key=f"details_{trade.get('id', 0)}"):
                show_details = not show_details
    
    # Show expandable details for covered calls
    if show_details and is_covered_call:
        with st.expander("Covered Call Details", expanded=True):
            render_covered_call_details(trade)
    
    st.markdown("---")


def render_portfolio_view(trades: List[Dict]) -> None:
    """Render the main portfolio view with all trades.
    
    Args:
        trades: List of trade dictionaries with P/L calculations
    """
    st.title("Portfolio")
    
    if not trades:
        st.info("No trades to display. Start by generating signals from the dashboard.")
        return
    
    # Separate open and closed trades
    open_trades = [t for t in trades if t.get('status') == 'open']
    closed_trades = [t for t in trades if t.get('status') == 'closed']
    
    # Display open trades
    st.header(f"Open Positions ({len(open_trades)})")
    if open_trades:
        for trade in open_trades:
            render_trade_row(trade)
    else:
        st.info("No open positions.")
    
    # Display closed trades
    st.header(f"Closed Positions ({len(closed_trades)})")
    if closed_trades:
        for trade in closed_trades:
            render_trade_row(trade)
    else:
        st.info("No closed positions.")
