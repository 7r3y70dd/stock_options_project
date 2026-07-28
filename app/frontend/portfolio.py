"""Portfolio frontend component for displaying user trades and positions.

Displays active and closed trades with P/L calculations, strategy details,
and expandable views for covered calls showing combined position P/L.
"""

import streamlit as st
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


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


def render_covered_call_details(trade: Dict[str, Any]) -> None:
    """Render detailed breakdown for a covered call position.
    
    Shows:
    - Underlying stock P/L
    - Option P/L
    - Premium captured %
    - Total return %
    - Break-even price
    - Maximum profit
    """
    with st.expander("📊 Covered Call Details"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Underlying Stock**")
            shares = trade.get('underlying_quantity', 100)
            entry_price = trade.get('underlying_entry_price', 0.0)
            current_price = trade.get('underlying_current_price', 0.0)
            stock_pnl = trade.get('stock_pnl', 0.0)
            
            st.write(f"Shares: {shares}")
            st.write(f"Entry Price: ${entry_price:.2f}")
            st.write(f"Current Price: ${current_price:.2f}")
            st.markdown(f"Stock P/L: {format_currency(stock_pnl)}", unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("**Short Call Option**")
            strike = trade.get('strike_price', 0.0)
            expiration = trade.get('expiration_date', 'N/A')
            premium = trade.get('premium_received', 0.0)
            entry_option = trade.get('entry_price', 0.0)
            current_option = trade.get('current_price', 0.0)
            option_pnl = trade.get('option_pnl', 0.0)
            
            st.write(f"Strike: ${strike:.2f}")
            st.write(f"Expiration: {expiration}")
            st.write(f"Premium Received: ${premium:.2f}")
            st.write(f"Entry Option Price: ${entry_option:.2f}")
            st.write(f"Current Option Price: ${current_option:.2f}")
            st.markdown(f"Option P/L: {format_currency(option_pnl)}", unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Combined Position Metrics**")
            
            # Total P/L
            total_pnl = trade.get('unrealized_pnl', 0.0)
            st.markdown(f"**Total Position P/L:** {format_currency(total_pnl)}", unsafe_allow_html=True)
            
            # Premium captured %
            if premium > 0:
                premium_captured_pct = (option_pnl / premium) * 100
                st.markdown(f"Premium Captured: {format_percentage(premium_captured_pct)}", unsafe_allow_html=True)
            
            # Total return %
            total_return_pct = trade.get('unrealized_pnl_pct', 0.0)
            st.markdown(f"**Total Return:** {format_percentage(total_return_pct)}", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Break-even
            break_even = entry_price - (premium / shares) if shares > 0 else 0.0
            st.write(f"Break-even: ${break_even:.2f}")
            
            # Maximum profit
            if strike > 0 and entry_price > 0:
                stock_appreciation = (strike - entry_price) * shares
                max_profit = stock_appreciation + premium
                st.write(f"Maximum Profit: ${max_profit:.2f}")
            
            # Warning if option profitable but total losing
            if option_pnl > 0 and total_pnl < 0:
                st.warning("⚠️ Option is profitable but underlying stock losses exceed option gains. Overall position is losing money.")


def render_trade_row(trade: Dict[str, Any]) -> None:
    """Render a single trade row with strategy-specific formatting."""
    strategy = trade.get('strategy_type', 'unknown')
    symbol = trade.get('symbol', 'N/A')
    status = trade.get('status', 'unknown')
    
    # For covered calls, show combined P/L as primary metric
    if strategy.lower() == 'covered_call':
        total_pnl = trade.get('unrealized_pnl', 0.0)
        total_pnl_pct = trade.get('unrealized_pnl_pct', 0.0)
        stock_pnl = trade.get('stock_pnl', 0.0)
        option_pnl = trade.get('option_pnl', 0.0)
        
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
        
        with col1:
            st.write(f"**{symbol}**")
            st.caption(strategy.replace('_', ' ').title())
        
        with col2:
            st.write(f"Status: {status}")
        
        with col3:
            st.markdown(f"**Total P/L:** {format_currency(total_pnl)}", unsafe_allow_html=True)
            st.markdown(f"**Return:** {format_percentage(total_pnl_pct)}", unsafe_allow_html=True)
        
        with col4:
            st.caption(f"Stock: {format_currency(stock_pnl)}")
            st.caption(f"Option: {format_currency(option_pnl)}")
        
        with col5:
            if st.button("📋", key=f"details_{trade.get('id')}"):
                st.session_state[f"show_details_{trade.get('id')}"] = not st.session_state.get(f"show_details_{trade.get('id')}", False)
        
        # Show detailed breakdown if expanded
        if st.session_state.get(f"show_details_{trade.get('id')}", False):
            render_covered_call_details(trade)
    
    else:
        # Standard display for other strategies
        pnl = trade.get('unrealized_pnl', 0.0)
        pnl_pct = trade.get('unrealized_pnl_pct', 0.0)
        
        col1, col2, col3, col4 = st.columns([2, 2, 3, 1])
        
        with col1:
            st.write(f"**{symbol}**")
            st.caption(strategy.replace('_', ' ').title())
        
        with col2:
            st.write(f"Status: {status}")
        
        with col3:
            st.markdown(f"P/L: {format_currency(pnl)}", unsafe_allow_html=True)
            st.markdown(f"Return: {format_percentage(pnl_pct)}", unsafe_allow_html=True)
        
        with col4:
            if st.button("📋", key=f"details_{trade.get('id')}"):
                st.session_state[f"show_details_{trade.get('id')}"] = not st.session_state.get(f"show_details_{trade.get('id')}", False)


def render_portfolio(trades: List[Dict[str, Any]]) -> None:
    """Render the portfolio view with all trades.
    
    Args:
        trades: List of trade dictionaries from the API
    """
    st.title("📊 Portfolio")
    
    if not trades:
        st.info("No active trades. Start by generating signals from the dashboard.")
        return
    
    # Separate open and closed trades
    open_trades = [t for t in trades if t.get('status') == 'open']
    closed_trades = [t for t in trades if t.get('status') == 'closed']
    
    # Display open trades
    st.header(f"Open Positions ({len(open_trades)})")
    
    if open_trades:
        for trade in open_trades:
            render_trade_row(trade)
            st.markdown("---")
    else:
        st.info("No open positions.")
    
    # Display closed trades
    if closed_trades:
        st.header(f"Closed Positions ({len(closed_trades)})")
        
        with st.expander("Show Closed Trades"):
            for trade in closed_trades:
                render_trade_row(trade)
                st.markdown("---")
