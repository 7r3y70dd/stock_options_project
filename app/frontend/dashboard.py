"""Dashboard view for displaying portfolio overview and key metrics.

Displays portfolio summary with separate option and stock P/L components
to prevent misleading profit displays from covered call positions.
"""

import logging
from typing import Optional, Dict, Any, List
import streamlit as st
from datetime import datetime, timedelta

from app.frontend.api_client import APIClient

logger = logging.getLogger(__name__)


class DashboardView:
    """Dashboard view component for portfolio overview."""

    def __init__(self, api_client: APIClient):
        """Initialize dashboard view.
        
        Args:
            api_client: API client for backend communication
        """
        self.api_client = api_client

    def render(self, user_id: int) -> None:
        """Render the dashboard view.
        
        Args:
            user_id: User ID to display dashboard for
        """
        st.header("📈 Dashboard")

        try:
            # Fetch dashboard data
            portfolio_data = self.api_client.get_portfolio(user_id)
            if not portfolio_data:
                st.info("No portfolio data available.")
                return

            # Render portfolio summary
            self._render_portfolio_summary(portfolio_data)

            # Render recent activity
            st.subheader("Recent Activity")
            self._render_recent_activity(portfolio_data)

            # Render performance charts
            st.subheader("Performance")
            self._render_performance_charts(portfolio_data)

        except Exception as e:
            logger.error(f"Error rendering dashboard: {e}")
            st.error(f"Failed to load dashboard: {str(e)}")

    def _render_portfolio_summary(self, portfolio_data: Dict[str, Any]) -> None:
        """Render portfolio summary with P/L breakdown.
        
        Args:
            portfolio_data: Portfolio data from API
        """
        summary = portfolio_data.get("summary", {})
        
        # Main metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_value = summary.get("total_value", 0.0)
            initial_value = summary.get("initial_value", 100000.0)
            st.metric(
                "Portfolio Value",
                f"${total_value:,.2f}",
                delta=f"${total_value - initial_value:,.2f}"
            )
        
        with col2:
            total_pnl = summary.get("total_unrealized_pnl", 0.0)
            pnl_color = "normal" if total_pnl >= 0 else "inverse"
            st.metric(
                "Total Unrealized P/L",
                f"${total_pnl:,.2f}",
                delta_color=pnl_color
            )
        
        with col3:
            active_trades = summary.get("active_trades", 0)
            st.metric("Active Trades", active_trades)
        
        with col4:
            win_rate = summary.get("win_rate", 0.0)
            st.metric("Win Rate", f"{win_rate:.1f}%")
        
        # P/L breakdown section
        st.divider()
        st.subheader("P/L Breakdown")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            option_pnl = summary.get("option_pnl", 0.0)
            option_color = "🟢" if option_pnl >= 0 else "🔴"
            st.metric(
                "Options P/L",
                f"{option_color} ${option_pnl:,.2f}"
            )
            st.caption("Profit/loss from option contracts")
        
        with col2:
            stock_pnl = summary.get("stock_pnl", 0.0)
            stock_color = "🟢" if stock_pnl >= 0 else "🔴"
            st.metric(
                "Underlying Stock P/L",
                f"{stock_color} ${stock_pnl:,.2f}"
            )
            st.caption("Profit/loss from shares held for covered calls")
        
        with col3:
            combined_pnl = option_pnl + stock_pnl
            combined_color = "🟢" if combined_pnl >= 0 else "🔴"
            st.metric(
                "Combined P/L",
                f"{combined_color} ${combined_pnl:,.2f}"
            )
            st.caption("Total position P/L (options + stock)")
        
        # Explanation box
        with st.expander("ℹ️ Understanding P/L Breakdown"):
            st.write("""
            **Why separate Options P/L and Stock P/L?**
            
            For covered call positions, the application tracks two components:
            
            1. **Options P/L**: The profit or loss from the short call option contract.
               - When the call price decreases, the option P/L is positive (you can buy it back cheaper).
               - When the call price increases, the option P/L is negative.
            
            2. **Underlying Stock P/L**: The profit or loss from the shares you own.
               - When the stock price increases, the stock P/L is positive.
               - When the stock price decreases, the stock P/L is negative.
            
            3. **Combined P/L**: The true economic performance of your covered call position.
               - This is what matters for your actual profit or loss.
               - A profitable option leg can coexist with a losing stock position, resulting in an overall loss.
            
            **Example:**
            - Stock entry: $17.87, Current: $16.50 → Stock P/L: -$137
            - Option entry: $1.54, Current: $0.72 → Option P/L: +$82
            - **Combined P/L: -$55** (the position is actually losing money)
            
            This breakdown prevents misleading displays where a profitable option premium
            hides losses in the underlying shares.
            """)

    def _render_recent_activity(self, portfolio_data: Dict[str, Any]) -> None:
        """Render recent trading activity.
        
        Args:
            portfolio_data: Portfolio data from API
        """
        trades = portfolio_data.get("trades", [])
        
        if not trades:
            st.info("No recent activity.")
            return
        
        # Show last 5 trades
        recent_trades = sorted(
            trades,
            key=lambda t: t.get("opened_at", ""),
            reverse=True
        )[:5]
        
        for trade in recent_trades:
            symbol = trade.get("symbol", "N/A")
            strategy = trade.get("strategy_type", "unknown").replace("_", " ").title()
            status = trade.get("status", "unknown")
            pnl = trade.get("unrealized_pnl", 0.0)
            pnl_color = "🟢" if pnl >= 0 else "🔴"
            
            opened_at = trade.get("opened_at", "N/A")
            if opened_at != "N/A":
                try:
                    opened_dt = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
                    opened_at = opened_dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass
            
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            with col1:
                st.write(f"**{symbol}**")
            with col2:
                st.write(strategy)
            with col3:
                st.write(f"{pnl_color} ${pnl:,.2f}")
            with col4:
                st.write(opened_at)

    def _render_performance_charts(self, portfolio_data: Dict[str, Any]) -> None:
        """Render performance charts.
        
        Args:
            portfolio_data: Portfolio data from API
        """
        summary = portfolio_data.get("summary", {})
        
        # Strategy breakdown
        st.write("**Strategy Performance**")
        
        trades = portfolio_data.get("trades", [])
        if not trades:
            st.info("No trades to display.")
            return
        
        # Group by strategy
        strategy_pnl: Dict[str, float] = {}
        strategy_count: Dict[str, int] = {}
        
        for trade in trades:
            strategy = trade.get("strategy_type", "unknown")
            pnl = trade.get("unrealized_pnl", 0.0)
            
            if strategy not in strategy_pnl:
                strategy_pnl[strategy] = 0.0
                strategy_count[strategy] = 0
            
            strategy_pnl[strategy] += pnl
            strategy_count[strategy] += 1
        
        # Display strategy breakdown
        for strategy, pnl in strategy_pnl.items():
            count = strategy_count[strategy]
            avg_pnl = pnl / count if count > 0 else 0.0
            pnl_color = "🟢" if pnl >= 0 else "🔴"
            
            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                st.write(f"**{strategy.replace('_', ' ').title()}**")
            with col2:
                st.write(f"{pnl_color} ${pnl:,.2f}")
            with col3:
                st.write(f"{count} trades (avg: ${avg_pnl:,.2f})")
