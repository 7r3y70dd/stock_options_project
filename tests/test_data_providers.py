"""Tests for data provider interface and implementations.

Verifies that:
1. DataProvider interface is properly defined
2. MockDataProvider implements all required methods
3. AlphaVantageProvider implements all required methods
4. Mock data is realistic and consistent
5. App code can swap providers without changes
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from app.data_sources import (
    DataProvider,
    MockDataProvider,
    AlphaVantageProvider,
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


class TestAlphaVantageProvider:
    """Test AlphaVantageProvider implementation."""

    def test_alpha_vantage_provider_is_data_provider(self):
        """Test that AlphaVantageProvider is a DataProvider."""
        with patch.dict('os.environ', {'ALPHAVANTAGE_API_KEY': 'test-key'}):
            provider = AlphaVantageProvider(api_key='test-key')
            assert isinstance(provider, DataProvider)

    def test_alpha_vantage_requires_api_key(self):
        """Test that AlphaVantageProvider requires API key."""
        with pytest.raises(ValueError, match="API key not provided"):
            AlphaVantageProvider(api_key=None)

    @patch('app.data_sources.alpha_vantage_provider.requests.get')
    def test_get_quote_success(self, mock_get):
        """Test get_quote with successful API response."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Global Quote": {
                "01. symbol": "AAPL",
                "05. price": "150.25",
                "08. bid": "150.20",
                "09. ask": "150.30",
                "06. volume": "1000000",
            }
        }
        mock_get.return_value = mock_response
        
        provider = AlphaVantageProvider(api_key='test-key')
        quote = provider.get_quote("AAPL")
        
        assert quote is not None
        assert quote.symbol == "AAPL"
        assert quote.price == 150.25
        assert quote.bid == 150.20
        assert quote.ask == 150.30

    @patch('app.data_sources.alpha_vantage_provider.requests.get')
    def test_get_quote_no_data(self, mock_get):
        """Test get_quote when no data is available."""
        mock_response = Mock()
        mock_response.json.return_value = {"Global Quote": {}}
        mock_get.return_value = mock_response
        
        provider = AlphaVantageProvider(api_key='test-key')
        quote = provider.get_quote("UNKNOWN")
        
        assert quote is None

    @patch('app.data_sources.alpha_vantage_provider.requests.get')
    def test_get_price_history_success(self, mock_get):
        """Test get_price_history with successful API response."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Time Series (Daily)": {
                "2024-01-15": {
                    "1. open": "150.0",
                    "2. high": "151.0",
                    "3. low": "149.0",
                    "4. close": "150.5",
                    "5. adjusted close": "150.5",
                    "6. volume": "1000000",
                },
                "2024-01-14": {
                    "1. open": "149.5",
                    "2. high": "150.5",
                    "3. low": "149.0",
                    "4. close": "150.0",
                    "5. adjusted close": "150.0",
                    "6. volume": "900000",
                },
            }
        }
        mock_get.return_value = mock_response
        
        provider = AlphaVantageProvider(api_key='test-key')
        bars = provider.get_price_history("AAPL", "2024-01-14", "2024-01-15")
        
        assert len(bars) == 2
        assert bars[0].date == "2024-01-14"
        assert bars[0].close == 150.0
        assert bars[1].date == "2024-01-15"
        assert bars[1].close == 150.5

    @patch('app.data_sources.alpha_vantage_provider.requests.get')
    def test_get_news_success(self, mock_get):
        """Test get_news with successful API response."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "feed": [
                {
                    "title": "Apple announces new features",
                    "summary": "Apple announced new features today",
                    "url": "https://example.com/news/1",
                    "source": "Example News",
                    "time_published": "2024-01-15T10:00:00Z",
                    "overall_sentiment_score": "0.5",
                },
                {
                    "title": "Apple stock rises",
                    "summary": "Apple stock rose today",
                    "url": "https://example.com/news/2",
                    "source": "Example News",
                    "time_published": "2024-01-15T09:00:00Z",
                    "overall_sentiment_score": "-0.3",
                },
            ]
        }
        mock_get.return_value = mock_response
        
        provider = AlphaVantageProvider(api_key='test-key')
        articles = provider.get_news("AAPL", limit=2)
        
        assert len(articles) == 2
        assert articles[0].title == "Apple announces new features"
        assert articles[0].sentiment == "positive"
        assert articles[1].sentiment == "negative"

    def test_get_options_chain_not_supported(self):
        """Test that get_options_chain returns empty list (not supported in free tier)."""
        provider = AlphaVantageProvider(api_key='test-key')
        chain = provider.get_options_chain("AAPL")
        assert chain == []

    def test_get_earnings_date_not_supported(self):
        """Test that get_earnings_date returns None (not supported in free tier)."""
        provider = AlphaVantageProvider(api_key='test-key')
        earnings = provider.get_earnings_date("AAPL")
        assert earnings is None

    @patch('app.data_sources.alpha_vantage_provider.requests.get')
    @patch('app.data_sources.alpha_vantage_provider.time.sleep')
    def test_rate_limit_handling(self, mock_sleep, mock_get):
        """Test that rate limiting is handled correctly."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute."
        }
        mock_get.return_value = mock_response
        
        provider = AlphaVantageProvider(api_key='test-key', rate_limit_calls_per_minute=5)
        
        # This should trigger rate limit handling
        with pytest.raises(Exception):  # RateLimitError after retries
            provider.get_quote("AAPL")

    def test_caching_works(self):
        """Test that response caching works."""
        with patch('app.data_sources.alpha_vantage_provider.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "Global Quote": {
                    "05. price": "150.25",
                    "08. bid": "150.20",
                    "09. ask": "150.30",
                }
            }
            mock_get.return_value = mock_response
            
            provider = AlphaVantageProvider(api_key='test-key', cache_ttl_seconds=300)
            
            # First call should hit API
            quote1 = provider.get_quote("AAPL")
            assert mock_get.call_count == 1
            
            # Second call should use cache
            quote2 = provider.get_quote("AAPL")
            assert mock_get.call_count == 1  # No additional call
            assert quote1.price == quote2.price


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

    def test_provider_swap_in_service(self):
        """Test that providers can be swapped in services."""
        from services.options_service import OptionsService
        from services import RiskLevel
        
        # Create service with mock provider
        mock_provider = MockDataProvider(seed=42)
        service = OptionsService(risk_level=RiskLevel.MEDIUM, data_provider=mock_provider)
        assert service.data_provider == mock_provider
        
        # Create service with different provider
        mock_provider2 = MockDataProvider(seed=99)
        service2 = OptionsService(risk_level=RiskLevel.MEDIUM, data_provider=mock_provider2)
        assert service2.data_provider == mock_provider2
        assert service.data_provider != service2.data_provider
