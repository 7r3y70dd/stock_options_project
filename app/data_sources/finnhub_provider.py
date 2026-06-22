"""Finnhub data provider implementation.

Provides market data, options chains, news, and earnings information via Finnhub API.
Handles rate limiting, caching, and error recovery.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
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


class FinnhubProvider(DataProvider):
    """Finnhub data provider.
    
    Implements DataProvider interface using Finnhub API.
    Handles rate limiting with token bucket algorithm.
    Caches responses to minimize API calls.
    
    Finnhub provides:
    - Real-time and historical stock quotes
    - Company news with sentiment analysis
    - Earnings dates
    - Limited options data (via partner APIs)
    """

    BASE_URL = "https://finnhub.io/api/v1"
    FREE_TIER_CALLS_PER_SECOND = 1
    CACHE_TTL_SECONDS = 300  # 5 minutes

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit_calls_per_second: int = FREE_TIER_CALLS_PER_SECOND,
        cache_ttl_seconds: int = CACHE_TTL_SECONDS,
    ):
        """Initialize Finnhub provider.
        
        Args:
            api_key: Finnhub API key. If None, uses FINNHUB_API_KEY from config.
            rate_limit_calls_per_second: Rate limit for API calls (default: 1 for free tier).
            cache_ttl_seconds: Cache time-to-live in seconds (default: 300).
            
        Raises:
            ValueError: If no API key is provided or configured.
        """
        self.api_key = api_key or config.FINNHUB_API_KEY
        if not self.api_key:
            raise ValueError(
                "Finnhub API key not provided. "
                "Set FINNHUB_API_KEY environment variable or pass api_key parameter."
            )
        
        self.rate_limit_calls_per_second = rate_limit_calls_per_second
        self.cache_ttl_seconds = cache_ttl_seconds
        self.last_call_time = 0.0
        self._response_cache: Dict[str, Tuple[float, any]] = {}
        
        logger.info(
            f"FinnhubProvider initialized with rate limit: "
            f"{rate_limit_calls_per_second} calls/sec"
        )

    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limits.
        
        Implements simple rate limiting based on minimum time between calls.
        """
        current_time = time.time()
        min_interval = 1.0 / self.rate_limit_calls_per_second
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < min_interval:
            wait_time = min_interval - time_since_last_call
            logger.debug(f"Rate limit: waiting {wait_time:.2f}s before next API call")
            time.sleep(wait_time)
        
        self.last_call_time = time.time()

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
        endpoint: str,
        params: Dict[str, str],
        max_retries: int = 3,
    ) -> Optional[Dict]:
        """Make API call to Finnhub with rate limiting and retry logic.
        
        Args:
            endpoint: API endpoint (e.g., "quote", "company-news")
            params: Query parameters for the API call
            max_retries: Maximum number of retries on rate limit
            
        Returns:
            JSON response as dictionary or None on error
            
        Raises:
            RateLimitError: If rate limit is exceeded after retries
        """
        # Create cache key
        cache_key = f"{endpoint}:{','.join(f'{k}={v}' for k, v in sorted(params.items()))}"
        
        # Check cache first
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        # Prepare request
        request_params = {
            "token": self.api_key,
            **params,
        }
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        # Retry loop with exponential backoff
        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()
                
                logger.debug(f"API call: {endpoint} with params {params}")
                response = requests.get(url, params=request_params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # Check for API errors
                if isinstance(data, dict) and "error" in data:
                    logger.error(f"API error: {data['error']}")
                    return None
                
                # Cache successful response
                self._set_cached(cache_key, data)
                return data
                
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:  # Rate limit
                    if attempt < max_retries - 1:
                        wait_time = 60 * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"Rate limit hit. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        raise RateLimitError("Rate limit exceeded after retries")
                else:
                    logger.error(f"HTTP error: {e}")
                    return None
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
                "quote",
                {"symbol": symbol.upper()},
            )
            
            if not data:
                logger.warning(f"No quote data for symbol {symbol}")
                return None
            
            price = data.get("c")  # current price
            bid = data.get("bp")  # bid price
            ask = data.get("ap")  # ask price
            volume = data.get("v")  # volume
            
            if price is None or price == 0:
                logger.warning(f"No price data for symbol {symbol}")
                return None
            
            return Quote(
                symbol=symbol.upper(),
                price=float(price),
                bid=float(bid) if bid and bid > 0 else None,
                ask=float(ask) if ask and ask > 0 else None,
                volume=int(volume) if volume and volume > 0 else None,
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
            # Parse dates to timestamps
            try:
                start_dt = datetime.fromisoformat(start_date)
                end_dt = datetime.fromisoformat(end_date)
            except ValueError:
                logger.error(f"Invalid date format: {start_date} or {end_date}")
                return []
            
            start_ts = int(start_dt.timestamp())
            end_ts = int(end_dt.timestamp())
            
            # Map interval to Finnhub resolution
            resolution_map = {
                "daily": "D",
                "weekly": "W",
                "monthly": "M",
            }
            resolution = resolution_map.get(interval, "D")
            
            data = self._api_call(
                "stock/candle",
                {
                    "symbol": symbol.upper(),
                    "from": str(start_ts),
                    "to": str(end_ts),
                    "resolution": resolution,
                },
            )
            
            if not data or "c" not in data:
                logger.warning(f"No price history data for symbol {symbol}")
                return []
            
            bars = []
            timestamps = data.get("t", [])
            opens = data.get("o", [])
            highs = data.get("h", [])
            lows = data.get("l", [])
            closes = data.get("c", [])
            volumes = data.get("v", [])
            
            for i, ts in enumerate(timestamps):
                try:
                    bar_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                    bar = PriceBar(
                        date=bar_date,
                        open=float(opens[i]) if i < len(opens) else 0,
                        high=float(highs[i]) if i < len(highs) else 0,
                        low=float(lows[i]) if i < len(lows) else 0,
                        close=float(closes[i]) if i < len(closes) else 0,
                        volume=int(volumes[i]) if i < len(volumes) else 0,
                        adjusted_close=float(closes[i]) if i < len(closes) else 0,
                    )
                    bars.append(bar)
                except (ValueError, IndexError) as e:
                    logger.warning(f"Error parsing bar data at index {i}: {e}")
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
        
        Note: Finnhub free tier does not provide options data.
        This method returns an empty list with a warning.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            expiration: Optional specific expiration date (YYYY-MM-DD)
            
        Returns:
            Empty list (Finnhub free tier limitation)
        """
        logger.warning(
            f"Options chain data not available from Finnhub free tier. "
            f"Use Alpha Vantage, yfinance, or Polygon for options data."
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
            # Finnhub company-news endpoint
            data = self._api_call(
                "company-news",
                {
                    "symbol": symbol.upper(),
                    "from": (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d"),
                    "to": datetime.utcnow().strftime("%Y-%m-%d"),
                },
            )
            
            if not data or not isinstance(data, list):
                logger.warning(f"No news data for symbol {symbol}")
                return []
            
            articles = []
            for item in data[:limit]:
                try:
                    # Parse timestamp (Finnhub provides Unix timestamp)
                    published_ts = item.get("datetime")
                    published_at = None
                    if published_ts:
                        published_at = datetime.fromtimestamp(published_ts)
                    
                    article = NewsArticle(
                        symbol=symbol.upper(),
                        title=item.get("headline", ""),
                        description=item.get("summary"),
                        url=item.get("url"),
                        source=item.get("source"),
                        published_at=published_at,
                        sentiment=None,  # Finnhub free tier doesn't provide sentiment
                    )
                    articles.append(article)
                except Exception as e:
                    logger.warning(f"Error parsing news item: {e}")
                    continue
            
            # Sort by date descending (newest first)
            articles.sort(key=lambda a: a.published_at or datetime.min, reverse=True)
            return articles
            
        except Exception as e:
            logger.error(f"Error getting news for {symbol}: {e}", exc_info=True)
            return []

    def get_earnings_date(self, symbol: str) -> Optional[EarningsDate]:
        """Get next earnings date for a symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            
        Returns:
            EarningsDate object with next earnings info, or None if not available
        """
        try:
            # Finnhub earnings calendar endpoint
            data = self._api_call(
                "calendar/earnings",
                {
                    "symbol": symbol.upper(),
                    "from": datetime.utcnow().strftime("%Y-%m-%d"),
                    "to": (datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d"),
                },
            )
            
            if not data or "earningsCalendar" not in data or not data["earningsCalendar"]:
                logger.warning(f"No earnings date for symbol {symbol}")
                return None
            
            # Get the first (next) earnings date
            earnings_item = data["earningsCalendar"][0]
            
            earnings_date = earnings_item.get("date")
            if not earnings_date:
                return None
            
            return EarningsDate(
                symbol=symbol.upper(),
                date=earnings_date,
                time=earnings_item.get("hour"),
                eps_estimate=earnings_item.get("epsEstimate"),
                eps_actual=earnings_item.get("epsActual"),
                revenue_estimate=earnings_item.get("revenueEstimate"),
                revenue_actual=earnings_item.get("revenueActual"),
            )
            
        except Exception as e:
            logger.error(f"Error getting earnings date for {symbol}: {e}", exc_info=True)
            return None
