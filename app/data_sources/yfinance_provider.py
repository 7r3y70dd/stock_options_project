"""yfinance data provider implementation.

Provides market data, options chains, and news via yfinance.
Warning: yfinance data is not suitable for production trading.
Use only for development, backtesting, and research.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

from app.data_sources.data_provider import (
    DataProvider,
    Quote,
    PriceBar,
    OptionChainEntry,
    NewsArticle,
    EarningsDate,
)

logger = logging.getLogger(__name__)

# Production warning
PRODUCTION_WARNING = (
    "WARNING: yfinance data is not suitable for production trading. "
    "Data may be delayed, inaccurate, or unavailable. "
    "Use only for development, backtesting, and research. "
    "For production trading, use official data providers (Polygon, Alpaca, Tradier, etc.)."
)


class YfinanceProvider(DataProvider):
    """yfinance data provider.
    
    Implements DataProvider interface using yfinance library.
    Provides convenient development fallback for historical prices and options chains.
    
    WARNING: Data is not suitable for production trading.
    """

    def __init__(self, warn_on_init: bool = True):
        """Initialize yfinance provider.
        
        Args:
            warn_on_init: If True, log production warning on initialization.
            
        Raises:
            ImportError: If yfinance is not installed.
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError(
                "yfinance is not installed. Install it with: pip install yfinance"
            )
        
        if warn_on_init:
            logger.warning(PRODUCTION_WARNING)
        
        logger.info("YfinanceProvider initialized")

    def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get current price quote for a symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            
        Returns:
            Quote object with current price, or None if not available
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            data = ticker.info
            
            if not data or "currentPrice" not in data:
                logger.warning(f"No quote data for symbol {symbol}")
                return None
            
            price = data.get("currentPrice")
            bid = data.get("bid")
            ask = data.get("ask")
            volume = data.get("volume")
            
            if price is None:
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
            # Map interval to yfinance period
            interval_map = {
                "daily": "1d",
                "weekly": "1wk",
                "monthly": "1mo",
            }
            yf_interval = interval_map.get(interval, "1d")
            
            ticker = yf.Ticker(symbol.upper())
            hist = ticker.history(start=start_date, end=end_date, interval=yf_interval)
            
            if hist.empty:
                logger.warning(f"No price history for symbol {symbol}")
                return []
            
            bars = []
            for date, row in hist.iterrows():
                try:
                    bar = PriceBar(
                        date=date.strftime("%Y-%m-%d"),
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=int(row["Volume"]),
                        adjusted_close=float(row.get("Adj Close", row["Close"])),
                    )
                    bars.append(bar)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error parsing bar data for {date}: {e}")
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
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            expiration: Optional specific expiration date (YYYY-MM-DD).
                       If None, return all available expirations.
            
        Returns:
            List of OptionChainEntry objects for all strikes and types
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            
            # Get available expirations
            expirations = ticker.options
            if not expirations:
                logger.warning(f"No options data for symbol {symbol}")
                return []
            
            # Filter to specific expiration if provided
            if expiration:
                if expiration not in expirations:
                    logger.warning(f"Expiration {expiration} not available for {symbol}")
                    return []
                expirations = [expiration]
            
            chain = []
            for exp in expirations:
                try:
                    opt_chain = ticker.option_chain(exp)
                    
                    # Process calls
                    for _, row in opt_chain.calls.iterrows():
                        entry = OptionChainEntry(
                            symbol=symbol.upper(),
                            expiration=exp,
                            strike=float(row["strike"]),
                            contract_type="call",
                            bid=float(row["bid"]) if row["bid"] > 0 else None,
                            ask=float(row["ask"]) if row["ask"] > 0 else None,
                            last=float(row["lastPrice"]) if row["lastPrice"] > 0 else None,
                            volume=int(row["volume"]) if row["volume"] > 0 else None,
                            open_interest=int(row["openInterest"]) if row["openInterest"] > 0 else None,
                            implied_volatility=float(row["impliedVolatility"]) if row["impliedVolatility"] > 0 else None,
                        )
                        chain.append(entry)
                    
                    # Process puts
                    for _, row in opt_chain.puts.iterrows():
                        entry = OptionChainEntry(
                            symbol=symbol.upper(),
                            expiration=exp,
                            strike=float(row["strike"]),
                            contract_type="put",
                            bid=float(row["bid"]) if row["bid"] > 0 else None,
                            ask=float(row["ask"]) if row["ask"] > 0 else None,
                            last=float(row["lastPrice"]) if row["lastPrice"] > 0 else None,
                            volume=int(row["volume"]) if row["volume"] > 0 else None,
                            open_interest=int(row["openInterest"]) if row["openInterest"] > 0 else None,
                            implied_volatility=float(row["impliedVolatility"]) if row["impliedVolatility"] > 0 else None,
                        )
                        chain.append(entry)
                        
                except Exception as e:
                    logger.warning(f"Error fetching options for {symbol} expiration {exp}: {e}")
                    continue
            
            return chain
            
        except Exception as e:
            logger.error(f"Error getting options chain for {symbol}: {e}", exc_info=True)
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
            ticker = yf.Ticker(symbol.upper())
            news = ticker.news
            
            if not news:
                logger.warning(f"No news data for symbol {symbol}")
                return []
            
            articles = []
            for item in news[:limit]:
                try:
                    article = NewsArticle(
                        symbol=symbol.upper(),
                        title=item.get("title", ""),
                        description=item.get("summary"),
                        url=item.get("link"),
                        source=item.get("source"),
                        published_at=datetime.fromtimestamp(item.get("providerPublishTime", 0)) if item.get("providerPublishTime") else None,
                    )
                    articles.append(article)
                except Exception as e:
                    logger.warning(f"Error parsing news item: {e}")
                    continue
            
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
            ticker = yf.Ticker(symbol.upper())
            data = ticker.info
            
            earnings_date = data.get("earningsDate")
            if not earnings_date:
                logger.warning(f"No earnings date for symbol {symbol}")
                return None
            
            # earnings_date is typically a list [start, end] or a single timestamp
            if isinstance(earnings_date, list) and len(earnings_date) > 0:
                earnings_ts = earnings_date[0]
            else:
                earnings_ts = earnings_date
            
            if isinstance(earnings_ts, (int, float)):
                earnings_dt = datetime.fromtimestamp(earnings_ts)
            else:
                earnings_dt = earnings_ts
            
            return EarningsDate(
                symbol=symbol.upper(),
                date=earnings_dt.strftime("%Y-%m-%d"),
                eps_estimate=data.get("epsTrailingTwelveMonths"),
                revenue_estimate=data.get("totalRevenue"),
            )
            
        except Exception as e:
            logger.error(f"Error getting earnings date for {symbol}: {e}", exc_info=True)
            return None
