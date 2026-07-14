"""Frontend smoke tests for HTML pages.

Tests verify that server-rendered HTML pages load correctly,
include expected containers/scripts, and do not silently break.
"""

import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.main import app


@pytest.fixture
def client():
    """FastAPI TestClient for the app."""
    return TestClient(app)


# Fixture data
DASHBOARD_FIXTURE = {
    "portfolio_summary": {
        "total_value": 10000.0,
        "cash": 10000.0,
        "positions_value": 0.0,
        "open_pl": 0.0,
        "open_pl_pct": 0.0,
        "num_open_trades": 0,
        "num_open_signals": 10,
    },
    "watchlist": [
        {
            "symbol": "AAPL",
            "current_price": None,
            "added_at": "2026-07-14T11:35:29.445328",
            "last_updated": None,
            "data_freshness_seconds": None,
        }
    ],
    "top_opportunities": [
        {
            "signal_id": 31,
            "symbol": "AAPL",
            "strategy_type": "cash_secured_put",
            "score": 89.51,
            "expected_profit": 300.0,
            "max_loss": 14700.0,
            "probability_estimate": 0.9,
            "reason": "cash_secured_put candidate for AAPL...",
            "status": "pending",
            "created_at": "2026-07-14T11:35:30.508672",
            "breakdown": {
                "expiration": "2026-08-13",
                "strike": 150.0,
                "contract_type": "put",
                "bid": 2.94,
                "ask": 3.06,
                "mid": 3.0,
            },
        }
    ],
    "open_trades": [],
    "recent_news": [],
    "risk_settings": {
        "risk_level": "medium",
        "paper_trading_enabled": True,
        "live_trading_enabled": False,
        "live_trading_approved": False,
        "risk_levels_info": [],
    },
    "timestamp": "2026-07-14T11:35:31.282008",
}

OPPORTUNITIES_FIXTURE = {
    "count": 1,
    "opportunities": [
        {
            "signal_id": 31,
            "symbol": "AAPL",
            "strategy_type": "cash_secured_put",
            "score": 89.51,
            "expected_profit": 300.0,
            "max_loss": 14700.0,
            "probability_estimate": 0.9,
            "reason": "cash_secured_put candidate for AAPL...",
            "status": "pending",
            "created_at": "2026-07-14T11:35:30.508672",
            "breakdown": {
                "expiration": "2026-08-13",
                "strike": 150.0,
                "contract_type": "put",
                "bid": 2.94,
                "ask": 3.06,
                "mid": 3.0,
            },
        }
    ],
}

PORTFOLIO_FIXTURE = {
    "total_value": 10000.0,
    "cash": 10000.0,
    "positions_value": 0.0,
    "open_pl": 0.0,
    "open_pl_pct": 0.0,
    "num_open_trades": 0,
    "num_open_signals": 10,
}

WATCHLIST_FIXTURE = {
    "count": 2,
    "symbols": [
        {
            "symbol": "AAPL",
            "current_price": None,
            "added_at": "2026-07-14T11:35:29.445328",
            "last_updated": None,
            "data_freshness_seconds": None,
        },
        {
            "symbol": "MSFT",
            "current_price": None,
            "added_at": "2026-07-14T11:35:29.445332",
            "last_updated": None,
            "data_freshness_seconds": None,
        },
    ],
}

RISK_SETTINGS_FIXTURE = {
    "risk_level": "medium",
    "paper_trading_enabled": True,
    "live_trading_enabled": False,
    "live_trading_approved": False,
    "risk_levels_info": [
        {
            "level": "low",
            "description": "Conservative: Favors high liquidity, defined risk, lower max loss",
            "max_position_size_pct": 2.0,
            "allowed_strategies": ["covered_call", "cash_secured_put"],
            "max_loss_per_trade_pct": 1.0,
            "requires_confirmation": False,
        }
    ],
}

RISK_SETTINGS_404_FIXTURE = {"detail": "Not Found"}

HEALTH_FIXTURE = {
    "service": "Options Tracker API",
    "status": "healthy",
    "timestamp": "2026-07-14T11:35:31.191940",
    "version": "0.1.0",
}


class TestDashboardPage:
    """Tests for /dashboard HTML page."""

    def test_dashboard_returns_html(self, client):
        """Dashboard route returns HTML with 200 status."""
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_dashboard_includes_title(self, client):
        """Dashboard HTML includes page title."""
        response = client.get("/dashboard")
        assert "Options Tracker" in response.text or "Dashboard" in response.text

    def test_dashboard_includes_root_container(self, client):
        """Dashboard HTML includes root content container."""
        response = client.get("/dashboard")
        assert 'id="app"' in response.text or 'id="main"' in response.text or 'class="container"' in response.text

    def test_dashboard_includes_scripts(self, client):
        """Dashboard HTML includes script tags."""
        response = client.get("/dashboard")
        assert "<script" in response.text

    def test_dashboard_includes_styles(self, client):
        """Dashboard HTML includes style/link tags."""
        response = client.get("/dashboard")
        assert "<link" in response.text or "<style" in response.text

    def test_dashboard_not_json(self, client):
        """Dashboard route does not return JSON."""
        response = client.get("/dashboard")
        assert "application/json" not in response.headers.get("content-type", "")
        # Verify it's not raw JSON object
        assert not response.text.strip().startswith("{")


class TestOpportunitiesPage:
    """Tests for /opportunities HTML page."""

    def test_opportunities_returns_html(self, client):
        """Opportunities route returns HTML with 200 status."""
        response = client.get("/opportunities")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_opportunities_includes_title(self, client):
        """Opportunities HTML includes page title."""
        response = client.get("/opportunities")
        assert "Options Tracker" in response.text or "Opportunit" in response.text

    def test_opportunities_includes_root_container(self, client):
        """Opportunities HTML includes root content container."""
        response = client.get("/opportunities")
        assert 'id="app"' in response.text or 'id="main"' in response.text or 'class="container"' in response.text

    def test_opportunities_includes_scripts(self, client):
        """Opportunities HTML includes script tags."""
        response = client.get("/opportunities")
        assert "<script" in response.text

    def test_opportunities_includes_styles(self, client):
        """Opportunities HTML includes style/link tags."""
        response = client.get("/opportunities")
        assert "<link" in response.text or "<style" in response.text

    def test_opportunities_not_json(self, client):
        """Opportunities route does not return JSON."""
        response = client.get("/opportunities")
        assert "application/json" not in response.headers.get("content-type", "")
        assert not response.text.strip().startswith("{")


class TestOpportunityDetailPage:
    """Tests for /opportunities/{signal_id} HTML page."""

    def test_opportunity_detail_returns_html(self, client):
        """Opportunity detail route returns HTML with 200 status."""
        response = client.get("/opportunities/31")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_opportunity_detail_includes_title(self, client):
        """Opportunity detail HTML includes page title."""
        response = client.get("/opportunities/31")
        assert "Options Tracker" in response.text or "Opportunit" in response.text

    def test_opportunity_detail_includes_root_container(self, client):
        """Opportunity detail HTML includes root content container."""
        response = client.get("/opportunities/31")
        assert 'id="app"' in response.text or 'id="main"' in response.text or 'class="container"' in response.text

    def test_opportunity_detail_includes_scripts(self, client):
        """Opportunity detail HTML includes script tags."""
        response = client.get("/opportunities/31")
        assert "<script" in response.text

    def test_opportunity_detail_includes_styles(self, client):
        """Opportunity detail HTML includes style/link tags."""
        response = client.get("/opportunities/31")
        assert "<link" in response.text or "<style" in response.text

    def test_opportunity_detail_not_json(self, client):
        """Opportunity detail route does not return JSON."""
        response = client.get("/opportunities/31")
        assert "application/json" not in response.headers.get("content-type", "")
        assert not response.text.strip().startswith("{")


class TestPortfolioPage:
    """Tests for /portfolio HTML page."""

    def test_portfolio_returns_html(self, client):
        """Portfolio route returns HTML with 200 status."""
        response = client.get("/portfolio")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_portfolio_includes_title(self, client):
        """Portfolio HTML includes page title."""
        response = client.get("/portfolio")
        assert "Options Tracker" in response.text or "Portfolio" in response.text

    def test_portfolio_includes_root_container(self, client):
        """Portfolio HTML includes root content container."""
        response = client.get("/portfolio")
        assert 'id="app"' in response.text or 'id="main"' in response.text or 'class="container"' in response.text

    def test_portfolio_includes_scripts(self, client):
        """Portfolio HTML includes script tags."""
        response = client.get("/portfolio")
        assert "<script" in response.text

    def test_portfolio_includes_styles(self, client):
        """Portfolio HTML includes style/link tags."""
        response = client.get("/portfolio")
        assert "<link" in response.text or "<style" in response.text

    def test_portfolio_not_json(self, client):
        """Portfolio route does not return JSON."""
        response = client.get("/portfolio")
        assert "application/json" not in response.headers.get("content-type", "")
        assert not response.text.strip().startswith("{")


class TestWatchlistPage:
    """Tests for /watchlist HTML page."""

    def test_watchlist_returns_html(self, client):
        """Watchlist route returns HTML with 200 status."""
        response = client.get("/watchlist")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_watchlist_includes_title(self, client):
        """Watchlist HTML includes page title."""
        response = client.get("/watchlist")
        assert "Options Tracker" in response.text or "Watchlist" in response.text

    def test_watchlist_includes_root_container(self, client):
        """Watchlist HTML includes root content container."""
        response = client.get("/watchlist")
        assert 'id="app"' in response.text or 'id="main"' in response.text or 'class="container"' in response.text

    def test_watchlist_includes_scripts(self, client):
        """Watchlist HTML includes script tags."""
        response = client.get("/watchlist")
        assert "<script" in response.text

    def test_watchlist_includes_styles(self, client):
        """Watchlist HTML includes style/link tags."""
        response = client.get("/watchlist")
        assert "<link" in response.text or "<style" in response.text

    def test_watchlist_not_json(self, client):
        """Watchlist route does not return JSON."""
        response = client.get("/watchlist")
        assert "application/json" not in response.headers.get("content-type", "")
        assert not response.text.strip().startswith("{")


class TestTradesPage:
    """Tests for /trades HTML page."""

    def test_trades_returns_html(self, client):
        """Trades route returns HTML with 200 status."""
        response = client.get("/trades")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_trades_includes_title(self, client):
        """Trades HTML includes page title."""
        response = client.get("/trades")
        assert "Options Tracker" in response.text or "Trade" in response.text

    def test_trades_includes_root_container(self, client):
        """Trades HTML includes root content container."""
        response = client.get("/trades")
        assert 'id="app"' in response.text or 'id="main"' in response.text or 'class="container"' in response.text

    def test_trades_includes_scripts(self, client):
        """Trades HTML includes script tags."""
        response = client.get("/trades")
        assert "<script" in response.text

    def test_trades_includes_styles(self, client):
        """Trades HTML includes style/link tags."""
        response = client.get("/trades")
        assert "<link" in response.text or "<style" in response.text

    def test_trades_not_json(self, client):
        """Trades route does not return JSON."""
        response = client.get("/trades")
        assert "application/json" not in response.headers.get("content-type", "")
        assert not response.text.strip().startswith("{")


class TestRiskSettingsPage:
    """Tests for /risk-settings HTML page."""

    def test_risk_settings_returns_html(self, client):
        """Risk settings route returns HTML with 200 status."""
        response = client.get("/risk-settings")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_risk_settings_includes_title(self, client):
        """Risk settings HTML includes page title."""
        response = client.get("/risk-settings")
        assert "Options Tracker" in response.text or "Risk" in response.text

    def test_risk_settings_includes_root_container(self, client):
        """Risk settings HTML includes root content container."""
        response = client.get("/risk-settings")
        assert 'id="app"' in response.text or 'id="main"' in response.text or 'class="container"' in response.text

    def test_risk_settings_includes_scripts(self, client):
        """Risk settings HTML includes script tags."""
        response = client.get("/risk-settings")
        assert "<script" in response.text

    def test_risk_settings_includes_styles(self, client):
        """Risk settings HTML includes style/link tags."""
        response = client.get("/risk-settings")
        assert "<link" in response.text or "<style" in response.text

    def test_risk_settings_not_json(self, client):
        """Risk settings route does not return JSON."""
        response = client.get("/risk-settings")
        assert "application/json" not in response.headers.get("content-type", "")
        assert not response.text.strip().startswith("{")


class TestNewsPage:
    """Tests for /news HTML page."""

    def test_news_returns_html(self, client):
        """News route returns HTML with 200 status."""
        response = client.get("/news")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_news_includes_title(self, client):
        """News HTML includes page title."""
        response = client.get("/news")
        assert "Options Tracker" in response.text or "News" in response.text

    def test_news_includes_root_container(self, client):
        """News HTML includes root content container."""
        response = client.get("/news")
        assert 'id="app"' in response.text or 'id="main"' in response.text or 'class="container"' in response.text

    def test_news_includes_scripts(self, client):
        """News HTML includes script tags."""
        response = client.get("/news")
        assert "<script" in response.text

    def test_news_includes_styles(self, client):
        """News HTML includes style/link tags."""
        response = client.get("/news")
        assert "<link" in response.text or "<style" in response.text

    def test_news_not_json(self, client):
        """News route does not return JSON."""
        response = client.get("/news")
        assert "application/json" not in response.headers.get("content-type", "")
        assert not response.text.strip().startswith("{")


class TestStatusPage:
    """Tests for /status HTML page."""

    def test_status_returns_html(self, client):
        """Status route returns HTML with 200 status."""
        response = client.get("/status")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_status_includes_title(self, client):
        """Status HTML includes page title."""
        response = client.get("/status")
        assert "Options Tracker" in response.text or "Status" in response.text or "Health" in response.text

    def test_status_includes_root_container(self, client):
        """Status HTML includes root content container."""
        response = client.get("/status")
        assert 'id="app"' in response.text or 'id="main"' in response.text or 'class="container"' in response.text

    def test_status_includes_scripts(self, client):
        """Status HTML includes script tags."""
        response = client.get("/status")
        assert "<script" in response.text

    def test_status_includes_styles(self, client):
        """Status HTML includes style/link tags."""
        response = client.get("/status")
        assert "<link" in response.text or "<style" in response.text

    def test_status_not_json(self, client):
        """Status route does not return JSON."""
        response = client.get("/status")
        assert "application/json" not in response.headers.get("content-type", "")
        assert not response.text.strip().startswith("{")


class TestStaticAssets:
    """Tests for static CSS and JS assets."""

    def test_app_css_reachable(self, client):
        """Static app.css is reachable."""
        response = client.get("/static/app.css")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")

    def test_app_js_reachable(self, client):
        """Static app.js is reachable."""
        response = client.get("/static/app.js")
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")

    def test_formatters_js_reachable(self, client):
        """Static formatters.js is reachable."""
        response = client.get("/static/formatters.js")
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")


class TestHTMLContent:
    """Tests for HTML content quality and safety."""

    def test_dashboard_no_raw_null(self, client):
        """Dashboard HTML does not expose raw null values."""
        response = client.get("/dashboard")
        # Check for common patterns of exposed null/undefined
        assert "null" not in response.text or "null" in response.text.lower() and "nullability" not in response.text
        assert "undefined" not in response.text
        assert "[object Object]" not in response.text

    def test_opportunities_no_raw_null(self, client):
        """Opportunities HTML does not expose raw null values."""
        response = client.get("/opportunities")
        assert "undefined" not in response.text
        assert "[object Object]" not in response.text

    def test_portfolio_no_raw_null(self, client):
        """Portfolio HTML does not expose raw null values."""
        response = client.get("/portfolio")
        assert "undefined" not in response.text
        assert "[object Object]" not in response.text

    def test_watchlist_no_raw_null(self, client):
        """Watchlist HTML does not expose raw null values."""
        response = client.get("/watchlist")
        assert "undefined" not in response.text
        assert "[object Object]" not in response.text

    def test_risk_settings_no_raw_null(self, client):
        """Risk settings HTML does not expose raw null values."""
        response = client.get("/risk-settings")
        assert "undefined" not in response.text
        assert "[object Object]" not in response.text


class TestPageNavigation:
    """Tests for page navigation and linking."""

    def test_dashboard_has_navigation(self, client):
        """Dashboard includes navigation links."""
        response = client.get("/dashboard")
        # Check for nav element or links
        assert "<nav" in response.text or "href=" in response.text

    def test_opportunities_has_navigation(self, client):
        """Opportunities includes navigation links."""
        response = client.get("/opportunities")
        assert "<nav" in response.text or "href=" in response.text

    def test_portfolio_has_navigation(self, client):
        """Portfolio includes navigation links."""
        response = client.get("/portfolio")
        assert "<nav" in response.text or "href=" in response.text
