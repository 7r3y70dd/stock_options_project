"""Data sources module for market data providers.

Provides abstract DataProvider interface and concrete implementations:
- MockDataProvider: Synthetic data for testing
- AlphaVantageProvider: Alpha Vantage API integration
- YfinanceProvider: yfinance library integration (dev fallback)
"""

from app.data_sources.data_provider import (
    DataProvider,
    Quote,
    PriceBar,
    OptionChainEntry,
    NewsArticle,
    EarningsDate,
)
from app.data_sources.mock_provider import MockDataProvider
from app.data_sources.alpha_vantage_provider import AlphaVantageProvider
from app.data_sources.yfinance_provider import YfinanceProvider

__all__ = [
    "DataProvider",
    "Quote",
    "PriceBar",
    "OptionChainEntry",
    "NewsArticle",
    "EarningsDate",
    "MockDataProvider",
    "AlphaVantageProvider",
    "YfinanceProvider",
]
