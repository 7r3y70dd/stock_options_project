# Options Tracker

A stock options research and paper-trading application that helps users find, score, and track options opportunities based on their selected risk level.

⚠️ **IMPORTANT DISCLAIMER**: This app does **not** promise guaranteed profits or "sure bets." Options trading is inherently risky. All signals and recommendations should be treated as research ideas for educational purposes only, not as financial advice. Past performance does not guarantee future results. Users must understand the risks of options trading, including the potential loss of the entire investment. Always paper trade first before considering any live trading.

## Overview

Options Tracker allows users to:

- **Portfolio Management**: Track portfolio value, cash, positions, and P&L in real-time
- **Watchlist Management**: Create and manage stock watchlists with current pricing and data freshness tracking
- **Options Analysis**: Fetch and analyze options chains with risk-scored opportunities
- **Strategy Scoring**: Score opportunities based on risk, liquidity, volatility, and news sentiment
- **Risk Management**: Choose risk levels (low, medium, high) with configurable guardrails and kill switch
- **Paper Trading**: Test strategies without risking real money (default mode)
- **Backtesting**: Backtest covered calls and other strategies using VectorBT
- **News Integration**: Pull relevant stock news with sentiment analysis
- **Trade Tracking**: Monitor open and closed trades with Greeks and P&L metrics
- **Live Trading**: Optional live trading mode (disabled by default, requires explicit user approval)

## Technology Stack

- **Backend Framework**: FastAPI (async, typed, auto-docs)
- **Web Server**: Uvicorn
- **Frontend**: Server-rendered HTML with Jinja2 templates and static assets
- **Database**: PostgreSQL 13+
- **Cache**: Redis 6+
- **Task Queue**: Celery with Redis broker
- **Backtesting**: VectorBT (vectorized, high-performance)
- **Data Sources**: yfinance, Alpha Vantage, Polygon, Finnhub
- **Testing**: pytest with async support

## Web Interface

The application provides a server-rendered HTML interface with the following pages:

- **`/` or `/dashboard`**: Main dashboard with portfolio summary, watchlist, top opportunities, open trades, recent news, and risk settings
- **`/opportunities`**: Browse all available trading opportunities with filtering and sorting
- **`/opportunities/{signal_id}`**: Detailed view of a specific opportunity with full analysis
- **`/portfolio`**: Portfolio overview with positions, cash, and performance metrics
- **`/watchlist`**: Manage watchlist symbols with add/remove functionality
- **`/trades`**: View all open and closed trades with P&L tracking
- **`/trades/{trade_id}`**: Detailed view of a specific trade with Greeks and exit rules
- **`/risk-settings`**: Configure risk level (low/medium/high) and trading mode
- **`/news`**: Recent news articles with sentiment analysis and event classification
- **`/status`**: System status and health monitoring
- **`/backtests`**: Backtesting interface for strategy evaluation

## Frontend Architecture

The frontend uses server-rendered HTML with:

- **Templates**: Jinja2 templates in `app/frontend/templates/`
  - `base.html`: Shared layout with navigation and styling
  - Page-specific templates: `dashboard.html`, `opportunities.html`, `portfolio.html`, etc.
- **Static Assets**: CSS and JavaScript in `app/frontend/static/`
  - `app.css`: Global styles
  - `app.js`: Shared JavaScript utilities
  - Page-specific assets: `dashboard.js`, `opportunities.js`, etc.
- **API Communication**: JavaScript fetches data from REST API endpoints
- **No Build Step**: Pure HTML/CSS/JS, no Node.js or bundler required

## Project Structure

```
options-tracker/
├── app/
│   ├── api/                     # REST API endpoints
│   │   ├── dashboard.py         # Dashboard aggregation endpoints
│   │   ├── health.py            # Health check endpoint
│   │   └── dev_workflows.py     # Development workflow endpoints
│   ├── core/                    # Core application logic
│   │   ├── config.py            # Configuration management
│   │   ├── database.py          # Database connection and session
│   │   ├── error_handling.py    # Error handling utilities
│   │   ├── main.py              # Application entry point with routes
│   │   ├── broker_provider.py   # Live broker integration
│   │   ├── paper_broker_provider.py  # Paper trading broker
│   │   ├── celery.py            # Celery configuration
│   │   ├── scoring.py           # Signal scoring logic
│   │   └── seed.py              # Database seeding
│   ├── data_sources/            # External data fetching
│   │   ├── data_provider.py     # Abstract data provider interface
│   │   ├── yfinance_provider.py # Yahoo Finance data source
│   │   ├── alpha_vantage_provider.py  # Alpha Vantage data source
│   │   ├── finnhub_provider.py  # Finnhub data source
│   │   └── mock_provider.py     # Mock data for testing
│   ├── models/                  # Data models and schemas
│   │   └── database.py          # SQLAlchemy ORM models
│   ├── news/                    # News analysis
│   │   └── sentiment_analyzer.py # News sentiment analysis
│   ├── options/                 # Options-specific logic
│   │   └── pricing.py           # Options pricing utilities
│   ├── risk/                    # Risk management
│   │   └── guardrails.py        # Risk guardrails and limits
│   ├── strategies/              # Trading strategy definitions
│   │   ├── strategy.py          # Strategy base classes and registry
│   │   ├── covered_call.py      # Covered call strategy
│   │   ├── cash_secured_put.py  # Cash-secured put strategy
│   │   ├── credit_spread.py     # Credit spread strategy
│   │   ├── debit_spread.py      # Debit spread strategy
│   │   └── long_call_put.py     # Long call/put strategy
│   ├── trading/                 # Trade execution and management
│   │   └── trade_manager.py     # Trade lifecycle management
│   ├── backtesting/             # Backtesting engine
│   │   ├── engine.py            # Core backtesting engine
│   │   ├── strategy_backtester.py  # Strategy backtester base
│   │   ├── covered_call_backtest.py # Covered call backtest
│   │   └── DECISION.md          # Backtesting library decision doc
│   ├── workers/                 # Background job workers
│   │   ├── celery_app.py        # Celery app configuration
│   │   └── tasks.py             # Celery task definitions
│   └── frontend/                # Frontend rendering
│       ├── templates/           # Jinja2 HTML templates
│       │   ├── base.html        # Shared layout
│       │   ├── dashboard.html   # Dashboard page
│       │   ├── opportunities.html # Opportunities list
│       │   ├── opportunity_detail.html # Opportunity detail
│       │   ├── portfolio.html   # Portfolio page
│       │   ├── watchlist.html   # Watchlist page
│       │   ├── trades.html      # Trades list
│       │   ├── trade_detail.html # Trade detail
│       │   ├── risk_settings.html # Risk settings
│       │   ├── news.html        # News page
│       │   └── status.html      # Status page
│       ├── static/              # Static assets (CSS, JS)
│       │   ├── app.css          # Global styles
│       │   ├── app.js           # Shared utilities
│       │   └── *.js             # Page-specific scripts
│       ├── api_client.py        # API client for backend communication
│       ├── app_shell.py         # Main app shell and layout
│       ├── dashboard.py         # Dashboard service
│       ├── portfolio_summary.py # Portfolio summary component
│       └── watchlist.py         # Watchlist component
├── services/                    # Service layer
│   ├── options_service.py       # Options analysis and scoring
│   └── test_risk_guardrails.py  # Risk guardrails tests
├── tests/                       # Test suite
│   ├── test_backtesting.py      # Backtesting tests
│   ├── test_broker_providers.py # Broker provider tests
│   ├── test_data_providers.py   # Data provider tests
│   ├── test_database.py         # Database tests
│   ├── test_options_service.py  # Options service tests
│   ├── test_scoring.py          # Scoring tests
│   ├── test_strategies.py       # Strategy tests
│   └── test_trade_manager.py    # Trade manager tests
├── docker-compose.yml           # Docker Compose configuration
├── Dockerfile                   # Docker image definition
├── .env.example                 # Environment variables template
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Key Features

### Dashboard

The dashboard provides a comprehensive overview of:
- **Portfolio Summary**: Total value, cash, positions, open P&L, and trade counts
- **Watchlist**: Symbols with current prices and data freshness
- **Top Opportunities**: Risk-scored trading signals ranked by confidence
- **Open Trades**: Active positions with entry prices, current P&L, and Greeks
- **Recent News**: Stock news with sentiment analysis
- **Risk Settings**: Current risk level and trading mode configuration

### Frontend Components

- **AppShell**: Main application layout with header, content area, and status
- **APIClient**: Centralized API communication with error handling
- **PortfolioSummary**: Reusable portfolio cards with formatting utilities
- **Watchlist**: Symbol management with validation and add/remove operations
- **Dashboard**: Aggregated data service combining all sections

### Strategies

The strategy framework supports multiple options strategies:
- **Covered Call**: Sell calls against long stock positions
- **Cash-Secured Put**: Sell puts with cash reserves
- **Credit Spread**: Sell spreads for premium collection
- **Debit Spread**: Buy spreads for directional bets
- **Long Call/Put**: Directional long options positions

Each strategy:
- Generates signals with confidence scores (0-100)
- Includes exit rules (profit targets, stop losses, time-based exits)
- Provides reasoning and factor breakdowns
- Adjusts scoring based on user risk level

### Backtesting

The backtesting engine uses **VectorBT** for high-performance strategy testing:
- Vectorized operations for 10-100x speed improvement
- Parameter optimization and sensitivity analysis
- Equity curve and performance metrics
- Trade-by-trade analysis
- Support for covered calls and other simple strategies
- Day-by-day replay to avoid look-ahead bias

See `app/backtesting/DECISION.md` for detailed rationale and limitations.

### Risk Management

- **Risk Levels**: Low, Medium, High with configurable guardrails
- **Position Sizing**: Maximum position size as % of portfolio
- **Loss Limits**: Maximum loss per trade and daily loss limits
- **Strategy Restrictions**: Different strategies allowed per risk level
  - Low: covered_call, cash_secured_put
  - Medium: + debit_spread, credit_spread
  - High: + long_call, long_put
- **Liquidity Thresholds**: Volume, open interest, and bid-ask spread limits
- **Kill Switch**: Emergency trading halt with optional position closure
- **Paper Trading**: Default safe mode for testing
- **Live Trading**: Requires explicit user approval and validation

## Setup Instructions

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for containerized setup)
- PostgreSQL 13+ (if running without Docker)
- Redis 6+ (if running without Docker)

### Option 1: Using Docker Compose (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/options-tracker.git
   cd options-tracker
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your API keys:
   - `ALPHAVANTAGE_API_KEY`: Get from https://www.alphavantage.co/
   - `POLYGON_API_KEY`: Get from https://polygon.io/
   - `NEWS_API_KEY`: Get from https://newsapi.org/
   - `FINNHUB_API_KEY`: Get from https://finnhub.io/

3. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Verify the app is running**
   ```bash
   curl http://localhost:8000/api/health
   ```
   Expected response:
   ```json
   {
     "status": "healthy",
     "timestamp": "2024-01-15T10:30:45.123456",
     "service": "Options Tracker API",
     "version": "0.1.0"
   }
   ```

5. **Access the application**
   - Web Interface: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

6. **View logs**
   ```bash
   docker-compose logs -f app
   ```

### Option 2: Local Python Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/options-tracker.git
   cd options-tracker
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create environment file**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your API keys and database configuration.

5. **Set up database** (ensure PostgreSQL is running)
   ```bash
   # Run migrations (when available)
   python -m app.core.seed
   ```

6. **Start Redis** (in a separate terminal)
   ```bash
   redis-server
   ```

7. **Start Celery worker** (in a separate terminal)
   ```bash
   celery -A app.workers.celery_app worker --loglevel=info
   ```

8. **Run the application** (in a separate terminal)
   ```bash
   uvicorn app.core.main:app --reload --host 0.0.0.0 --port 8000
   ```
   The app will start on http://localhost:8000

## Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test module
python -m pytest tests/test_strategies.py -v

# Run with coverage
python -m pytest --cov=app --cov=services

# Run tests in Docker
docker-compose exec app pytest

# Run backtesting tests
python -m pytest tests/test_backtesting.py -v
```

## Running the Application

**Paper Trading Mode** (default, safe for testing):
```bash
python -m uvicorn app.core.main:app --reload
```

**Live Trading Mode** (requires explicit user approval):
```bash
python -m uvicorn app.core.main:app --reload
# Note: Live trading must be enabled in risk settings UI
```

## API Endpoints

### Health Check

```
GET /api/health
```

Returns the health status of the application.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123456",
  "service": "Options Tracker API",
  "version": "0.1.0"
}
```

### Dashboard Endpoints

#### Get Complete Dashboard Data

```
GET /api/api/dashboard/?user_id={user_id}&watchlist_id={watchlist_id}
```

Returns complete dashboard data including portfolio, watchlist, opportunities, trades, news, and risk settings.

**Parameters:**
- `user_id` (required): User ID
- `watchlist_id` (optional): Specific watchlist ID

**Response:**
```json
{
  "portfolio_summary": {
    "total_value": 105000.0,
    "cash": 95000.0,
    "positions_value": 10000.0,
    "open_pl": 500.0,
    "open_pl_pct": 5.0,
    "num_open_trades": 3,
    "num_open_signals": 5
  },
  "watchlist": [...],
  "top_opportunities": [...],
  "open_trades": [...],
  "recent_news": [...],
  "risk_settings": {...},
  "timestamp": "2024-01-15T10:30:45.123456"
}
```

#### Get Portfolio Summary

```
GET /api/api/dashboard/portfolio?user_id={user_id}
```

#### Get Watchlist

```
GET /api/api/dashboard/watchlist?user_id={user_id}&watchlist_id={watchlist_id}
```

#### Add Symbol to Watchlist

```
POST /api/api/dashboard/watchlist/add?user_id={user_id}&symbol={symbol}&watchlist_id={watchlist_id}
```

#### Remove Symbol from Watchlist

```
POST /api/api/dashboard/watchlist/remove?user_id={user_id}&symbol={symbol}&watchlist_id={watchlist_id}
```

#### Validate Symbol

```
POST /api/api/dashboard/watchlist/validate?symbol={symbol}
```

#### Get Top Opportunities

```
GET /api/api/dashboard/opportunities?user_id={user_id}&limit={limit}
```

#### Get Opportunity Detail

```
GET /api/api/dashboard/opportunities/{signal_id}?user_id={user_id}
```

#### Get Open Trades

```
GET /api/api/dashboard/trades/open?user_id={user_id}
```

#### Get Open Trades with Current Marks

```
GET /api/api/dashboard/trades/open-marked?user_id={user_id}
```

Returns open trades with computed current option prices and paper P&L.

#### Get Recent News

```
GET /api/api/dashboard/news?user_id={user_id}&limit={limit}
```

#### Get Risk Settings

```
GET /api/api/dashboard/risk-settings?user_id={user_id}
```

**Response:**
```json
{
  "user_id": 1,
  "risk_level": "medium",
  "current_risk_level": "medium",
  "paper_trading_enabled": true,
  "live_trading_enabled": false,
  "live_trading_approved": false,
  "initial_portfolio_value": 100000.0,
  "risk_profiles": {
    "low": {...},
    "medium": {...},
    "high": {...}
  }
}
```

#### Update Risk Settings

```
POST /api/api/dashboard/risk-settings/update?user_id={user_id}&risk_level={risk_level}&confirmed={confirmed}
```

**Parameters:**
- `user_id` (required): User ID
- `risk_level` (required): "low", "medium", or "high"
- `confirmed` (optional): Boolean, required for high risk level

#### Get Kill Switch Status

```
GET /api/api/dashboard/kill-switch?user_id={user_id}
```

#### Activate Kill Switch

```
POST /api/api/dashboard/kill-switch/activate?user_id={user_id}&reason={reason}&close_positions={close_positions}
```

#### Deactivate Kill Switch

```
POST /api/api/dashboard/kill-switch/deactivate?user_id={user_id}
```

## Configuration

The application is configured via environment variables. See `.env.example` for all available options:

### Required Configuration

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `ALPHAVANTAGE_API_KEY`: Alpha Vantage API key
- `POLYGON_API_KEY`: Polygon API key
- `NEWS_API_KEY`: News API key
- `FINNHUB_API_KEY`: Finnhub API key

### Optional Configuration

- `LOG_LEVEL`: Logging level (default: INFO)
- `CELERY_BROKER_URL`: Celery broker URL (default: Redis)
- `CELERY_RESULT_BACKEND`: Celery result backend (default: Redis)
- `INITIAL_PORTFOLIO_VALUE`: Initial portfolio value for new users (default: 100000.0)
- `DEFAULT_RISK_LEVEL`: Default risk level for new users (default: medium)

## Development Workflow

### Code Style

```bash
# Format code with black
black app/ services/ tests/

# Lint with flake8
flake8 app/ services/ tests/

# Type check with mypy
mypy app/ services/
```

### Adding a New Strategy

1. Create a new file in `app/strategies/` (e.g., `iron_condor.py`)
2. Implement the `Strategy` base class:

```python
from app.strategies.strategy import Strategy, StrategySignal, MarketData, NewsContext
from services import RiskLevel
from services.options_service import OptionContract, ExitRule
from typing import Optional, List

class IronCondorStrategy(Strategy):
    def __init__(self):
        super().__init__(name="iron_condor", enabled=True)
    
    def generate(
        self,
        symbol: str,
        market_data: MarketData,
        options_chain: List[OptionContract],
        news_context: Optional[NewsContext] = None,
        risk_profile: RiskLevel = RiskLevel.MEDIUM,
    ) -> Optional[StrategySignal]:
        # Implement strategy logic
        # Return StrategySignal with score, expected_profit, max_loss, reason, exit_rules
        pass
```

3. Register the strategy in `app/strategies/__init__.py`
4. Add tests in `tests/test_strategies.py`
5. Update risk guardrails in `app/risk/guardrails.py` if needed

### Adding a New Data Provider

1. Create a new file in `app/data_sources/` (e.g., `tradier_provider.py`)
2. Implement the `DataProvider` interface:

```python
from app.data_sources.data_provider import DataProvider
from typing import Dict, List, Any, Optional
from datetime import datetime

class TradierProvider(DataProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        # Implement quote fetching
        pass
    
    def get_options_chain(self, symbol: str, expiration: Optional[str] = None) -> List[Dict[str, Any]]:
        # Implement options chain fetching
        pass
    
    def get_news(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        # Implement news fetching
        pass
```

3. Add configuration in `app/core/config.py`
4. Add tests in `tests/test_data_providers.py`

### Running Backtests

```python
from app.backtesting.engine import BacktestEngine
import pandas as pd

# Create engine
engine = BacktestEngine(initial_cash=100000.0)

# Load price data
price_data = pd.read_csv("price_data.csv", index_col="date", parse_dates=True)

# Generate signals (1=buy, -1=sell, 0=hold)
signals = pd.Series([0, 1, 0, 0, -1, 0], index=price_data.index)

# Run backtest
result = engine.backtest(
    symbol="AAPL",
    price_data=price_data,
    signals=signals,
    strategy_name="my_strategy"
)

print(result)
print(f"Total Return: {result.total_return:.2f}%")
print(f"Win Rate: {result.win_rate:.2%}")
print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- All tests pass (`pytest`)
- Code is formatted (`black`)
- Code is linted (`flake8`)
- Type hints are correct (`mypy`)
- New features include tests

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and research purposes only. It is not financial advice. Options trading involves substantial risk of loss. Past performance does not guarantee future results. Always consult with a qualified financial advisor before making investment decisions.
