"""Alpha Vantage data provider implementation.

Provides market data, options chains, news, and earnings information via Alpha Vantage API.
Handles rate limiting, caching, and error recovery.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from functools import lru_cache
import requests

from app.data_sources.data_provider import (
    DataProvider,
    Quote,
    PriceBar,
    OptionChainEntry,
    NewsArticle,
    EarningsDate,
)
from app.core.config import config

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""
    pass


class AlphaVantageProvider(DataProvider):
    """Alpha Vantage data provider.
    
    Implements DataProvider interface using Alpha Vantage API.
    Handles rate limiting (5 calls/min for free tier) with exponential backoff.
    Caches responses to minimize API calls.
    """

    BASE_URL = "https://www.alphavantage.co/query"
    FREE_TIER_CALLS_PER_MINUTE = 5
    CACHE_TTL_SECONDS = 300  # 5 minutes

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit_calls_per_minute: int = FREE_TIER_CALLS_PER_MINUTE,
        cache_ttl_seconds: int = CACHE_TTL_SECONDS,
    ):
        """Initialize Alpha Vantage provider.
        
        Args:
            api_key: Alpha Vantage API key. If None, uses ALPHAVANTAGE_API_KEY from config.
            rate_limit_calls_per_minute: Rate limit for API calls (default: 5 for free tier).
            cache_ttl_seconds: Cache time-to-live in seconds (default: 300).
            
        Raises:
            ValueError: If no API key is provided or configured.
        """
        self.api_key = api_key or config.ALPHAVANTAGE_API_KEY
        if not self.api_key:
            raise ValueError(
                "Alpha Vantage API key not provided. "
                "Set ALPHAVANTAGE_API_KEY environment variable or pass api_key parameter."
            )
        
        self.rate_limit_calls_per_minute = rate_limit_calls_per_minute
        self.cache_ttl_seconds = cache_ttl_seconds
        self.last_call_time = 0.0
        self.call_count = 0
        self.call_window_start = time.time()
        self._response_cache: Dict[str, Tuple[float, any]] = {}
        
        logger.info(
            f"AlphaVantageProvider initialized with rate limit: "
            f"{rate_limit_calls_per_minute} calls/min"
        )

    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limits.
        
        Implements token bucket algorithm for rate limiting.
        """
        current_time = time.time()
        window_elapsed = current_time - self.call_window_start
        
        # Reset window if 60 seconds have passed
        if window_elapsed >= 60:
            self.call_count = 0
            self.call_window_start = current_time
            window_elapsed = 0
        
        # If we've hit the limit, wait until window resets
        if self.call_count >= self.rate_limit_calls_per_minute:
            wait_time = 60 - window_elapsed
            if wait_time > 0:
                logger.warning(
                    f"Rate limit reached. Waiting {wait_time:.1f}s before next API call."
                )
                time.sleep(wait_time)
                self.call_count = 0
                self.call_window_start = time.time()
        
        self.call_count += 1

    def _get_cached(self, key: str) -> Optional[any]:
        """Get value from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if key in self._response_cache:
            timestamp, value = self._response_cache[key]
            if time.time() - timestamp < self.cache_ttl_seconds:
                logger.debug(f"Cache hit for key: {key}")
                return value
            else:
                del self._response_cache[key]
        return None

    def _set_cached(self, key: str, value: any) -> None:
        """Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self._response_cache[key] = (time.time(), value)
        logger.debug(f"Cached value for key: {key}")

    def _api_call(
        self,
        function: str,
        params: Dict[str, str],
        max_retries: int = 3,
    ) -> Optional[Dict]:
        """Make API call to Alpha Vantage with rate limiting and retry logic.
        
        Args:
            function: Alpha Vantage function name (e.g., "GLOBAL_QUOTE")
            params: Additional parameters for the API call
            max_retries: Maximum number of retries on rate limit
            
        Returns:
            JSON response as dictionary or None on error
            
        Raises:
            RateLimitError: If rate limit is exceeded after retries
        """
        # Create cache key
        cache_key = f"{function}:{','.join(f'{k}={v}' for k, v in sorted(params.items()))}"
        
        # Check cache first
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        # Prepare request
        request_params = {
            "function": function,
            "apikey": self.api_key,
            **params,
        }
        
        # Retry loop with exponential backoff
        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()
                
                logger.debug(f"API call: {function} with params {params}")
                response = requests.get(self.BASE_URL, params=request_params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # Check for API errors
                if "Error Message" in data:
                    logger.error(f"API error: {data['Error Message']}")
                    return None
                
                if "Note" in data:
                    # Rate limit hit
                    if attempt < max_retries - 1:
                        wait_time = 60 * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"Rate limit hit. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        raise RateLimitError("Rate limit exceeded after retries")
                
                # Cache successful response
                self._set_cached(cache_key, data)
                return data
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 5 * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    return None
        
        return None

    def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get current price quote for a symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            
        Returns:
            Quote object with current price and bid/ask, or None if not available
        """
        try:
            data = self._api_call(
                "GLOBAL_QUOTE",
                {"symbol": symbol.upper()},
            )
            
            if not data or "Global Quote" not in data:
                logger.warning(f"No quote data for symbol {symbol}")
                return None
            
            quote_data = data["Global Quote"]
            
            if not quote_data.get("05. price"):
                logger.warning(f"No price data for symbol {symbol}")
                return None
            
            price = float(quote_data.get("05. price", 0))
            bid = float(quote_data.get("08. bid", price))
            ask = float(quote_data.get("09. ask", price))
            volume = int(quote_data.get("06. volume", 0))
            
            return Quote(
                symbol=symbol.upper(),
                price=price,
                bid=bid if bid > 0 else None,
                ask=ask if ask > 0 else None,
                volume=volume if volume > 0 else None,
                timestamp=datetime.utcnow(),
            )
            
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}", exc_info=True)
            return None

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
        try:
            # Map interval to Alpha Vantage function
            function_map = {
                "daily": "TIME_SERIES_DAILY_ADJUSTED",
                "weekly": "TIME_SERIES_WEEKLY_ADJUSTED",
                "monthly": "TIME_SERIES_MONTHLY_ADJUSTED",
            }
            
            function = function_map.get(interval, "TIME_SERIES_DAILY_ADJUSTED")
            
            data = self._api_call(
                function,
                {"symbol": symbol.upper()},
            )
            
            if not data:
                logger.warning(f"No price history data for symbol {symbol}")
                return []
            
            # Extract time series data
            time_series_key = None
            for key in data.keys():
                if "Time Series" in key:
                    time_series_key = key
                    break
            
            if not time_series_key or not data[time_series_key]:
                logger.warning(f"No time series data for symbol {symbol}")
                return []
            
            time_series = data[time_series_key]
            
            # Parse dates
            try:
                start = datetime.fromisoformat(start_date).date()
                end = datetime.fromisoformat(end_date).date()
            except ValueError:
                logger.error(f"Invalid date format: {start_date} or {end_date}")
                return []
            
            bars = []
            for date_str, ohlcv in sorted(time_series.items()):
                try:
                    bar_date = datetime.fromisoformat(date_str).date()
                    
                    # Filter by date range
                    if bar_date < start or bar_date > end:
                        continue
                    
                    bar = PriceBar(
                        date=date_str,
                        open=float(ohlcv.get("1. open", 0)),
                        high=float(ohlcv.get("2. high", 0)),
                        low=float(ohlcv.get("3. low", 0)),
                        close=float(ohlcv.get("4. close", 0)),
                        volume=int(float(ohlcv.get("6. volume", 0))),
                        adjusted_close=float(ohlcv.get("5. adjusted close", 0)),
                    )
                    bars.append(bar)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error parsing bar data for {date_str}: {e}")
                    continue
            
            return sorted(bars, key=lambda b: b.date)
            
        except Exception as e:
            logger.error(f"Error getting price history for {symbol}: {e}", exc_info=True)
            return []

    def get_options_chain(
        self,
        symbol: str,
        expiration: Optional[str] = None,
    ) -> List[OptionChainEntry]:
        """Get options chain for a symbol.
        
        Note: Alpha Vantage provides historical options data but not real-time chains.
        This implementation returns empty list as Alpha Vantage free tier does not
        provide current options chain data. For production, consider Polygon or Tradier.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            expiration: Optional specific expiration date (YYYY-MM-DD)
            
        Returns:
            List of OptionChainEntry objects (empty for Alpha Vantage free tier)
        """
        logger.warning(
            f"Alpha Vantage free tier does not provide real-time options chains. "
            f"Consider using Polygon or Tradier for options data."
        )
        return []

    def get_news(self, symbol: str, limit: int = 10) -> List[NewsArticle]:
        """Get recent news articles for a symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            limit: Maximum number of articles to return
            
        Returns:
            List of NewsArticle objects sorted by date descending (newest first)
        """
        try:
            data = self._api_call(
                "NEWS_SENTIMENT",
                {"tickers": symbol.upper(), "limit": str(limit)},
            )
            
            if not data or "feed" not in data:
                logger.warning(f"No news data for symbol {symbol}")
                return []
            
            articles = []
            for item in data["feed"][:limit]:
                try:
                    # Parse sentiment
                    sentiment_score = float(item.get("overall_sentiment_score", 0))
                    if sentiment_score > 0.1:
                        sentiment = "positive"
                    elif sentiment_score < -0.1:
                        sentiment = "negative"
                    else:
                        sentiment = "neutral"
                    
                    # Parse published date
                    published_at = None
                    try:
                        published_at = datetime.fromisoformat(
                            item.get("time_published", "").replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        pass
                    
                    article = NewsArticle(
                        symbol=symbol.upper(),
                        title=item.get("title", ""),
                        description=item.get("summary", ""),
                        url=item.get("url", ""),
                        source=item.get("source", ""),
                        published_at=published_at,
                        sentiment=sentiment,
                    )
                    articles.append(article)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error parsing news item: {e}")
                    continue
            
            return sorted(
                articles,
                key=lambda a: a.published_at or datetime.min,
                reverse=True,
            )
            
        except Exception as e:
            logger.error(f"Error getting news for {symbol}: {e}", exc_info=True)
            return []

    def get_earnings_date(self, symbol: str) -> Optional[EarningsDate]:
        """Get next earnings date for a symbol.
        
        Note: Alpha Vantage does not provide earnings dates in free tier.
        This implementation returns None. For production, use dedicated earnings API.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            
        Returns:
            None (Alpha Vantage free tier does not provide earnings data)
        """
        logger.warning(
            f"Alpha Vantage free tier does not provide earnings dates. "
            f"Consider using Finnhub or Polygon for earnings data."
        )
        return None
