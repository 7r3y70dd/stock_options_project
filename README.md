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
- **Web Interface**: Server-rendered HTML pages for dashboard, opportunities, portfolio, watchlist, trades, risk settings, news, status, and backtests

## Technology Stack

- **Backend Framework**: FastAPI (async, typed, auto-docs)
- **Web Server**: Uvicorn
- **Frontend**: Server-rendered HTML with Jinja2 templates
- **Database**: PostgreSQL 13+
- **Cache**: Redis 6+
- **Task Queue**: Celery with Redis broker
- **Backtesting**: VectorBT (vectorized, high-performance)
- **Data Sources**: yfinance, Alpha Vantage, Polygon, Finnhub, MarketData
- **Testing**: pytest with async support
- **Containerization**: Docker and Docker Compose

## Web Interface

The application provides a complete web interface with server-rendered HTML pages:

- **`/` or `/dashboard`**: Main dashboard with portfolio summary, watchlist, top opportunities, open trades, recent news, and risk settings
- **`/opportunities`**: List of all trading opportunities with filtering and sorting
- **`/opportunities/{signal_id}`**: Detailed view of a specific opportunity with full analysis
- **`/portfolio`**: Portfolio overview with positions, P&L, and performance metrics
- **`/watchlist`**: Manage watchlist symbols with add/remove functionality
- **`/trades`**: List of all trades (open and closed) with P&L tracking
- **`/trades/{trade_id}`**: Detailed view of a specific trade with Greeks and exit rules
- **`/risk-settings`**: Configure risk level, trading mode, and guardrails
- **`/news`**: Recent news articles with sentiment analysis
- **`/status`**: System status and health checks
- **`/backtests`**: Backtest results and performance analysis

## Frontend Architecture

The frontend uses a server-rendered HTML approach:

- **Templates**: Jinja2 templates in `app/frontend/templates/`
  - `dashboard.html`: Main dashboard page
  - `opportunities.html`: Opportunities list page
  - `opportunity_detail.html`: Opportunity detail page
  - `portfolio.html`: Portfolio page
  - `watchlist.html`: Watchlist management page
  - `trades.html`: Trades list page
  - `trade_detail.html`: Trade detail page
  - `risk_settings.html`: Risk settings page
  - `news.html`: News page
  - `status.html`: Status page
  - `backtests.html`: Backtests page

- **Static Assets**: CSS, JavaScript, and images in `app/frontend/static/`
  - Mounted at `/static` via FastAPI StaticFiles
  - Client-side JavaScript fetches data from API endpoints

- **API Communication**: Frontend JavaScript calls REST API endpoints in `/api/api/dashboard/` for dynamic data

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
│   │   ├── main.py              # Application entry point with HTML routes
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
│   ├── frontend/                # Frontend rendering
│   │   ├── templates/           # Jinja2 HTML templates
│   │   │   ├── dashboard.html
│   │   │   ├── opportunities.html
│   │   │   ├── opportunity_detail.html
│   │   │   ├── portfolio.html
│   │   │   ├── watchlist.html
│   │   │   ├── trades.html
│   │   │   ├── trade_detail.html
│   │   │   ├── risk_settings.html
│   │   │   ├── news.html
│   │   │   ├── status.html
│   │   │   └── backtests.html
│   │   ├── static/              # Static assets (CSS, JS, images)
│   │   ├── api_client.py        # API client for backend communication
│   │   ├── app_shell.py         # Main app shell and layout
│   │   ├── dashboard.py         # Dashboard service
│   │   ├── portfolio_summary.py # Portfolio summary component
│   │   └── watchlist.py         # Watchlist component
│   └── tests/                   # App-level tests
│       └── test_watchlist.py    # Watchlist tests
├── services/                    # Service layer
│   ├── options_service.py       # Options analysis and scoring
│   └── test_risk_guardrails.py  # Risk guardrails tests
├── tests/                       # Test suite
│   ├── test_backtesting.py      # Backtesting tests
│   ├── test_broker_providers.py # Broker provider tests
│   ├── test_covered_call_pnl.py # Covered call P&L tests
│   ├── test_data_providers.py   # Data provider tests
│   ├── test_database.py         # Database tests
│   ├── test_frontend.py         # Frontend tests
│   ├── test_options_service.py  # Options service tests
│   ├── test_risk_guardrails.py  # Risk guardrails tests
│   ├── test_scoring.py          # Scoring tests
│   ├── test_strategies.py       # Strategy tests
│   └── test_trade_manager.py    # Trade manager tests
├── scripts/                     # Utility scripts
│   ├── dev_dump_frontend_json.py
│   ├── dev_ingest_and_recommend.py
│   └── dev_reseed_database.py
├── docker-compose.yml           # Docker Compose configuration
├── Dockerfile                   # Docker image definition
├── .env.example                 # Environment variables template
├── requirements.txt             # Python dependencies
├── conftest.py                  # Pytest configuration
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

See `app/backtesting/DECISION.md` for detailed rationale and limitations.

### Risk Management

- **Risk Levels**: Low, Medium, High with configurable guardrails
- **Position Sizing**: Maximum position size as % of portfolio
- **Loss Limits**: Maximum loss per trade and daily loss limits
- **Strategy Restrictions**: Different strategies allowed per risk level
- **Kill Switch**: Emergency trading halt feature to disable new orders and optionally close paper positions
- **Paper Trading**: Default safe mode for testing
- **Live Trading**: Requires explicit user approval and validation

## Database Models

The application uses PostgreSQL with the following SQLAlchemy models:

- **User**: User accounts with risk preferences and trading settings
  - Fields: username, email, risk_level, paper_trading_enabled, live_trading_enabled, initial_portfolio_value
  - Relationships: watchlists, trades, signals, backtest_results

- **Watchlist**: User watchlists for tracking symbols
  - Fields: name, description, is_active
  - Relationships: user, symbols (WatchlistSymbol)

- **WatchlistSymbol**: Symbols in a watchlist
  - Fields: symbol, added_at
  - Unique constraint: watchlist_id + symbol

- **OptionContract**: Option contract data with Greeks and market data
  - Fields: symbol, expiration, strike, contract_type, bid, ask, volume, open_interest, implied_volatility, delta, gamma, theta, vega, underlying_price, days_to_expiration, liquidity_score, event_risks
  - Relationships: trades, signals

- **Signal**: Trading signals with risk assessment and exit rules
  - Fields: symbol, strategy_type, risk_level, score, expected_profit, max_loss, probability_estimate, reason, status, breakdown, event_risks, exit_rules
  - Status: pending, approved, rejected, expired, executed, no_trade
  - Relationships: user, option_contract, trades

- **Trade**: Trade execution records for paper and live trades
  - Fields: symbol, strategy_type, entry_price, exit_price, quantity, status, order_status, is_paper_trading, opened_at, closed_at, realized_pl, exit_reason
  - Relationships: user, signal, option_contract

- **NewsArticle**: News articles with sentiment analysis
  - Fields: symbol, title, description, url, source, published_at, sentiment, sentiment_score, confidence_score, event_type, provider
  - Unique constraint: url

- **KillSwitch**: Global kill switch for emergency trading halt
  - Fields: is_active, activated_by, reason, close_positions, activated_at, deactivated_at

- **BacktestResult**: Backtest results and performance metrics
  - Fields: strategy_type, symbol, start_date, end_date, initial_capital, final_value, total_return, sharpe_ratio, max_drawdown, num_trades, win_rate, parameters, equity_curve
  - Relationships: user

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
   - `MARKETDATA_TOKEN`: Get from https://www.marketdata.app/
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
   - Dashboard: http://localhost:8000/dashboard
   - API Documentation: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

6. **View logs**
   ```bash
   docker-compose logs -f app
   docker-compose logs -f celery_worker
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
   uvicorn app.core.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   The app will start on http://localhost:8000

## Configuration

Key environment variables (see `.env.example` for full list):

- **Database**:
  - `DATABASE_URL`: PostgreSQL connection string
  - `REDIS_URL`: Redis connection string

- **Data Providers**:
  - `DATA_PROVIDER`: Primary data provider (marketdata, yfinance, alpha_vantage, polygon, finnhub)
  - `MARKETDATA_TOKEN`: MarketData API token
  - `MARKETDATA_STRIKE_LIMIT`: Number of strikes to fetch (default: 10)
  - `MARKETDATA_DTE`: Days to expiration filter (default: 30)
  - `YFINANCE_ENABLED`: Enable yfinance provider (true/false)

- **Celery**:
  - `CELERY_BROKER_URL`: Celery broker URL (Redis)
  - `CELERY_RESULT_BACKEND`: Celery result backend (Redis)

- **Application**:
  - `ENVIRONMENT`: Environment (dev, prod)
  - `DEBUG`: Debug mode (True/False)

## Running Tests

```bash
# Run all tests
pytest

# Run specific test module
pytest tests/test_strategies.py -v

# Run with coverage
pytest --cov=app --cov=services

# Run tests in Docker
docker-compose exec app pytest

# Run backtesting tests
pytest tests/test_backtesting.py -v

# Run frontend tests
pytest tests/test_frontend.py -v
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

Returns portfolio summary for user.

#### Get Watchlist

```
GET /api/api/dashboard/watchlist?user_id={user_id}&watchlist_id={watchlist_id}
```

Returns watchlist with symbols and current prices.

#### Add Symbol to Watchlist

```
POST /api/api/dashboard/watchlist/add?user_id={user_id}&symbol={symbol}&watchlist_id={watchlist_id}
```

Adds a symbol to user's watchlist.

#### Remove Symbol from Watchlist

```
POST /api/api/dashboard/watchlist/remove?user_id={user_id}&symbol={symbol}&watchlist_id={watchlist_id}
```

Removes a symbol from user's watchlist.

#### Validate Symbol

```
POST /api/api/dashboard/watchlist/validate?symbol={symbol}
```

Validates a stock symbol format.

#### Get Top Opportunities

```
GET /api/api/dashboard/opportunities?user_id={user_id}&limit={limit}
```

Returns top ranked opportunities for user.

#### Get Opportunity Detail

```
GET /api/api/dashboard/opportunities/{signal_id}?user_id={user_id}
```

Returns detailed information for a specific opportunity.

#### Get Open Trades

```
GET /api/api/dashboard/trades/open?user_id={user_id}
```

Returns all open trades for user.

#### Get Open Trades with Current Mark

```
GET /api/api/dashboard/trades/open-marked?user_id={user_id}
```

Returns open trades with computed current option mark and paper P&L.

#### Get Trade Detail

```
GET /api/api/dashboard/trades/{trade_id}?user_id={user_id}
```

Returns detailed information for a specific trade.

#### Get Recent News

```
GET /api/api/dashboard/news?user_id={user_id}&limit={limit}
```

Returns recent news articles with sentiment analysis.

#### Get Risk Settings

```
GET /api/api/dashboard/risk-settings?user_id={user_id}
```

Returns risk settings for user.

#### Update Risk Settings

```
POST /api/api/dashboard/risk-settings/update?user_id={user_id}&risk_level={risk_level}&confirmed={confirmed}
```

Updates risk settings for user.

**Query Parameters:**
- `user_id` (required): User ID
- `risk_level` (required): Risk level (low, medium, high)
- `confirmed` (optional): Confirmation flag for high risk (true/false)

#### Get Kill Switch Status

```
GET /api/api/dashboard/kill-switch?user_id={user_id}
```

Returns current kill switch status.

#### Activate Kill Switch

```
POST /api/api/dashboard/kill-switch/activate?user_id={user_id}&reason={reason}&close_positions={close_positions}
```

Activates the kill switch to halt trading.

#### Deactivate Kill Switch

```
POST /api/api/dashboard/kill-switch/deactivate?user_id={user_id}
```

Deactivates the kill switch to resume trading.

## Development Workflow

### Code Style

- Use `black` for code formatting
- Use `flake8` for linting
- Use `mypy` for type checking
- Follow PEP 8 guidelines

```bash
# Format code
black app/ tests/ services/

# Lint code
flake8 app/ tests/ services/

# Type check
mypy app/ tests/ services/
```

### Adding a New Strategy

1. Create a new strategy file in `app/strategies/`:

```python
from app.strategies.strategy import Strategy, StrategySignal

class MyNewStrategy(Strategy):
    def __init__(self):
        super().__init__(
            name="my_new_strategy",
            description="Description of my strategy",
            risk_level="medium"
        )
    
    def generate_signal(self, symbol: str, data: dict, user_risk_level: str) -> StrategySignal:
        # Implement signal generation logic
        pass
```

2. Register the strategy in `app/strategies/__init__.py`:

```python
from app.strategies.my_new_strategy import MyNewStrategy

STRATEGY_REGISTRY["my_new_strategy"] = MyNewStrategy()
```

3. Add tests in `tests/test_strategies.py`

### Adding a New Data Provider

1. Create a new provider file in `app/data_sources/`:

```python
from app.data_sources.data_provider import DataProvider

class MyNewProvider(DataProvider):
    def fetch_stock_price(self, symbol: str) -> float:
        # Implement price fetching
        pass
    
    def fetch_options_chain(self, symbol: str) -> list:
        # Implement options chain fetching
        pass
```

2. Register the provider in `app/data_sources/__init__.py`

3. Add tests in `tests/test_data_providers.py`

### Running Backtests

```python
from app.backtesting.covered_call_backtest import CoveredCallBacktest

# Initialize backtest
backtest = CoveredCallBacktest(
    symbol="AAPL",
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=100000.0
)

# Run backtest
results = backtest.run()

# Analyze results
print(f"Total Return: {results['total_return']:.2%}")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {results['max_drawdown']:.2%}")
print(f"Win Rate: {results['win_rate']:.2%}")
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes with tests
4. Run tests and linting (`pytest`, `black`, `flake8`, `mypy`)
5. Commit your changes (`git commit -am 'Add my feature'`)
6. Push to the branch (`git push origin feature/my-feature`)
7. Create a Pull Request

## License

This project is licensed under the MIT License.

## Disclaimer

This software is provided for educational and research purposes only. It is not intended to provide financial advice or recommendations. Options trading involves substantial risk and is not suitable for all investors. Past performance does not guarantee future results. Always consult with a qualified financial advisor before making investment decisions. The authors and contributors are not responsible for any financial losses incurred through the use of this software.
