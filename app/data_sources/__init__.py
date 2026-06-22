"""External data source integrations (market data, news, etc.).

Provides abstract interface for data providers and concrete implementations.
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

__all__ = [
    "DataProvider",
    "Quote",
    "PriceBar",
    "OptionChainEntry",
    "NewsArticle",
    "EarningsDate",
    "MockDataProvider",
]
