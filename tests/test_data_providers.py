"""Tests for data provider interface and mock implementation.

Verifies that:
1. DataProvider interface is properly defined
2. MockDataProvider implements all required methods
3. Mock data is realistic and consistent
4. App code can swap providers without changes
"""

import pytest
from datetime import datetime, timedelta

from app.data_sources import (
    DataProvider,
    MockDataProvider,
    Quote,
    PriceBar,
    OptionChainEntry,
    NewsArticle,
    EarningsDate,
)


class TestDataProviderInterface:
    """Test that DataProvider interface is properly defined."""

    def test_data_provider_is_abstract(self):
        """Test that DataProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DataProvider()

    def test_data_provider_has_required_methods(self):
        """Test that DataProvider defines all required methods."""
        required_methods = [
            "get_quote",
            "get_price_history",
            "get_options_chain",
            "get_news",
            "get_earnings_date",
        ]
        for method in required_methods:
            assert hasattr(DataProvider, method), f"DataProvider missing method: {method}"


class TestMockDataProvider:
    """Test MockDataProvider implementation."""

    @pytest.fixture
    def provider(self):
        """Create a mock provider instance."""
        return MockDataProvider(seed=42)

    def test_mock_provider_is_data_provider(self, provider):
        """Test that MockDataProvider is a DataProvider."""
        assert isinstance(provider, DataProvider)

    def test_get_quote_returns_quote_object(self, provider):
        """Test get_quote returns Quote object with required fields."""
        quote = provider.get_quote("AAPL")
        assert quote is not None
        assert isinstance(quote, Quote)
        assert quote.symbol == "AAPL"
        assert quote.price > 0
        assert quote.bid is not None
        assert quote.ask is not None
        assert quote.bid < quote.ask
        assert quote.timestamp is not None

    def test_get_quote_unknown_symbol(self, provider):
        """Test get_quote returns None for unknown symbol."""
        quote = provider.get_quote("UNKNOWN")
        assert quote is None

    def test_get_quote_case_insensitive(self, provider):
        """Test get_quote is case insensitive."""
        quote_upper = provider.get_quote("AAPL")
        quote_lower = provider.get_quote("aapl")
        assert quote_upper is not None
        assert quote_lower is not None
        assert quote_upper.symbol == quote_lower.symbol

    def test_get_price_history_returns_bars(self, provider):
        """Test get_price_history returns list of PriceBar objects."""
        start = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        end = datetime.utcnow().strftime("%Y-%m-%d")
        bars = provider.get_price_history("AAPL", start, end)
        
        assert isinstance(bars, list)
        assert len(bars) > 0
        for bar in bars:
            assert isinstance(bar, PriceBar)
            assert bar.open > 0
            assert bar.high >= bar.low
            assert bar.high >= bar.close
            assert bar.low <= bar.close
            assert bar.volume > 0

    def test_get_price_history_sorted_by_date(self, provider):
        """Test get_price_history returns bars sorted by date."""
        start = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        end = datetime.utcnow().strftime("%Y-%m-%d")
        bars = provider.get_price_history("AAPL", start, end)
        
        dates = [bar.date for bar in bars]
        assert dates == sorted(dates)

    def test_get_price_history_invalid_dates(self, provider):
        """Test get_price_history handles invalid dates gracefully."""
        bars = provider.get_price_history("AAPL", "invalid", "dates")
        assert bars == []

    def test_get_price_history_unknown_symbol(self, provider):
        """Test get_price_history returns empty list for unknown symbol."""
        start = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        end = datetime.utcnow().strftime("%Y-%m-%d")
        bars = provider.get_price_history("UNKNOWN", start, end)
        assert bars == []

    def test_get_options_chain_returns_entries(self, provider):
        """Test get_options_chain returns list of OptionChainEntry objects."""
        chain = provider.get_options_chain("AAPL")
        
        assert isinstance(chain, list)
        assert len(chain) > 0
        for entry in chain:
            assert isinstance(entry, OptionChainEntry)
            assert entry.symbol == "AAPL"
            assert entry.contract_type in ["call", "put"]
            assert entry.strike > 0
            assert entry.bid is not None
            assert entry.ask is not None
            assert entry.bid < entry.ask
            assert entry.volume >= 0
            assert entry.open_interest >= 0

    def test_get_options_chain_specific_expiration(self, provider):
        """Test get_options_chain with specific expiration."""
        expiration = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")
        chain = provider.get_options_chain("AAPL", expiration=expiration)
        
        assert len(chain) > 0
        for entry in chain:
            assert entry.expiration == expiration

    def test_get_options_chain_unknown_symbol(self, provider):
        """Test get_options_chain returns empty list for unknown symbol."""
        chain = provider.get_options_chain("UNKNOWN")
        assert chain == []

    def test_get_news_returns_articles(self, provider):
        """Test get_news returns list of NewsArticle objects."""
        articles = provider.get_news("AAPL")
        
        assert isinstance(articles, list)
        assert len(articles) > 0
        for article in articles:
            assert isinstance(article, NewsArticle)
            assert article.symbol == "AAPL"
            assert article.title is not None
            assert len(article.title) > 0
            assert article.published_at is not None

    def test_get_news_respects_limit(self, provider):
        """Test get_news respects limit parameter."""
        articles = provider.get_news("AAPL", limit=2)
        assert len(articles) <= 2

    def test_get_news_sorted_by_date_descending(self, provider):
        """Test get_news returns articles sorted by date descending."""
        articles = provider.get_news("AAPL")
        dates = [article.published_at for article in articles]
        assert dates == sorted(dates, reverse=True)

    def test_get_news_unknown_symbol(self, provider):
        """Test get_news returns empty list for unknown symbol."""
        articles = provider.get_news("UNKNOWN")
        assert articles == []

    def test_get_earnings_date_returns_earnings_date(self, provider):
        """Test get_earnings_date returns EarningsDate object."""
        earnings = provider.get_earnings_date("AAPL")
        
        assert earnings is not None
        assert isinstance(earnings, EarningsDate)
        assert earnings.symbol == "AAPL"
        assert earnings.date is not None
        assert len(earnings.date) == 10  # YYYY-MM-DD format

    def test_get_earnings_date_unknown_symbol(self, provider):
        """Test get_earnings_date returns None for unknown symbol."""
        earnings = provider.get_earnings_date("UNKNOWN")
        assert earnings is None

    def test_mock_provider_reproducible_with_seed(self):
        """Test that MockDataProvider produces reproducible data with same seed."""
        provider1 = MockDataProvider(seed=42)
        provider2 = MockDataProvider(seed=42)
        
        quote1 = provider1.get_quote("AAPL")
        quote2 = provider2.get_quote("AAPL")
        
        assert quote1.price == quote2.price
        assert quote1.bid == quote2.bid
        assert quote1.ask == quote2.ask

    def test_mock_provider_different_with_different_seed(self):
        """Test that MockDataProvider produces different data with different seeds."""
        provider1 = MockDataProvider(seed=42)
        provider2 = MockDataProvider(seed=99)
        
        quote1 = provider1.get_quote("AAPL")
        quote2 = provider2.get_quote("AAPL")
        
        # Prices should be different (with very high probability)
        assert quote1.price != quote2.price


class TestDataProviderIntegration:
    """Test that app code can use DataProvider interface."""

    def test_provider_can_be_injected(self):
        """Test that DataProvider can be injected as dependency."""
        provider: DataProvider = MockDataProvider(seed=42)
        
        # Should be able to call all methods
        quote = provider.get_quote("AAPL")
        assert quote is not None
        
        start = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        end = datetime.utcnow().strftime("%Y-%m-%d")
        bars = provider.get_price_history("AAPL", start, end)
        assert len(bars) > 0
        
        chain = provider.get_options_chain("AAPL")
        assert len(chain) > 0
        
        news = provider.get_news("AAPL")
        assert len(news) > 0
        
        earnings = provider.get_earnings_date("AAPL")
        assert earnings is not None

    def test_multiple_providers_can_coexist(self):
        """Test that multiple provider instances can coexist."""
        provider1 = MockDataProvider(seed=1)
        provider2 = MockDataProvider(seed=2)
        
        quote1 = provider1.get_quote("AAPL")
        quote2 = provider2.get_quote("AAPL")
        
        # Both should work independently
        assert quote1 is not None
        assert quote2 is not None
        assert quote1.symbol == quote2.symbol
