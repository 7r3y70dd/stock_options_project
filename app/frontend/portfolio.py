"""Portfolio view for displaying user trades and positions.

Displays active and closed trades with detailed P/L breakdowns.
For covered calls, shows combined position P/L including both stock and option legs.
"""

import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime


def format_currency(value: float) -> str:
    """Format a value as currency with color."""
    if value >= 0:
        return f"<span style='color: green;'>+${value:,.2f}</span>"
    else:
        return f"<span style='color: red;'>-${abs(value):,.2f}</span>"


def format_percentage(value: float) -> str:
    """Format a percentage with color."""
    if value >= 0:
        return f"<span style='color: green;'>+{value:.2f}%</span>"
    else:
        return f"<span style='color: red;'>{value:.2f}%</span>"


def render_covered_call_details(trade: Dict) -> None:
    """Render detailed breakdown for a covered call position.
    
    Shows:
    - Underlying stock P/L
    - Option P/L
    - Premium captured %
    - Total position P/L
    - Total return %
    - Break-even price
    - Maximum profit
    """
    with st.expander("📊 Covered Call Details"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Underlying Stock**")
            underlying_qty = trade.get('underlying_quantity', 100)
            underlying_entry = trade.get('underlying_entry_price', 0.0)
            underlying_current = trade.get('underlying_current_price', 0.0)
            stock_pnl = trade.get('stock_pnl', 0.0)
            
            st.write(f"Shares: {underlying_qty}")
            st.write(f"Entry Price: ${underlying_entry:.2f}")
            st.write(f"Current Price: ${underlying_current:.2f}")
            st.markdown(f"Stock P/L: {format_currency(stock_pnl)}", unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("**Short Call Option**")
            strike = trade.get('strike_price', 0.0)
            expiration = trade.get('expiration_date', 'N/A')
            premium_received = trade.get('premium_received', 0.0)
            option_entry = trade.get('entry_price', 0.0)
            option_current = trade.get('current_price', 0.0)
            option_pnl = trade.get('option_pnl', 0.0)
            
            st.write(f"Strike: ${strike:.2f}")
            st.write(f"Expiration: {expiration}")
            st.write(f"Premium Received: ${premium_received:.2f}")
            st.write(f"Entry Option Price: ${option_entry:.2f}")
            st.write(f"Current Option Price: ${option_current:.2f}")
            st.markdown(f"Option P/L: {format_currency(option_pnl)}", unsafe_allow_html=True)
            
            # Premium captured percentage
            if premium_received > 0:
                premium_captured_pct = (option_pnl / premium_received) * 100
                st.markdown(f"Premium Captured: {format_percentage(premium_captured_pct)}", unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Combined Position**")
            total_pnl = trade.get('pnl', 0.0)
            st.markdown(f"Total Position P/L: {format_currency(total_pnl)}", unsafe_allow_html=True)
            
            # Total return percentage
            quantity = trade.get('quantity', 1)
            net_capital = (underlying_entry * underlying_qty * quantity) - premium_received
            if net_capital > 0:
                total_return_pct = (total_pnl / net_capital) * 100
                st.markdown(f"Total Return: {format_percentage(total_return_pct)}", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Break-even calculation
            premium_per_share = premium_received / (underlying_qty * quantity) if underlying_qty > 0 else 0
            break_even = underlying_entry - premium_per_share
            st.write(f"Break-even: ${break_even:.2f}")
            
            # Maximum profit calculation
            stock_appreciation = (strike - underlying_entry) * underlying_qty * quantity
            max_profit = stock_appreciation + premium_received
            st.write(f"Maximum Profit: ${max_profit:.2f}")
            
            # Additional metrics
            st.markdown("---")
            st.markdown("**Position Metrics**")
            days_to_exp = trade.get('days_to_expiration', 0)
            st.write(f"Days to Expiration: {days_to_exp}")
            
            # Show if cost basis is estimated
            if trade.get('cost_basis_estimated', False):
                st.warning("⚠️ Stock cost basis is estimated (using entry price)")


def render_trade_row(trade: Dict) -> None:
    """Render a single trade row with appropriate details based on strategy."""
    cols = st.columns([2, 2, 2, 2, 2, 2])
    
    symbol = trade.get('symbol', 'N/A')
    strategy = trade.get('strategy_type', 'N/A')
    status = trade.get('status', 'open')
    pnl = trade.get('pnl', 0.0)
    pnl_pct = trade.get('pnl_pct', 0.0)
    entry_date = trade.get('entry_date', 'N/A')
    
    with cols[0]:
        st.write(symbol)
    
    with cols[1]:
        st.write(strategy.replace('_', ' ').title())
    
    with cols[2]:
        badge_color = "green" if status == "open" else "gray"
        st.markdown(f"<span style='background-color: {badge_color}; color: white; padding: 2px 8px; border-radius: 4px;'>{status.upper()}</span>", unsafe_allow_html=True)
    
    with cols[3]:
        # For covered calls, show combined P/L as primary
        if strategy == 'covered_call':
            st.markdown(f"{format_currency(pnl)}", unsafe_allow_html=True)
            # Show breakdown in smaller text
            stock_pnl = trade.get('stock_pnl', 0.0)
            option_pnl = trade.get('option_pnl', 0.0)
            st.markdown(f"<small>Stock: {format_currency(stock_pnl)}<br>Option: {format_currency(option_pnl)}</small>", unsafe_allow_html=True)
        else:
            st.markdown(f"{format_currency(pnl)}", unsafe_allow_html=True)
    
    with cols[4]:
        st.markdown(f"{format_percentage(pnl_pct)}", unsafe_allow_html=True)
    
    with cols[5]:
        st.write(entry_date)
    
    # Show detailed breakdown for covered calls
    if strategy == 'covered_call':
        render_covered_call_details(trade)


def render_portfolio_view(trades: List[Dict]) -> None:
    """Render the portfolio view with all trades.
    
    Args:
        trades: List of trade dictionaries with P/L calculations
    """
    st.title("📊 Portfolio")
    
    if not trades:
        st.info("No trades found. Start by generating signals and executing trades.")
        return
    
    # Filter controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "Open", "Closed"],
            index=0
        )
    
    with col2:
        strategy_filter = st.selectbox(
            "Strategy",
            ["All"] + sorted(list(set(t.get('strategy_type', 'N/A') for t in trades))),
            index=0
        )
    
    with col3:
        sort_by = st.selectbox(
            "Sort By",
            ["Entry Date", "P/L", "P/L %"],
            index=0
        )
    
    # Apply filters
    filtered_trades = trades
    
    if status_filter != "All":
        filtered_trades = [t for t in filtered_trades if t.get('status', 'open').lower() == status_filter.lower()]
    
    if strategy_filter != "All":
        filtered_trades = [t for t in filtered_trades if t.get('strategy_type', 'N/A') == strategy_filter]
    
    # Sort trades
    if sort_by == "P/L":
        filtered_trades = sorted(filtered_trades, key=lambda t: t.get('pnl', 0.0), reverse=True)
    elif sort_by == "P/L %":
        filtered_trades = sorted(filtered_trades, key=lambda t: t.get('pnl_pct', 0.0), reverse=True)
    else:  # Entry Date
        filtered_trades = sorted(filtered_trades, key=lambda t: t.get('entry_date', ''), reverse=True)
    
    # Summary metrics
    st.markdown("### Summary")
    total_pnl = sum(t.get('pnl', 0.0) for t in filtered_trades)
    open_trades = [t for t in filtered_trades if t.get('status', 'open') == 'open']
    closed_trades = [t for t in filtered_trades if t.get('status', 'open') == 'closed']
    
    # Separate P/L by type for covered calls
    total_stock_pnl = sum(t.get('stock_pnl', 0.0) for t in filtered_trades if t.get('strategy_type') == 'covered_call')
    total_option_pnl = sum(t.get('option_pnl', 0.0) for t in filtered_trades if t.get('strategy_type') == 'covered_call')
    other_pnl = sum(t.get('pnl', 0.0) for t in filtered_trades if t.get('strategy_type') != 'covered_call')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total P/L", f"${total_pnl:,.2f}")
    
    with col2:
        st.metric("Open Positions", len(open_trades))
    
    with col3:
        st.metric("Closed Positions", len(closed_trades))
    
    with col4:
        win_rate = len([t for t in closed_trades if t.get('pnl', 0.0) > 0]) / len(closed_trades) * 100 if closed_trades else 0
        st.metric("Win Rate", f"{win_rate:.1f}%")
    
    # Show P/L breakdown for covered calls
    if total_stock_pnl != 0 or total_option_pnl != 0:
        st.markdown("---")
        st.markdown("**Covered Call P/L Breakdown**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"Stock P/L: {format_currency(total_stock_pnl)}", unsafe_allow_html=True)
        with col2:
            st.markdown(f"Option P/L: {format_currency(total_option_pnl)}", unsafe_allow_html=True)
        with col3:
            st.markdown(f"Other Strategies: {format_currency(other_pnl)}", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Trades table
    st.markdown("### Trades")
    
    # Header
    header_cols = st.columns([2, 2, 2, 2, 2, 2])
    with header_cols[0]:
        st.markdown("**Symbol**")
    with header_cols[1]:
        st.markdown("**Strategy**")
    with header_cols[2]:
        st.markdown("**Status**")
    with header_cols[3]:
        st.markdown("**P/L**")
    with header_cols[4]:
        st.markdown("**P/L %**")
    with header_cols[5]:
        st.markdown("**Entry Date**")
    
    st.markdown("---")
    
    # Render each trade
    for trade in filtered_trades:
        render_trade_row(trade)
        st.markdown("---")
