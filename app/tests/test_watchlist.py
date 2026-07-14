"""Tests for watchlist functionality.

Tests watchlist operations including adding, removing, and refreshing symbols.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.database import User, WatchlistSymbol, MarketQuote
from app.core.paper_broker_provider import PaperBrokerProvider
from app.data_sources.mock_provider import MockDataProvider
from app.workers.tasks import refresh_watchlist_market_data


@pytest.fixture
def db_session():
    """Create a test database session."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user."""
    user = User(username="testuser", email="test@example.com")
    db_session.add(user)
    db_session.commit()
    return user


class TestWatchlistRefresh:
    """Tests for watchlist market data refresh."""
    
    def test_refresh_watchlist_market_data_empty(self, db_session: Session, test_user: User):
        """Test refresh with empty watchlist."""
        provider = MockDataProvider()
        result = refresh_watchlist_market_data(test_user.id, provider=provider)
        
        assert result["updated"] == 0
        assert result["failed"] == 0
        assert result["symbols"] == []
    
    def test_refresh_watchlist_market_data_with_symbols(self, db_session: Session, test_user: User):
        """Test refresh with watchlist symbols."""
        # Add symbols to watchlist
        ws1 = WatchlistSymbol(user_id=test_user.id, symbol="AAPL")
        ws2 = WatchlistSymbol(user_id=test_user.id, symbol="MSFT")
        db_session.add(ws1)
        db_session.add(ws2)
        db_session.commit()
        
        provider = MockDataProvider()
        result = refresh_watchlist_market_data(test_user.id, provider=provider)
        
        assert result["updated"] == 2
        assert result["failed"] == 0
        assert "AAPL" in result["symbols"]
        assert "MSFT" in result["symbols"]
    
    def test_refresh_watchlist_creates_market_quotes(self, db_session: Session, test_user: User):
        """Test that refresh creates MarketQuote records."""
        # Add symbol to watchlist
        ws = WatchlistSymbol(user_id=test_user.id, symbol="AAPL")
        db_session.add(ws)
        db_session.commit()
        
        provider = MockDataProvider()
        refresh_watchlist_market_data(test_user.id, provider=provider)
        
        # Check that MarketQuote was created
        quote = db_session.query(MarketQuote).filter(
            MarketQuote.watchlist_symbol_id == ws.id
        ).first()
        
        assert quote is not None
        assert quote.symbol == "AAPL"
        assert quote.price is not None
        assert quote.price > 0
    
    def test_refresh_watchlist_updates_existing_quote(self, db_session: Session, test_user: User):
        """Test that refresh updates existing MarketQuote."""
        # Add symbol to watchlist
        ws = WatchlistSymbol(user_id=test_user.id, symbol="AAPL")
        db_session.add(ws)
        db_session.commit()
        
        # Create initial quote
        old_quote = MarketQuote(
            watchlist_symbol_id=ws.id,
            symbol="AAPL",
            price=150.0,
            fetched_at=datetime.utcnow() - timedelta(hours=1)
        )
        db_session.add(old_quote)
        db_session.commit()
        
        provider = MockDataProvider()
        refresh_watchlist_market_data(test_user.id, provider=provider)
        
        # Check that new quote was created (not updated)
        quotes = db_session.query(MarketQuote).filter(
            MarketQuote.watchlist_symbol_id == ws.id
        ).all()
        
        assert len(quotes) == 2  # Old and new
        latest = max(quotes, key=lambda q: q.fetched_at)
        assert latest.fetched_at > old_quote.fetched_at


class TestPaperBrokerPortfolio:
    """Tests for PaperBrokerProvider portfolio methods."""
    
    def test_get_portfolio_empty(self, db_session: Session, test_user: User):
        """Test portfolio with no trades."""
        broker = PaperBrokerProvider(initial_cash=10000.0)
        portfolio = broker.get_portfolio(user_id=test_user.id, db=db_session)
        
        assert portfolio["total_value"] == 10000.0
        assert portfolio["cash"] == 10000.0
        assert portfolio["positions_value"] == 0.0
        assert portfolio["open_pl"] == 0.0
        assert portfolio["open_pl_pct"] == 0.0
        assert portfolio["num_open_trades"] == 0
    
    def test_get_portfolio_no_db(self):
        """Test portfolio without database session."""
        broker = PaperBrokerProvider(initial_cash=10000.0)
        portfolio = broker.get_portfolio()
        
        assert portfolio["total_value"] == 10000.0
        assert portfolio["cash"] == 10000.0
        assert portfolio["positions_value"] == 0.0
    
    def test_get_portfolio_with_open_trade(self, db_session: Session, test_user: User):
        """Test portfolio with open trades."""
        from app.models.database import Trade
        
        # Create open trade
        trade = Trade(
            user_id=test_user.id,
            symbol="AAPL",
            strategy_type="covered_call",
            status="open",
            entry_price=150.0,
            quantity=10,
            profit_loss=100.0
        )
        db_session.add(trade)
        db_session.commit()
        
        broker = PaperBrokerProvider(initial_cash=10000.0)
        portfolio = broker.get_portfolio(user_id=test_user.id, db=db_session)
        
        assert portfolio["num_open_trades"] == 1
        assert portfolio["positions_value"] == 1500.0  # 150 * 10
        assert portfolio["open_pl"] == 100.0


class TestWatchlistRendering:
    """Tests for watchlist rendering."""
    
    def test_render_watchlist_list_input(self):
        """Test rendering with list input."""
        from app.frontend.app_shell import render_watchlist_section
        
        watchlist = [
            {
                "symbol": "AAPL",
                "current_price": 150.0,
                "added_at": "2024-01-01T00:00:00",
                "last_updated": "2024-01-02T00:00:00",
                "data_freshness_seconds": 3600
            }
        ]
        
        html = render_watchlist_section(watchlist)
        assert "AAPL" in html
        assert "$150.00" in html
        assert "3600s ago" in html
    
    def test_render_watchlist_dict_input(self):
        """Test rendering with dict input."""
        from app.frontend.app_shell import render_watchlist_section
        
        watchlist = {
            "symbols": [
                {
                    "symbol": "MSFT",
                    "current_price": 380.0,
                    "added_at": "2024-01-01T00:00:00",
                    "last_updated": "2024-01-02T00:00:00",
                    "data_freshness_seconds": 1800
                }
            ],
            "count": 1
        }
        
        html = render_watchlist_section(watchlist)
        assert "MSFT" in html
        assert "$380.00" in html
        assert "1800s ago" in html
    
    def test_render_watchlist_null_price(self):
        """Test rendering with null price."""
        from app.frontend.app_shell import render_watchlist_section
        
        watchlist = [
            {
                "symbol": "AAPL",
                "current_price": None,
                "added_at": "2024-01-01T00:00:00",
                "last_updated": None,
                "data_freshness_seconds": None
            }
        ]
        
        html = render_watchlist_section(watchlist)
        assert "AAPL" in html
        assert "Price unavailable" in html
        assert "Not yet updated" in html
    
    def test_render_watchlist_empty(self):
        """Test rendering empty watchlist."""
        from app.frontend.app_shell import render_watchlist_section
        
        html = render_watchlist_section([])
        assert "empty" in html.lower()
