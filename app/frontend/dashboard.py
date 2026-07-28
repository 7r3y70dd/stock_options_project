"""Dashboard view for portfolio overview and key metrics.

Displays portfolio-level P/L with breakdown by strategy type,
separating options P/L from underlying stock P/L for covered calls.
"""

import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime, timedelta


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


def calculate_portfolio_metrics(trades: List[Dict], initial_value: float = 100000.0) -> Dict:
    """Calculate portfolio-level metrics with proper P/L breakdown.
    
    For covered calls, separates stock P/L from option P/L to prevent
    misleading displays where profitable options hide losing stocks.
    
    Args:
        trades: List of trade dictionaries
        initial_value: Initial portfolio value
    
    Returns:
        Dictionary with portfolio metrics including:
        - total_pnl: Combined P/L across all positions
        - options_pnl: P/L from option legs only
        - stock_pnl: P/L from underlying stock legs (covered calls)
        - other_pnl: P/L from non-covered-call strategies
        - current_value: Current portfolio value
        - return_pct: Overall return percentage
    """
    open_trades = [t for t in trades if t.get('status', 'open') == 'open']
    closed_trades = [t for t in trades if t.get('status', 'open') == 'closed']
    
    # Separate P/L by type
    options_pnl = 0.0
    stock_pnl = 0.0
    other_pnl = 0.0
    
    for trade in trades:
        strategy = trade.get('strategy_type', '')
        
        if strategy == 'covered_call':
            # For covered calls, track stock and option P/L separately
            options_pnl += trade.get('option_pnl', 0.0)
            stock_pnl += trade.get('stock_pnl', 0.0)
        else:
            # For other strategies, add to other_pnl
            other_pnl += trade.get('pnl', 0.0)
    
    total_pnl = options_pnl + stock_pnl + other_pnl
    current_value = initial_value + total_pnl
    return_pct = (total_pnl / initial_value) * 100 if initial_value > 0 else 0.0
    
    return {
        'total_pnl': total_pnl,
        'options_pnl': options_pnl,
        'stock_pnl': stock_pnl,
        'other_pnl': other_pnl,
        'current_value': current_value,
        'return_pct': return_pct,
        'open_count': len(open_trades),
        'closed_count': len(closed_trades),
        'total_count': len(trades)
    }


def render_pnl_breakdown(metrics: Dict) -> None:
    """Render detailed P/L breakdown showing options vs stock vs other.
    
    This prevents profitable option premiums from hiding losses in underlying shares.
    """
    st.markdown("### 📊 P/L Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Total Unrealized P/L**")
        st.markdown(f"<h2>{format_currency(metrics['total_pnl'])}</h2>", unsafe_allow_html=True)
        st.markdown(f"Return: {format_percentage(metrics['return_pct'])}", unsafe_allow_html=True)
    
    with col2:
        st.markdown("**Component Breakdown**")
        
        # Show breakdown
        if metrics['options_pnl'] != 0:
            st.markdown(f"Options P/L: {format_currency(metrics['options_pnl'])}", unsafe_allow_html=True)
        
        if metrics['stock_pnl'] != 0:
            st.markdown(f"Underlying Stock P/L: {format_currency(metrics['stock_pnl'])}", unsafe_allow_html=True)
        
        if metrics['other_pnl'] != 0:
            st.markdown(f"Other Strategies P/L: {format_currency(metrics['other_pnl'])}", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown(f"**Combined P/L: {format_currency(metrics['total_pnl'])}**", unsafe_allow_html=True)
    
    # Warning if options are profitable but stock is losing
    if metrics['options_pnl'] > 0 and metrics['stock_pnl'] < 0:
        net_covered_call_pnl = metrics['options_pnl'] + metrics['stock_pnl']
        if net_covered_call_pnl < 0:
            st.warning(
                f"⚠️ Covered call options show +${metrics['options_pnl']:.2f} profit, "
                f"but underlying stock losses of ${abs(metrics['stock_pnl']):.2f} result in "
                f"a net covered call loss of ${abs(net_covered_call_pnl):.2f}."
            )


def render_strategy_performance(trades: List[Dict]) -> None:
    """Render performance breakdown by strategy type."""
    st.markdown("### 📈 Strategy Performance")
    
    # Group trades by strategy
    strategy_stats = {}
    
    for trade in trades:
        strategy = trade.get('strategy_type', 'unknown')
        pnl = trade.get('pnl', 0.0)
        
        if strategy not in strategy_stats:
            strategy_stats[strategy] = {
                'count': 0,
                'total_pnl': 0.0,
                'wins': 0,
                'losses': 0
            }
        
        strategy_stats[strategy]['count'] += 1
        strategy_stats[strategy]['total_pnl'] += pnl
        
        if pnl > 0:
            strategy_stats[strategy]['wins'] += 1
        elif pnl < 0:
            strategy_stats[strategy]['losses'] += 1
    
    # Display strategy stats
    for strategy, stats in sorted(strategy_stats.items(), key=lambda x: x[1]['total_pnl'], reverse=True):
        with st.expander(f"{strategy.replace('_', ' ').title()} ({stats['count']} trades)"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total P/L", f"${stats['total_pnl']:,.2f}")
            
            with col2:
                win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
                st.metric("Win Rate", f"{win_rate:.1f}%")
            
            with col3:
                st.metric("Wins / Losses", f"{stats['wins']} / {stats['losses']}")


def render_recent_activity(trades: List[Dict], limit: int = 5) -> None:
    """Render recent trade activity."""
    st.markdown("### 🕐 Recent Activity")
    
    # Sort by entry date
    recent_trades = sorted(
        trades,
        key=lambda t: t.get('entry_date', ''),
        reverse=True
    )[:limit]
    
    if not recent_trades:
        st.info("No recent activity.")
        return
    
    for trade in recent_trades:
        symbol = trade.get('symbol', 'N/A')
        strategy = trade.get('strategy_type', 'N/A').replace('_', ' ').title()
        pnl = trade.get('pnl', 0.0)
        entry_date = trade.get('entry_date', 'N/A')
        status = trade.get('status', 'open')
        
        col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
        
        with col1:
            st.write(f"**{symbol}**")
        
        with col2:
            st.write(strategy)
        
        with col3:
            st.markdown(format_currency(pnl), unsafe_allow_html=True)
        
        with col4:
            st.write(entry_date)
        
        st.markdown("---")


def render_dashboard(trades: List[Dict], initial_value: float = 100000.0) -> None:
    """Render the main dashboard view.
    
    Args:
        trades: List of trade dictionaries
        initial_value: Initial portfolio value
    """
    st.title("📊 Dashboard")
    
    if not trades:
        st.info("No trades found. Start by generating signals and executing trades.")
        return
    
    # Calculate portfolio metrics
    metrics = calculate_portfolio_metrics(trades, initial_value)
    
    # Top-level metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Portfolio Value",
            f"${metrics['current_value']:,.2f}",
            delta=f"${metrics['total_pnl']:,.2f}"
        )
    
    with col2:
        st.metric(
            "Total Return",
            f"{metrics['return_pct']:.2f}%"
        )
    
    with col3:
        st.metric(
            "Open Positions",
            metrics['open_count']
        )
    
    with col4:
        st.metric(
            "Closed Positions",
            metrics['closed_count']
        )
    
    st.markdown("---")
    
    # P/L breakdown
    render_pnl_breakdown(metrics)
    
    st.markdown("---")
    
    # Strategy performance
    render_strategy_performance(trades)
    
    st.markdown("---")
    
    # Recent activity
    render_recent_activity(trades)
