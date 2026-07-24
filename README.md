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
- **Web Interface**: Server-rendered HTML pages for dashboard, opportunities, portfolio, watchlist, trades, risk settings, news, and system status

## Technology Stack

- **Backend Framework**: FastAPI (async, typed, auto-docs)
- **Web Server**: Uvicorn
- **Frontend**: Server-rendered HTML with Jinja2 templates
- **Database**: PostgreSQL 13+
- **Cache**: Redis 6+
- **Task Queue**: Celery with Redis broker
- **Backtesting**: VectorBT (vectorized, high-performance)
- **Data Sources**: yfinance, Alpha Vantage, Polygon, Finnhub
- **Testing**: pytest with async support

## Web Interface

The application provides a complete web interface with server-rendered HTML pages:

- **`/` or `/dashboard`**: Main dashboard with portfolio summary, watchlist, top opportunities, open trades, recent news, and risk settings
- **`/opportunities`**: Browse all trading opportunities with filtering and sorting
- **`/opportunities/{signal_id}`**: Detailed view of a specific opportunity with full analysis
- **`/portfolio`**: Portfolio overview with positions, P&L, and performance metrics
- **`/watchlist`**: Manage watchlist symbols with add/remove functionality
- **`/trades`**: View all open and closed trades with detailed metrics
- **`/trades/{trade_id}`**: Detailed view of a specific trade
- **`/risk-settings`**: Configure risk level, trading mode, and guardrails
- **`/news`**: Recent news articles with sentiment analysis and event classification
- **`/status`**: System health status and service monitoring
- **`/backtests`**: Backtesting results and analysis

### Frontend Architecture

The frontend uses a server-rendered approach:

- **Templates**: Jinja2 templates in `app/frontend/templates/`
  - `base.html`: Shared layout with navigation and styling
  - Page-specific templates: `dashboard.html`, `opportunities.html`, `portfolio.html`, etc.
- **Static Assets**: CSS and JavaScript in `app/frontend/static/`
  - `app.css`: Global styles
  - `app.js`: Shared JavaScript utilities
  - `api.js`: API client for backend communication
  - `formatters.js`: Data formatting helpers
- **API Communication**: JavaScript fetches data from REST API endpoints and updates the DOM
- **No Build Step**: Pure HTML/CSS/JS without React, Vue, or build tools

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
│   │   ├── polygon_provider.py  # Polygon data source (if exists)
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
│   └── frontend/                # Frontend components
│       ├── templates/           # Jinja2 HTML templates
│       │   ├── base.html        # Base layout template
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
│       │   ├── api.js           # API client
│       │   └── formatters.js    # Data formatters
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
├── scripts/                     # Development scripts
│   ├── dev_dump_frontend_json.py # Dump dashboard data for frontend dev
│   ├── dev_ingest_and_recommend.py # Ingest data and generate signals
│   └── dev_reseed_database.py   # Reseed database with test data
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
- **Recent News**: Stock news with sentiment analysis and event classification
- **Risk Settings**: Current risk level, trading mode, and kill switch status

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
- Analyzes Greeks (delta, gamma, theta, vega)
- Considers volatility context and event risks

### Backtesting

The backtesting engine uses **VectorBT** for high-performance strategy testing:
- Vectorized operations for 10-100x speed improvement
- Parameter optimization and sensitivity analysis
- Equity curve and performance metrics
- Trade-by-trade analysis
- Support for covered calls and other simple strategies

See `app/backtesting/DECISION.md` for detailed rationale and limitations.

### Risk Management

- **Risk Levels**: Low, Medium, High with configurable guardrails
- **Position Sizing**: Maximum position size as % of portfolio
- **Loss Limits**: Maximum loss per trade and daily loss limits
- **Strategy Restrictions**: Different strategies allowed per risk level
- **Kill Switch**: Emergency trading halt with optional position closing
- **Paper Trading**: Default safe mode for testing
- **Live Trading**: Requires explicit user approval and validation

### Database Models

Key database models include:
- **User**: User accounts with risk preferences and trading settings
- **Watchlist**: User watchlists with symbols
- **WatchlistSymbol**: Symbols in watchlists
- **OptionContract**: Option contracts with Greeks, pricing, and volatility data
- **Signal**: Trading signals with analysis and exit rules
- **Trade**: Trade executions with P&L tracking
- **NewsArticle**: News articles with sentiment analysis and event classification
- **KillSwitch**: Global kill switch for emergency trading halt
- **BacktestResult**: Backtesting results and metrics

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
   - Web Interface: http://localhost:8000/
   - API Documentation (Swagger): http://localhost:8000/docs
   - API Documentation (ReDoc): http://localhost:8000/redoc

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
   # Run database seeding
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

**Live Trading Mode** (requires explicit user approval in database):
- Set `live_trading_enabled=True` and `live_trading_approved=True` in User model
- Configure broker credentials in environment variables

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

Returns complete dashboard data including portfolio summary, watchlist, top opportunities, open trades, recent news, and risk settings.

**Query Parameters:**
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
    "low": {
      "label": "Low Risk",
      "description": "Conservative strategies with lower potential loss."
    },
    "medium": {
      "label": "Medium Risk",
      "description": "Balanced strategies with moderate risk and return."
    },
    "high": {
      "label": "High Risk",
      "description": "Aggressive strategies with higher potential loss."
    }
  }
}
```

#### Update Risk Settings

```
POST /api/api/dashboard/risk-settings/update?user_id={user_id}&risk_level={risk_level}&confirmed={confirmed}
```

**Query Parameters:**
- `user_id` (required): User ID
- `risk_level` (required): "low", "medium", or "high"
- `confirmed` (optional): Boolean, required for "high" risk level

#### Execute Trade

```
POST /api/api/dashboard/trades/execute?user_id={user_id}&signal_id={signal_id}
```

#### Close Trade

```
POST /api/api/dashboard/trades/close?user_id={user_id}&trade_id={trade_id}
```

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

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/options_tracker

# API Configuration
API_BASE_URL=http://localhost:8000/api
DASHBOARD_PREFIX=/api/dashboard
DEMO_USER_ID=1

# External APIs
ALPHAVANTAGE_API_KEY=your_key_here
POLYGON_API_KEY=your_key_here
NEWS_API_KEY=your_key_here
FINNHUB_API_KEY=your_key_here

# Redis
REDIS_URL=redis://localhost:6379

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Environment
ENVIRONMENT=development
DEBUG=true
```

## Development Workflow

### Adding a New Strategy

1. Create a new strategy file in `app/strategies/`:

```python
from app.strategies.strategy import Strategy, StrategySignal

class MyNewStrategy(Strategy):
    def generate_signal(self, symbol: str, data: dict) -> StrategySignal:
        # Implement strategy logic
        pass
```

2. Register the strategy in `app/strategies/__init__.py`:

```python
from app.strategies.my_new_strategy import MyNewStrategy

STRATEGY_REGISTRY["my_new_strategy"] = MyNewStrategy
```

3. Add tests in `tests/test_strategies.py`

### Adding a New Data Provider

1. Create a new provider file in `app/data_sources/`:

```python
from app.data_sources.data_provider import DataProvider

class MyDataProvider(DataProvider):
    def fetch_stock_data(self, symbol: str) -> dict:
        # Implement data fetching
        pass
```

2. Register the provider in `app/data_sources/__init__.py`

3. Add tests in `tests/test_data_providers.py`

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions focused and under 50 lines when possible
- Use meaningful variable names

### Running Development Scripts

```bash
# Reseed database with test data
python scripts/dev_reseed_database.py

# Ingest data and generate signals
python scripts/dev_ingest_and_recommend.py

# Dump dashboard data for frontend development
python scripts/dev_dump_frontend_json.py
```

## Backtesting

### Running a Backtest

```python
from app.backtesting.covered_call_backtest import CoveredCallBacktest

backtest = CoveredCallBacktest(
    symbol="AAPL",
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=100000.0
)

results = backtest.run()
print(results.summary())
```

### Backtest Results

Backtest results include:
- Total return and annualized return
- Sharpe ratio and Sortino ratio
- Maximum drawdown
- Win rate and profit factor
- Trade-by-trade analysis
- Equity curve

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -am 'Add my feature'`)
6. Push to the branch (`git push origin feature/my-feature`)
7. Create a Pull Request

## License

This project is for educational purposes only. See LICENSE file for details.

## Disclaimer

This software is provided for educational and research purposes only. It is not intended to provide financial advice or recommendations. Options trading involves substantial risk of loss and is not suitable for all investors. Past performance does not guarantee future results. Always consult with a qualified financial advisor before making any investment decisions.

The developers and contributors of this project are not responsible for any financial losses incurred through the use of this software. Use at your own risk.
