"""Dashboard frontend component for portfolio overview and signal generation.

Displays portfolio summary with P/L breakdown, active signals, and controls
for generating new trading signals. For covered calls, shows separate
options P/L and underlying stock P/L to prevent misleading displays.
"""

import streamlit as st
from typing import Dict, Any, List, Optional
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


def render_portfolio_summary(summary: Dict[str, Any]) -> None:
    """Render portfolio summary with P/L breakdown.
    
    For portfolios with covered calls, shows:
    - Total unrealized P/L
    - Options P/L (separate)
    - Underlying stock P/L (separate)
    - Warning if profitable options hide losing stocks
    
    Args:
        summary: Portfolio summary dictionary from API
    """
    st.header("Portfolio Summary")
    
    total_value = summary.get('total_value', 0.0)
    cash_balance = summary.get('cash_balance', 0.0)
    total_pnl = summary.get('total_unrealized_pnl', 0.0)
    total_pnl_pct = summary.get('total_unrealized_pnl_pct', 0.0)
    
    # Check if we have separate option and stock P/L
    option_pnl = summary.get('option_pnl', None)
    stock_pnl = summary.get('stock_pnl', None)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Portfolio Value", f"${total_value:,.2f}")
    
    with col2:
        st.metric("Cash Balance", f"${cash_balance:,.2f}")
    
    with col3:
        st.markdown(f"**Total Unrealized P/L:** {format_currency(total_pnl)}", unsafe_allow_html=True)
        st.markdown(f"**Return:** {format_percentage(total_pnl_pct)}", unsafe_allow_html=True)
    
    # Show P/L breakdown if available
    if option_pnl is not None and stock_pnl is not None:
        st.markdown("---")
        st.subheader("P/L Breakdown")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"**Options P/L:** {format_currency(option_pnl)}", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"**Underlying Stock P/L:** {format_currency(stock_pnl)}", unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"**Combined P/L:** {format_currency(total_pnl)}", unsafe_allow_html=True)
        
        # Warning if options are profitable but stocks are losing more
        if option_pnl > 0 and stock_pnl < 0 and total_pnl < 0:
            st.warning(
                "⚠️ **Portfolio Alert:** Your options positions are profitable, "
                "but underlying stock losses exceed option gains. "
                "Overall portfolio is losing money."
            )
        
        # Info box explaining the breakdown
        with st.expander("ℹ️ Understanding P/L Breakdown"):
            st.markdown("""
            **Options P/L:** Profit/loss from option premiums (short calls, short puts, spreads, etc.)
            
            **Underlying Stock P/L:** Profit/loss from stock positions associated with covered calls
            
            **Combined P/L:** Total portfolio P/L = Options P/L + Underlying Stock P/L
            
            For covered calls specifically:
            - A declining stock price can cause losses even if the option premium is profitable
            - The combined P/L shows the true economic performance of the strategy
            - Break-even is calculated as: Stock Entry Price - Premium Received per Share
            """)


def render_active_signals(signals: List[Dict[str, Any]]) -> None:
    """Render active trading signals awaiting approval.
    
    Args:
        signals: List of signal dictionaries from API
    """
    st.header(f"Active Signals ({len(signals)})")
    
    if not signals:
        st.info("No active signals. Generate new signals using the controls below.")
        return
    
    for signal in signals:
        with st.expander(f"{signal.get('symbol', 'N/A')} - {signal.get('strategy_type', 'unknown').replace('_', ' ').title()}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Score:** {signal.get('score', 0.0):.2f}")
                st.write(f"**Risk Level:** {signal.get('risk_level', 'unknown')}")
                st.write(f"**Expected Profit:** ${signal.get('expected_profit', 0.0):.2f}")
                st.write(f"**Max Loss:** ${signal.get('max_loss', 0.0):.2f}")
            
            with col2:
                st.write(f"**Probability:** {signal.get('probability_estimate', 0.0):.1%}")
                st.write(f"**Status:** {signal.get('status', 'unknown')}")
                st.write(f"**Created:** {signal.get('created_at', 'N/A')}")
            
            st.markdown("**Reason:**")
            st.write(signal.get('reason', 'No reason provided'))
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ Approve", key=f"approve_{signal.get('id')}"):
                    st.success(f"Signal {signal.get('id')} approved!")
            with col2:
                if st.button("❌ Reject", key=f"reject_{signal.get('id')}"):
                    st.warning(f"Signal {signal.get('id')} rejected.")
            with col3:
                if st.button("📋 Details", key=f"details_{signal.get('id')}"):
                    st.info("Detailed view coming soon...")


def render_signal_generation_controls() -> None:
    """Render controls for generating new trading signals."""
    st.header("Generate New Signals")
    
    col1, col2 = st.columns(2)
    
    with col1:
        symbol = st.text_input("Symbol", placeholder="e.g., AAPL")
        strategy = st.selectbox(
            "Strategy",
            [
                "covered_call",
                "cash_secured_put",
                "bull_call_spread",
                "bear_put_spread",
                "iron_condor",
                "long_call",
                "long_put"
            ]
        )
    
    with col2:
        risk_level = st.selectbox("Risk Level", ["low", "medium", "high"])
        
        if st.button("🔍 Generate Signal", type="primary"):
            if symbol:
                st.info(f"Generating {strategy.replace('_', ' ').title()} signal for {symbol.upper()}...")
                # API call would go here
            else:
                st.error("Please enter a symbol.")


def render_dashboard(
    summary: Dict[str, Any],
    signals: List[Dict[str, Any]],
    trades: List[Dict[str, Any]]
) -> None:
    """Render the main dashboard view.
    
    Args:
        summary: Portfolio summary dictionary
        signals: List of active signals
        trades: List of active trades
    """
    st.title("📈 Options Trading Dashboard")
    
    # Portfolio summary
    render_portfolio_summary(summary)
    
    st.markdown("---")
    
    # Active signals
    render_active_signals(signals)
    
    st.markdown("---")
    
    # Signal generation controls
    render_signal_generation_controls()
