"""Data sources package.

Provides data provider interface and implementations.
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
from app.data_sources.finnhub_provider import FinnhubProvider

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
    "FinnhubProvider",
]
