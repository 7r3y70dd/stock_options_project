"""Dashboard view for portfolio summary and signal generation.

Displays portfolio-level P/L with separate breakdowns for options P/L
and underlying stock P/L to prevent misleading displays where profitable
option premiums hide losses in underlying shares.
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


def calculate_portfolio_pnl_breakdown(trades: List[Dict]) -> Dict[str, float]:
    """Calculate portfolio P/L with separate options and stock components.
    
    Returns:
        Dictionary with:
        - total_pnl: Combined P/L
        - options_pnl: P/L from option legs only
        - stock_pnl: P/L from underlying stock legs (covered calls)
        - total_value: Current portfolio value
    """
    total_pnl = 0.0
    options_pnl = 0.0
    stock_pnl = 0.0
    
    for trade in trades:
        if trade.get('status') != 'open':
            continue
        
        strategy_type = trade.get('strategy_type', '').lower()
        trade_pnl = trade.get('pnl', 0.0)
        
        # For covered calls, separate option and stock P/L
        if strategy_type == 'covered_call':
            trade_option_pnl = trade.get('option_pnl', 0.0)
            trade_stock_pnl = trade.get('stock_pnl', 0.0)
            options_pnl += trade_option_pnl
            stock_pnl += trade_stock_pnl
            total_pnl += trade_pnl
        else:
            # For other strategies, treat as option-only P/L
            options_pnl += trade_pnl
            total_pnl += trade_pnl
    
    return {
        'total_pnl': total_pnl,
        'options_pnl': options_pnl,
        'stock_pnl': stock_pnl,
    }


def render_portfolio_summary(portfolio_data: Dict) -> None:
    """Render portfolio summary with P/L breakdown.
    
    Shows:
    - Total unrealized P/L
    - Options P/L component
    - Underlying stock P/L component
    - Warning if profitable options are hiding stock losses
    """
    st.header("Portfolio Summary")
    
    total_value = portfolio_data.get('total_value', 0.0)
    initial_value = portfolio_data.get('initial_value', 100000.0)
    total_pnl = portfolio_data.get('total_pnl', 0.0)
    options_pnl = portfolio_data.get('options_pnl', 0.0)
    stock_pnl = portfolio_data.get('stock_pnl', 0.0)
    
    # Calculate return percentage
    return_pct = 0.0
    if initial_value > 0:
        return_pct = ((total_value - initial_value) / initial_value) * 100
    
    # Display main metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Portfolio Value",
            value=f"${total_value:,.2f}",
            delta=f"{return_pct:+.2f}%"
        )
    
    with col2:
        st.metric(
            label="Total Unrealized P/L",
            value=f"${total_pnl:,.2f}",
            delta=None
        )
    
    with col3:
        st.metric(
            label="Initial Value",
            value=f"${initial_value:,.2f}",
            delta=None
        )
    
    # Display P/L breakdown
    st.markdown("---")
    st.subheader("P/L Breakdown")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Options P/L**")
        st.markdown(format_currency(options_pnl), unsafe_allow_html=True)
    
    with col2:
        st.markdown("**Underlying Stock P/L**")
        st.markdown(format_currency(stock_pnl), unsafe_allow_html=True)
    
    with col3:
        st.markdown("**Combined P/L**")
        st.markdown(format_currency(total_pnl), unsafe_allow_html=True)
    
    # Warning if profitable options are hiding stock losses
    if options_pnl > 0 and stock_pnl < 0:
        st.warning(
            f"⚠️ **Portfolio Alert**: While your options positions show a profit of ${options_pnl:,.2f}, "
            f"your underlying stock holdings have declined by ${abs(stock_pnl):,.2f}. "
            f"The combined portfolio P/L is ${total_pnl:,.2f}. "
            "Consider reviewing your covered call positions to ensure the overall strategy remains profitable."
        )
    
    # Info message explaining the breakdown
    with st.expander("Understanding P/L Breakdown"):
        st.markdown("""
        **Options P/L**: Profit or loss from option contracts (calls, puts, spreads).
        
        **Underlying Stock P/L**: Profit or loss from stock holdings associated with covered calls.
        
        **Combined P/L**: Total portfolio P/L including both components.
        
        For covered calls specifically:
        - A declining stock price may cause stock losses even if the option premium has decreased (option profit)
        - The combined P/L represents the true economic performance of the position
        - Always consider both components when evaluating covered call profitability
        """)


def render_dashboard(portfolio_data: Dict, signals: List[Dict], trades: List[Dict]) -> None:
    """Render the main dashboard view.
    
    Args:
        portfolio_data: Portfolio summary data
        signals: List of pending signals
        trades: List of all trades
    """
    st.title("Options Trading Dashboard")
    
    # Calculate P/L breakdown
    pnl_breakdown = calculate_portfolio_pnl_breakdown(trades)
    portfolio_data.update(pnl_breakdown)
    
    # Render portfolio summary
    render_portfolio_summary(portfolio_data)
    
    st.markdown("---")
    
    # Display pending signals
    st.header(f"Pending Signals ({len(signals)})")
    if signals:
        for signal in signals:
            render_signal_card(signal)
    else:
        st.info("No pending signals. Generate new signals from your watchlist.")
    
    # Quick actions
    st.markdown("---")
    st.header("Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Generate New Signals"):
            st.info("Signal generation triggered. Check back in a moment.")
    
    with col2:
        if st.button("Refresh Prices"):
            st.info("Refreshing market data...")
    
    with col3:
        if st.button("View Watchlist"):
            st.info("Navigate to Watchlist page.")


def render_signal_card(signal: Dict) -> None:
    """Render a signal card with key information."""
    symbol = signal.get('symbol', 'N/A')
    strategy = signal.get('strategy_type', 'Unknown').replace('_', ' ').title()
    score = signal.get('score', 0.0)
    expected_profit = signal.get('expected_profit', 0.0)
    max_loss = signal.get('max_loss', 0.0)
    probability = signal.get('probability_estimate', 0.0)
    
    with st.container():
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        
        with col1:
            st.markdown(f"**{symbol}**")
            st.caption(strategy)
        
        with col2:
            st.markdown(f"Score: {score:.2f}")
            st.caption(f"Probability: {probability:.1%}")
        
        with col3:
            st.markdown(f"Expected: {format_currency(expected_profit)}", unsafe_allow_html=True)
            st.caption(f"Max Loss: ${abs(max_loss):.2f}")
        
        with col4:
            if st.button("Review", key=f"signal_{signal.get('id', 0)}"):
                st.info(f"Reviewing signal for {symbol}...")
        
        st.markdown("---")
