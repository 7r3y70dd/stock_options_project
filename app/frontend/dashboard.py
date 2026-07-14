"""Dashboard service for aggregating and managing dashboard data.

Provides methods for fetching and managing dashboard data including
portfolio, watchlist, opportunities, trades, news, and risk settings.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from app.frontend.api_client import APIClient, APIError
from app.models.database import MarketQuote, WatchlistSymbol
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class Dashboard:
    """Dashboard service for data aggregation."""
    
    def __init__(self, api_client: APIClient, db: Optional[Session] = None):
        """Initialize dashboard service.
        
        Args:
            api_client: API client instance
            db: Optional database session for local queries
        """
        self.api_client = api_client
        self.db = db
    
    def get_dashboard_data(self, user_id: int = None) -> Dict[str, Any]:
        """Get full dashboard data.
        
        Args:
            user_id: User ID (optional)
            
        Returns:
            Dashboard data dictionary
            
        Raises:
            APIError: If API call fails
        """
        try:
            return self.api_client.get_dashboard(user_id=user_id)
        except APIError as e:
            logger.error(f"Error fetching dashboard data: {e.message}")
            raise
    
    def get_portfolio_summary(self, user_id: int = None) -> Dict[str, Any]:
        """Get portfolio summary.
        
        Args:
            user_id: User ID (optional)
            
        Returns:
            Portfolio summary data
            
        Raises:
            APIError: If API call fails
        """
        try:
            return self.api_client.get_portfolio(user_id=user_id)
        except APIError as e:
            logger.error(f"Error fetching portfolio: {e.message}")
            raise
    
    def get_watchlist(self, user_id: int = None) -> Dict[str, Any]:
        """Get watchlist with current prices and data freshness.
        
        Fetches watchlist symbols and enriches with latest market quotes
        from the database.
        
        Args:
            user_id: User ID (optional)
            
        Returns:
            Watchlist data with current_price, last_updated, data_freshness_seconds
            
        Raises:
            APIError: If API call fails
        """
        try:
            watchlist_data = self.api_client.get_watchlist(user_id=user_id)
            
            # Enrich with market quote data if database available
            if self.db and isinstance(watchlist_data, dict) and "symbols" in watchlist_data:
                for item in watchlist_data["symbols"]:
                    symbol = item.get("symbol")
                    if symbol and user_id:
                        # Get latest market quote for this symbol
                        try:
                            ws = self.db.query(WatchlistSymbol).filter(
                                WatchlistSymbol.user_id == user_id,
                                WatchlistSymbol.symbol == symbol
                            ).first()
                            
                            if ws:
                                latest_quote = self.db.query(MarketQuote).filter(
                                    MarketQuote.watchlist_symbol_id == ws.id
                                ).order_by(MarketQuote.fetched_at.desc()).first()
                                
                                if latest_quote:
                                    item["current_price"] = latest_quote.price
                                    item["last_updated"] = latest_quote.fetched_at.isoformat()
                                    
                                    # Calculate data freshness
                                    now = datetime.utcnow()
                                    freshness = (now - latest_quote.fetched_at).total_seconds()
                                    item["data_freshness_seconds"] = int(freshness)
                        except Exception as e:
                            logger.warning(f"Error enriching watchlist for {symbol}: {e}")
            
            return watchlist_data
        except APIError as e:
            logger.error(f"Error fetching watchlist: {e.message}")
            raise
    
    def get_top_opportunities(self, user_id: int = None, limit: int = 10) -> Dict[str, Any]:
        """Get top trading opportunities.
        
        Args:
            user_id: User ID (optional)
            limit: Maximum number of opportunities
            
        Returns:
            Opportunities data
            
        Raises:
            APIError: If API call fails
        """
        try:
            return self.api_client.get_opportunities(user_id=user_id, limit=limit)
        except APIError as e:
            logger.error(f"Error fetching opportunities: {e.message}")
            raise
    
    def get_opportunity_detail(self, signal_id: str, user_id: int = None) -> Dict[str, Any]:
        """Get detailed opportunity data.
        
        Args:
            signal_id: Signal ID
            user_id: User ID (optional)
            
        Returns:
            Detailed opportunity data
            
        Raises:
            APIError: If API call fails
        """
        try:
            return self.api_client.get_opportunity_detail(signal_id=signal_id, user_id=user_id)
        except APIError as e:
            logger.error(f"Error fetching opportunity detail: {e.message}")
            raise
    
    def get_open_trades(self, user_id: int = None) -> Dict[str, Any]:
        """Get open trades.
        
        Args:
            user_id: User ID (optional)
            
        Returns:
            Trades data
            
        Raises:
            APIError: If API call fails
        """
        try:
            return self.api_client.get_trades(user_id=user_id)
        except APIError as e:
            logger.error(f"Error fetching trades: {e.message}")
            raise
    
    def get_recent_news(self, user_id: int = None, limit: int = 20) -> Dict[str, Any]:
        """Get recent news.
        
        Args:
            user_id: User ID (optional)
            limit: Maximum number of news items
            
        Returns:
            News data
            
        Raises:
            APIError: If API call fails
        """
        try:
            return self.api_client.get_news(user_id=user_id, limit=limit)
        except APIError as e:
            logger.error(f"Error fetching news: {e.message}")
            raise
    
    def get_risk_settings(self, user_id: int = None) -> Dict[str, Any]:
        """Get risk settings.
        
        Args:
            user_id: User ID (optional)
            
        Returns:
            Risk settings data
            
        Raises:
            APIError: If API call fails
        """
        try:
            return self.api_client.get_risk_settings(user_id=user_id)
        except APIError as e:
            logger.error(f"Error fetching risk settings: {e.message}")
            raise
    
    def validate_symbol(self, symbol: str) -> Dict[str, Any]:
        """Validate a stock symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Validation result
            
        Raises:
            APIError: If API call fails
        """
        try:
            return self.api_client.validate_symbol(symbol=symbol)
        except APIError as e:
            logger.error(f"Error validating symbol: {e.message}")
            raise
    
    def add_watchlist_symbol(self, symbol: str, user_id: int = None) -> Dict[str, Any]:
        """Add symbol to watchlist.
        
        Args:
            symbol: Stock symbol
            user_id: User ID (optional)
            
        Returns:
            Add result
            
        Raises:
            APIError: If API call fails
        """
        try:
            return self.api_client.add_watchlist_symbol(symbol=symbol, user_id=user_id)
        except APIError as e:
            logger.error(f"Error adding watchlist symbol: {e.message}")
            raise
    
    def remove_watchlist_symbol(self, symbol: str, user_id: int = None) -> Dict[str, Any]:
        """Remove symbol from watchlist.
        
        Args:
            symbol: Stock symbol
            user_id: User ID (optional)
            
        Returns:
            Remove result
            
        Raises:
            APIError: If API call fails
        """
        try:
            return self.api_client.remove_watchlist_symbol(symbol=symbol, user_id=user_id)
        except APIError as e:
            logger.error(f"Error removing watchlist symbol: {e.message}")
            raise
    
    def update_risk_settings(self, risk_level: str, confirmed: bool = False,
                            user_id: int = None) -> Dict[str, Any]:
        """Update risk settings.
        
        Args:
            risk_level: Risk level (low, medium, high)
            confirmed: Whether user confirmed
            user_id: User ID (optional)
            
        Returns:
            Update result
            
        Raises:
            APIError: If API call fails
        """
        try:
            return self.api_client.update_risk_settings(
                risk_level=risk_level,
                confirmed=confirmed,
                user_id=user_id
            )
        except APIError as e:
            logger.error(f"Error updating risk settings: {e.message}")
            raise
