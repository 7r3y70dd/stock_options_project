"""Abstract base interface for data providers.

Defines the contract that all data providers (Alpha Vantage, yfinance, Finnhub, Alpaca, Tradier, Polygon) must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Quote:
    """Current price quote for a symbol."""
    symbol: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[int] = None
    timestamp: Optional[datetime] = None


@dataclass
class PriceBar:
    """OHLCV price bar for a symbol."""
    date: str  # ISO format YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None


@dataclass
class OptionChainEntry:
    """Single option contract in a chain."""
    symbol: str
    expiration: str  # ISO format YYYY-MM-DD
    strike: float
    contract_type: str  # "call" or "put"
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    implied_volatility: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None


@dataclass
class NewsArticle:
    """News article about a symbol."""
    symbol: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    published_at: Optional[datetime] = None
    sentiment: Optional[str] = None  # "positive", "negative", "neutral"


@dataclass
class EarningsDate:
    """Earnings date information for a symbol."""
    symbol: str
    date: str  # ISO format YYYY-MM-DD
    time: Optional[str] = None  # HH:MM format or "before_open", "after_close"
    eps_estimate: Optional[float] = None
    eps_actual: Optional[float] = None
    revenue_estimate: Optional[float] = None
    revenue_actual: Optional[float] = None


class DataProvider(ABC):
    """Abstract base class for data providers.
    
    All data providers must implement these methods to provide market data,
    options chains, news, and earnings information.
    """

    @abstractmethod
    def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get current price quote for a symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            
        Returns:
            Quote object with current price and bid/ask, or None if not available
        """
        pass

    @abstractmethod
    def get_price_history(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "daily",
    ) -> List[PriceBar]:
        """Get historical price data for a symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
            interval: Data interval ("daily", "weekly", "monthly")
            
        Returns:
            List of PriceBar objects sorted by date ascending
        """
        pass

    @abstractmethod
    def get_options_chain(
        self,
        symbol: str,
        expiration: Optional[str] = None,
    ) -> List[OptionChainEntry]:
        """Get options chain for a symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            expiration: Optional specific expiration date (YYYY-MM-DD).
                       If None, return all available expirations.
            
        Returns:
            List of OptionChainEntry objects for all strikes and types
        """
        pass

    @abstractmethod
    def get_news(self, symbol: str, limit: int = 10) -> List[NewsArticle]:
        """Get recent news articles for a symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            limit: Maximum number of articles to return
            
        Returns:
            List of NewsArticle objects sorted by date descending (newest first)
        """
        pass

    @abstractmethod
    def get_earnings_date(self, symbol: str) -> Optional[EarningsDate]:
        """Get next earnings date for a symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            
        Returns:
            EarningsDate object with next earnings info, or None if not available
        """
        pass
