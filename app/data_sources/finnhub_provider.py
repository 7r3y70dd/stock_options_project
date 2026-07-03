"""Finnhub data provider implementation.

Provides access to Finnhub API for quotes, price history, options chains, news, and earnings data.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import requests

from app.data_sources.data_provider import (
    DataProvider,
    Quote,
    PriceBar,
    OptionChainEntry,
    NewsArticle,
    EarningsDate,
)

logger = logging.getLogger(__name__)


class FinnhubProvider(DataProvider):
    """Finnhub data provider.
    
    Provides market data from Finnhub API.
    Requires FINNHUB_API_KEY environment variable or api_key parameter.
    """

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Finnhub provider.
        
        Args:
            api_key: Finnhub API key. If not provided, uses FINNHUB_API_KEY env var.
            
        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        import os
        
        self.api_key = api_key or os.environ.get('FINNHUB_API_KEY')
        if not self.api_key:
            raise ValueError("Finnhub API key not provided and FINNHUB_API_KEY not set")

    def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get current quote for symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            Quote object or None if not found
        """
        try:
            url = f"{self.BASE_URL}/quote"
            params = {"symbol": symbol.upper(), "token": self.api_key}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data or data.get('c') is None:
                return None
            
            return Quote(
                symbol=symbol.upper(),
                price=float(data.get('c', 0)),
                bid=float(data.get('bp', data.get('c', 0))),
                ask=float(data.get('ap', data.get('c', 0))),
                timestamp=datetime.utcnow().isoformat(),
            )
        except Exception as e:
            logger.warning(f"Error fetching quote for {symbol}: {e}")
            return None

    def get_price_history(
        self,
        symbol: str,
        start: str,
        end: str,
    ) -> List[PriceBar]:
        """Get price history for symbol.
        
        Args:
            symbol: Stock symbol
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            
        Returns:
            List of PriceBar objects
        """
        try:
            url = f"{self.BASE_URL}/stock/candle"
            params = {
                "symbol": symbol.upper(),
                "resolution": "D",
                "from": int(datetime.strptime(start, "%Y-%m-%d").timestamp()),
                "to": int(datetime.strptime(end, "%Y-%m-%d").timestamp()),
                "token": self.api_key,
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('o'):
                return []
            
            bars = []
            for i in range(len(data['o'])):
                bars.append(
                    PriceBar(
                        date=datetime.fromtimestamp(data['t'][i]).strftime("%Y-%m-%d"),
                        open=float(data['o'][i]),
                        high=float(data['h'][i]),
                        low=float(data['l'][i]),
                        close=float(data['c'][i]),
                        volume=int(data['v'][i]),
                    )
                )
            
            return sorted(bars, key=lambda x: x.date)
        except Exception as e:
            logger.warning(f"Error fetching price history for {symbol}: {e}")
            return []

    def get_options_chain(
        self,
        symbol: str,
        expiration: Optional[str] = None,
    ) -> List[OptionChainEntry]:
        """Get options chain for symbol.
        
        Args:
            symbol: Stock symbol
            expiration: Optional expiration date (YYYY-MM-DD)
            
        Returns:
            List of OptionChainEntry objects
        """
        try:
            url = f"{self.BASE_URL}/stock/option-chain"
            params = {"symbol": symbol.upper(), "token": self.api_key}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data or 'data' not in data:
                return []
            
            entries = []
            for option in data['data']:
                if expiration and option.get('expirationDate') != expiration:
                    continue
                
                entries.append(
                    OptionChainEntry(
                        symbol=symbol.upper(),
                        expiration=option.get('expirationDate', ''),
                        strike=float(option.get('strike', 0)),
                        contract_type=option.get('type', 'call').lower(),
                        bid=float(option.get('bid', 0)),
                        ask=float(option.get('ask', 0)),
                        volume=int(option.get('volume', 0)),
                        open_interest=int(option.get('openInterest', 0)),
                        implied_volatility=float(option.get('impliedVolatility', 0)),
                    )
                )
            
            return entries
        except Exception as e:
            logger.warning(f"Error fetching options chain for {symbol}: {e}")
            return []

    def get_news(
        self,
        symbol: str,
        limit: int = 10,
    ) -> List[NewsArticle]:
        """Get news articles for symbol.
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of articles to return
            
        Returns:
            List of NewsArticle objects
        """
        try:
            url = f"{self.BASE_URL}/company-news"
            params = {
                "symbol": symbol.upper(),
                "limit": limit,
                "token": self.api_key,
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                logger.warning(f"No news data for symbol {symbol}")
                return []
            
            articles = []
            for item in data:
                articles.append(
                    NewsArticle(
                        symbol=symbol.upper(),
                        title=item.get('headline', ''),
                        description=item.get('summary', ''),
                        url=item.get('url', ''),
                        source=item.get('source', ''),
                        published_at=datetime.fromtimestamp(item.get('datetime', 0)),
                    )
                )
            
            return sorted(articles, key=lambda x: x.published_at, reverse=True)[:limit]
        except Exception as e:
            logger.warning(f"Error fetching news for {symbol}: {e}")
            return []

    def get_earnings_date(self, symbol: str) -> Optional[EarningsDate]:
        """Get next earnings date for symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            EarningsDate object or None if not found
        """
        try:
            url = f"{self.BASE_URL}/calendar/earnings"
            params = {
                "symbol": symbol.upper(),
                "token": self.api_key,
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data or 'earningsCalendar' not in data or not data['earningsCalendar']:
                return None
            
            # Get the first (next) earnings date
            earnings = data['earningsCalendar'][0]
            
            return EarningsDate(
                symbol=symbol.upper(),
                date=earnings.get('date', ''),
                time=earnings.get('hour', ''),
                eps_estimate=float(earnings.get('epsEstimate')) if earnings.get('epsEstimate') is not None else None,
                eps_actual=float(earnings.get('epsActual')) if earnings.get('epsActual') is not None else None,
                revenue_estimate=float(earnings.get('revenueEstimate')) if earnings.get('revenueEstimate') is not None else None,
                revenue_actual=float(earnings.get('revenueActual')) if earnings.get('revenueActual') is not None else None,
            )
        except Exception as e:
            logger.warning(f"Error fetching earnings date for {symbol}: {e}")
            return None
