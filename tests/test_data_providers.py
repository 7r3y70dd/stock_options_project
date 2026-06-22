"""Tests for data provider interface and implementations.

Verifies that:
1. DataProvider interface is properly defined
2. MockDataProvider implements all required methods
3. AlphaVantageProvider implements all required methods
4. YfinanceProvider implements all required methods
5. Mock data is realistic and consistent
6. App code can swap providers without changes
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from app.data_sources import (
    DataProvider,
    MockDataProvider,
    AlphaVantageProvider,
    YfinanceProvider,
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


class TestYfinanceProvider:
    """Test YfinanceProvider implementation."""

    def test_yfinance_provider_is_data_provider(self):
        """Test that YfinanceProvider is a DataProvider."""
        try:
            provider = YfinanceProvider(warn_on_init=False)
            assert isinstance(provider, DataProvider)
        except ImportError:
            pytest.skip("yfinance not installed")

    def test_yfinance_requires_yfinance_library(self):
        """Test that YfinanceProvider requires yfinance library."""
        with patch('app.data_sources.yfinance_provider.YFINANCE_AVAILABLE', False):
            with pytest.raises(ImportError, match="yfinance is not installed"):
                YfinanceProvider(warn_on_init=False)

    @patch('app.data_sources.yfinance_provider.yf.Ticker')
    def test_get_quote_success(self, mock_ticker_class):
        """Test get_quote with successful yfinance response."""
        mock_ticker = Mock()
        mock_ticker.info = {
            "currentPrice": 150.25,
            "bid": 150.20,
            "ask": 150.30,
            "volume": 1000000,
        }
        mock_ticker_class.return_value = mock_ticker
        
        try:
            provider = YfinanceProvider(warn_on_init=False)
            quote = provider.get_quote("AAPL")
            
            assert quote is not None
            assert quote.symbol == "AAPL"
            assert quote.price == 150.25
            assert quote.bid == 150.20
            assert quote.ask == 150.30
        except ImportError:
            pytest.skip("yfinance not installed")

    @patch('app.data_sources.yfinance_provider.yf.Ticker')
    def test_get_quote_no_data(self, mock_ticker_class):
        """Test get_quote when no data is available."""
        mock_ticker = Mock()
        mock_ticker.info = {}
        mock_ticker_class.return_value = mock_ticker
        
        try:
            provider = YfinanceProvider(warn_on_init=False)
            quote = provider.get_quote("UNKNOWN")
            
            assert quote is None
        except ImportError:
            pytest.skip("yfinance not installed")

    @patch('app.data_sources.yfinance_provider.yf.Ticker')
    def test_get_price_history_success(self, mock_ticker_class):
        """Test get_price_history with successful yfinance response."""
        import pandas as pd
        
        mock_ticker = Mock()
        mock_history = pd.DataFrame({
            "Open": [149.5, 150.0],
            "High": [150.5, 151.0],
            "Low": [149.0, 149.0],
            "Close": [150.0, 150.5],
            "Volume": [900000, 1000000],
            "Adj Close": [150.0, 150.5],
        }, index=pd.DatetimeIndex(["2024-01-14", "2024-01-15"]))
        mock_ticker.history.return_value = mock_history
        mock_ticker_class.return_value = mock_ticker
        
        try:
            provider = YfinanceProvider(warn_on_init=False)
            bars = provider.get_price_history("AAPL", "2024-01-14", "2024-01-15")
            
            assert len(bars) == 2
            assert bars[0].date == "2024-01-14"
            assert bars[0].close == 150.0
            assert bars[1].date == "2024-01-15"
            assert bars[1].close == 150.5
        except ImportError:
            pytest.skip("yfinance not installed")

    @patch('app.data_sources.yfinance_provider.yf.Ticker')
    def test_get_options_chain_success(self, mock_ticker_class):
        """Test get_options_chain with successful yfinance response."""
        import pandas as pd
        
        mock_ticker = Mock()
        mock_ticker.options = ["2024-02-16", "2024-03-15"]
        
        mock_calls = pd.DataFrame({
            "strike": [150.0, 155.0],
            "bid": [2.5, 1.5],
            "ask": [2.6, 1.6],
            "lastPrice": [2.55, 1.55],
            "volume": [100, 50],
            "openInterest": [1000, 500],
            "impliedVolatility": [0.25, 0.23],
        })
        mock_puts = pd.DataFrame({
            "strike": [150.0, 155.0],
            "bid": [1.5, 2.5],
            "ask": [1.6, 2.6],
            "lastPrice": [1.55, 2.55],
            "volume": [50, 100],
            "openInterest": [500, 1000],
            "impliedVolatility": [0.23, 0.25],
        })
        
        mock_chain = Mock()
        mock_chain.calls = mock_calls
        mock_chain.puts = mock_puts
        mock_ticker.option_chain.return_value = mock_chain
        mock_ticker_class.return_value = mock_ticker
        
        try:
            provider = YfinanceProvider(warn_on_init=False)
            chain = provider.get_options_chain("AAPL", expiration="2024-02-16")
            
            assert len(chain) == 4  # 2 calls + 2 puts
            calls = [e for e in chain if e.contract_type == "call"]
            puts = [e for e in chain if e.contract_type == "put"]
            assert len(calls) == 2
            assert len(puts) == 2
        except ImportError:
            pytest.skip("yfinance not installed")
