"""Mock data provider for testing and development.

Provides realistic but synthetic market data without requiring API keys or network calls.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from random import Random

from app.data_sources.data_provider import (
    DataProvider,
    Quote,
    PriceBar,
    OptionChainEntry,
    NewsArticle,
    EarningsDate,
)

logger = logging.getLogger(__name__)


class MockDataProvider(DataProvider):
    """Mock data provider for testing and development.
    
    Generates realistic synthetic data for testing without external API dependencies.
    """

    # Mock data for common symbols
    MOCK_PRICES = {
        "AAPL": 150.0,
        "MSFT": 380.0,
        "GOOGL": 140.0,
        "TSLA": 250.0,
        "AMZN": 170.0,
    }

    MOCK_NEWS = {
        "AAPL": [
            "Apple announces new iPhone features",
            "Apple stock reaches all-time high",
            "Apple expands services business",
        ],
        "MSFT": [
            "Microsoft launches new AI features",
            "Microsoft cloud revenue grows",
            "Microsoft partners with OpenAI",
        ],
    }

    MOCK_EARNINGS = {
        "AAPL": "2024-02-01",
        "MSFT": "2024-01-30",
        "GOOGL": "2024-01-30",
    }

    def __init__(self, seed: Optional[int] = None):
        """Initialize mock provider with optional random seed.
        
        Args:
            seed: Optional random seed for reproducible data
        """
        self._rng = Random(seed)
        logger.info("MockDataProvider initialized")

    def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get mock current price quote.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Quote with synthetic but realistic data
        """
        base_price = self.MOCK_PRICES.get(symbol.upper())
        if base_price is None:
            logger.warning(f"No mock data for symbol {symbol}")
            return None

        # Add some random variation
        variation = base_price * self._rng.uniform(-0.02, 0.02)
        price = base_price + variation
        bid = price - 0.01
        ask = price + 0.01

        return Quote(
            symbol=symbol.upper(),
            price=round(price, 2),
            bid=round(bid, 2),
            ask=round(ask, 2),
            volume=self._rng.randint(1000000, 50000000),
            timestamp=datetime.utcnow(),
        )

    def get_price_history(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "daily",
    ) -> List[PriceBar]:
        """Get mock historical price data.
        
        Args:
            symbol: Stock ticker symbol
            start_date: Start date in ISO format
            end_date: End date in ISO format
            interval: Data interval (only "daily" supported in mock)
            
        Returns:
            List of synthetic PriceBar objects
        """
        base_price = self.MOCK_PRICES.get(symbol.upper())
        if base_price is None:
            logger.warning(f"No mock data for symbol {symbol}")
            return []

        try:
            start = datetime.fromisoformat(start_date).date()
            end = datetime.fromisoformat(end_date).date()
        except ValueError:
            logger.error(f"Invalid date format: {start_date} or {end_date}")
            return []

        bars = []
        current_date = start
        current_price = base_price

        while current_date <= end:
            # Skip weekends
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            # Generate realistic OHLCV data
            daily_change = self._rng.uniform(-0.03, 0.03)
            open_price = current_price
            close_price = current_price * (1 + daily_change)
            high_price = max(open_price, close_price) * self._rng.uniform(1.0, 1.02)
            low_price = min(open_price, close_price) * self._rng.uniform(0.98, 1.0)

            bar = PriceBar(
                date=current_date.isoformat(),
                open=round(open_price, 2),
                high=round(high_price, 2),
                low=round(low_price, 2),
                close=round(close_price, 2),
                volume=self._rng.randint(1000000, 50000000),
                adjusted_close=round(close_price, 2),
            )
            bars.append(bar)
            current_price = close_price
            current_date += timedelta(days=1)

        return bars

    def get_options_chain(
        self,
        symbol: str,
        expiration: Optional[str] = None,
    ) -> List[OptionChainEntry]:
        """Get mock options chain.
        
        Args:
            symbol: Stock ticker symbol
            expiration: Optional specific expiration date
            
        Returns:
            List of synthetic OptionChainEntry objects
        """
        base_price = self.MOCK_PRICES.get(symbol.upper())
        if base_price is None:
            logger.warning(f"No mock data for symbol {symbol}")
            return []

        # Generate expirations if not specified
        if expiration is None:
            expirations = [
                (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d"),
                (datetime.utcnow() + timedelta(days=14)).strftime("%Y-%m-%d"),
                (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d"),
            ]
        else:
            expirations = [expiration]

        chain = []
        for exp in expirations:
            # Generate strikes around current price
            strikes = [
                base_price * 0.90,
                base_price * 0.95,
                base_price,
                base_price * 1.05,
                base_price * 1.10,
            ]

            for strike in strikes:
                for contract_type in ["call", "put"]:
                    # Calculate days to expiration
                    try:
                        exp_date = datetime.fromisoformat(exp).date()
                        today = datetime.utcnow().date()
                        dte = (exp_date - today).days
                    except ValueError:
                        dte = 30

                    # Generate realistic option prices
                    if contract_type == "call":
                        intrinsic = max(0, base_price - strike)
                        time_value = (strike * 0.02) * (dte / 30.0)
                    else:
                        intrinsic = max(0, strike - base_price)
                        time_value = (strike * 0.02) * (dte / 30.0)

                    mid_price = intrinsic + time_value
                    bid = mid_price * 0.98
                    ask = mid_price * 1.02

                    entry = OptionChainEntry(
                        symbol=symbol.upper(),
                        expiration=exp,
                        strike=round(strike, 2),
                        contract_type=contract_type,
                        bid=round(bid, 2),
                        ask=round(ask, 2),
                        last=round(mid_price, 2),
                        volume=self._rng.randint(10, 10000),
                        open_interest=self._rng.randint(100, 100000),
                        implied_volatility=round(self._rng.uniform(0.15, 0.50), 2),
                        delta=round(self._rng.uniform(-1.0, 1.0), 2),
                        gamma=round(self._rng.uniform(0.0, 0.1), 3),
                        theta=round(self._rng.uniform(-0.1, 0.0), 3),
                        vega=round(self._rng.uniform(0.0, 0.5), 2),
                        rho=round(self._rng.uniform(-0.1, 0.1), 2),
                    )
                    chain.append(entry)

        return chain

    def get_news(self, symbol: str, limit: int = 10) -> List[NewsArticle]:
        """Get mock news articles.
        
        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of articles
            
        Returns:
            List of synthetic NewsArticle objects
        """
        symbol_upper = symbol.upper()
        headlines = self.MOCK_NEWS.get(symbol_upper, [])

        if not headlines:
            logger.warning(f"No mock news for symbol {symbol}")
            return []

        articles = []
        for i, headline in enumerate(headlines[:limit]):
            article = NewsArticle(
                symbol=symbol_upper,
                title=headline,
                description=f"Mock news article about {symbol_upper}",
                url=f"https://example.com/news/{i}",
                source="Mock News",
                published_at=datetime.utcnow() - timedelta(hours=i),
                sentiment=self._rng.choice(["positive", "negative", "neutral"]),
            )
            articles.append(article)

        return articles

    def get_earnings_date(self, symbol: str) -> Optional[EarningsDate]:
        """Get mock earnings date.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Synthetic EarningsDate object or None
        """
        symbol_upper = symbol.upper()
        earnings_date = self.MOCK_EARNINGS.get(symbol_upper)

        if earnings_date is None:
            logger.warning(f"No mock earnings data for symbol {symbol}")
            return None

        return EarningsDate(
            symbol=symbol_upper,
            date=earnings_date,
            time=self._rng.choice(["before_open", "after_close"]),
            eps_estimate=round(self._rng.uniform(1.0, 5.0), 2),
            eps_actual=None,
            revenue_estimate=round(self._rng.uniform(50000, 500000), 0),
            revenue_actual=None,
        )
