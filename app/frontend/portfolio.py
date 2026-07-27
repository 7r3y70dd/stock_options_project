"""Portfolio view for displaying user trades and positions.

Displays active trades with P/L calculations, including separate option and stock
P/L for covered calls to show the true economic performance of the position.
"""

import logging
from typing import Optional, List, Dict, Any
import streamlit as st
from datetime import datetime

from app.frontend.api_client import APIClient

logger = logging.getLogger(__name__)


class PortfolioView:
    """Portfolio view component for displaying trades and positions."""

    def __init__(self, api_client: APIClient):
        """Initialize portfolio view.
        
        Args:
            api_client: API client for backend communication
        """
        self.api_client = api_client

    def render(self, user_id: int) -> None:
        """Render the portfolio view.
        
        Args:
            user_id: User ID to display portfolio for
        """
        st.header("📊 Portfolio")

        # Fetch portfolio data
        try:
            portfolio_data = self.api_client.get_portfolio(user_id)
            if not portfolio_data:
                st.info("No portfolio data available.")
                return

            # Display portfolio summary
            self._render_portfolio_summary(portfolio_data)

            # Display active trades
            st.subheader("Active Trades")
            trades = portfolio_data.get("trades", [])
            if not trades:
                st.info("No active trades.")
            else:
                self._render_trades_table(trades)

        except Exception as e:
            logger.error(f"Error rendering portfolio: {e}")
            st.error(f"Failed to load portfolio: {str(e)}")

    def _render_portfolio_summary(self, portfolio_data: Dict[str, Any]) -> None:
        """Render portfolio summary metrics.
        
        Args:
            portfolio_data: Portfolio data from API
        """
        summary = portfolio_data.get("summary", {})
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_value = summary.get("total_value", 0.0)
            st.metric("Total Portfolio Value", f"${total_value:,.2f}")
        
        with col2:
            total_pnl = summary.get("total_unrealized_pnl", 0.0)
            pnl_color = "normal" if total_pnl >= 0 else "inverse"
            st.metric("Total Unrealized P/L", f"${total_pnl:,.2f}", delta_color=pnl_color)
        
        with col3:
            option_pnl = summary.get("option_pnl", 0.0)
            st.metric("Options P/L", f"${option_pnl:,.2f}")
        
        with col4:
            stock_pnl = summary.get("stock_pnl", 0.0)
            st.metric("Underlying Stock P/L", f"${stock_pnl:,.2f}")
        
        # Show breakdown explanation for covered calls
        if option_pnl != 0 or stock_pnl != 0:
            with st.expander("ℹ️ P/L Breakdown Explanation"):
                st.write("""
                **Total Unrealized P/L** includes both:
                - **Options P/L**: Profit/loss from option contracts (calls, puts, spreads)
                - **Underlying Stock P/L**: Profit/loss from shares held for covered calls
                
                For covered calls, the combined position P/L reflects the true economic performance,
                not just the option premium captured.
                """)

    def _render_trades_table(self, trades: List[Dict[str, Any]]) -> None:
        """Render trades in a table format.
        
        Args:
            trades: List of trade dictionaries
        """
        for trade in trades:
            self._render_trade_card(trade)

    def _render_trade_card(self, trade: Dict[str, Any]) -> None:
        """Render a single trade as an expandable card.
        
        Args:
            trade: Trade dictionary
        """
        strategy_type = trade.get("strategy_type", "unknown")
        symbol = trade.get("symbol", "N/A")
        status = trade.get("status", "unknown")
        
        # Calculate total P/L
        total_pnl = trade.get("unrealized_pnl", 0.0)
        option_pnl = trade.get("option_pnl")
        stock_pnl = trade.get("stock_pnl")
        
        # Format P/L display
        pnl_display = f"${total_pnl:,.2f}"
        pnl_color = "🟢" if total_pnl >= 0 else "🔴"
        
        # Create expandable section
        with st.expander(f"{pnl_color} {symbol} - {strategy_type.replace('_', ' ').title()} | P/L: {pnl_display}"):
            # Basic trade info
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Status:** {status}")
                st.write(f"**Quantity:** {trade.get('quantity', 0)}")
            
            with col2:
                entry_price = trade.get("entry_price", 0.0)
                current_price = trade.get("current_price", 0.0)
                st.write(f"**Entry Price:** ${entry_price:.2f}")
                st.write(f"**Current Price:** ${current_price:.2f}")
            
            with col3:
                opened_at = trade.get("opened_at", "N/A")
                if opened_at != "N/A":
                    try:
                        opened_dt = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
                        opened_at = opened_dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                st.write(f"**Opened:** {opened_at}")
            
            # For covered calls, show detailed breakdown
            if strategy_type == "covered_call" and (option_pnl is not None or stock_pnl is not None):
                st.divider()
                st.write("**Covered Call Position Breakdown**")
                
                # Underlying stock section
                st.write("**Underlying Stock**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    shares = trade.get("underlying_quantity", 100)
                    st.write(f"Shares: {shares}")
                with col2:
                    stock_entry = trade.get("underlying_entry_price", 0.0)
                    st.write(f"Entry: ${stock_entry:.2f}")
                with col3:
                    stock_current = trade.get("underlying_current_price", 0.0)
                    st.write(f"Current: ${stock_current:.2f}")
                
                if stock_pnl is not None:
                    stock_pnl_color = "🟢" if stock_pnl >= 0 else "🔴"
                    st.write(f"{stock_pnl_color} **Stock P/L:** ${stock_pnl:,.2f}")
                
                # Option section
                st.write("**Short Call Option**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    strike = trade.get("strike", 0.0)
                    st.write(f"Strike: ${strike:.2f}")
                with col2:
                    expiration = trade.get("expiration", "N/A")
                    st.write(f"Expiration: {expiration}")
                with col3:
                    premium = entry_price * 100 * trade.get('quantity', 1)
                    st.write(f"Premium: ${premium:.2f}")
                
                if option_pnl is not None:
                    option_pnl_color = "🟢" if option_pnl >= 0 else "🔴"
                    st.write(f"{option_pnl_color} **Option P/L:** ${option_pnl:,.2f}")
                    
                    # Premium captured percentage
                    if premium > 0:
                        premium_captured_pct = (option_pnl / premium) * 100
                        st.write(f"**Premium Captured:** {premium_captured_pct:.2f}%")
                
                # Combined position
                st.divider()
                st.write("**Combined Position**")
                col1, col2 = st.columns(2)
                with col1:
                    total_pnl_color = "🟢" if total_pnl >= 0 else "🔴"
                    st.write(f"{total_pnl_color} **Total Position P/L:** ${total_pnl:,.2f}")
                
                with col2:
                    # Calculate total return percentage
                    stock_entry = trade.get("underlying_entry_price", 0.0)
                    shares = trade.get("underlying_quantity", 100)
                    quantity = trade.get('quantity', 1)
                    if stock_entry > 0 and shares > 0:
                        net_capital = (stock_entry * shares * quantity) - premium
                        if net_capital > 0:
                            total_return_pct = (total_pnl / net_capital) * 100
                            st.write(f"**Total Return:** {total_return_pct:.2f}%")
                
                # Show break-even and max profit
                col1, col2 = st.columns(2)
                with col1:
                    stock_entry = trade.get("underlying_entry_price", 0.0)
                    if stock_entry > 0 and premium > 0:
                        premium_per_share = premium / (shares * quantity)
                        break_even = stock_entry - premium_per_share
                        st.write(f"**Break-even:** ${break_even:.2f}")
                
                with col2:
                    strike = trade.get("strike", 0.0)
                    if stock_entry > 0 and strike > 0:
                        stock_appreciation = (strike - stock_entry) * shares * quantity
                        max_profit = stock_appreciation + premium
                        st.write(f"**Maximum Profit:** ${max_profit:.2f}")
            
            else:
                # For non-covered-call strategies, show standard P/L
                st.divider()
                pnl_pct = trade.get("unrealized_pnl_pct", 0.0)
                st.write(f"**P/L:** ${total_pnl:,.2f} ({pnl_pct:.2f}%)")
            
            # Action buttons
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Close Trade #{trade.get('id')}", key=f"close_{trade.get('id')}"):
                    self._close_trade(trade.get('id'))
            with col2:
                if st.button(f"View Details #{trade.get('id')}", key=f"details_{trade.get('id')}"):
                    self._show_trade_details(trade)

    def _close_trade(self, trade_id: int) -> None:
        """Close a trade.
        
        Args:
            trade_id: Trade ID to close
        """
        try:
            result = self.api_client.close_trade(trade_id)
            if result:
                st.success(f"Trade #{trade_id} closed successfully!")
                st.rerun()
            else:
                st.error(f"Failed to close trade #{trade_id}")
        except Exception as e:
            logger.error(f"Error closing trade {trade_id}: {e}")
            st.error(f"Error closing trade: {str(e)}")

    def _show_trade_details(self, trade: Dict[str, Any]) -> None:
        """Show detailed trade information in a modal.
        
        Args:
            trade: Trade dictionary
        """
        st.json(trade)
