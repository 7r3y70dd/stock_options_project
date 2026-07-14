# Options Tracker

A stock options research and paper-trading application that helps users find, score, and track options opportunities based on their selected risk level.

⚠️ **IMPORTANT DISCLAIMER**: This app does **not** promise guaranteed profits or "sure bets." Options trading is inherently risky. All signals and recommendations should be treated as research ideas for educational purposes only, not as financial advice. Past performance does not guarantee future results. Users must understand the risks of options trading, including the potential loss of the entire investment. Always paper trade first before considering any live trading.

## Overview

Options Tracker allows users to:

- **Portfolio Management**: Track portfolio value, cash, positions, and P&L in real-time
- **Watchlist Management**: Create and manage stock watchlists with current pricing and data freshness tracking
- **Options Analysis**: Fetch and analyze options chains with risk-scored opportunities
- **Strategy Scoring**: Score opportunities based on risk, liquidity, volatility, and news sentiment
- **Risk Management**: Choose risk levels (low, medium, high) with configurable guardrails
- **Paper Trading**: Test strategies without risking real money (default mode)
- **Backtesting**: Backtest covered calls and other strategies using VectorBT
- **News Integration**: Pull relevant stock news with sentiment analysis
- **Trade Tracking**: Monitor open and closed trades with Greeks and P&L metrics
- **Live Trading**: Optional live trading mode (disabled by default, requires explicit user approval)

## Technology Stack

- **Backend Framework**: FastAPI (async, typed, auto-docs)
- **Web Server**: Uvicorn
- **Database**: PostgreSQL 13+
- **Cache**: Redis 6+
- **Task Queue**: Celery with Redis broker
- **Backtesting**: VectorBT (vectorized, high-performance)
- **Data Sources**: yfinance, Alpha Vantage, Polygon, Finnhub
- **Testing**: pytest with async support
- **Frontend**: Python-based rendering with structured data output

## Project Structure

```
options-tracker/
├── app/
│   ├── api/                     # REST API endpoints
│   │   ├── dashboard.py         # Dashboard aggregation endpoints
│   │   └── health.py            # Health check endpoint
│   ├── core/                    # Core application logic
│   │   ├── config.py            # Configuration management
│   │   ├── database.py          # Database connection and session
│   │   ├── error_handling.py    # Error handling utilities
│   │   ├── main.py              # Application entry point
│   │   ├── broker_provider.py   # Live broker integration
│   │   ├── paper_broker_provider.py  # Paper trading broker
│   │   ├── celery.py            # Celery configuration
│   │   └── seed.py              # Database seeding
│   ├── data_sources/            # External data fetching
│   │   ├── data_provider.py     # Abstract data provider interface
│   │   ├── yfinance_provider.py # Yahoo Finance data source
│   │   ├── alpha_vantage_provider.py  # Alpha Vantage data source
│   │   ├── polygon_provider.py  # Polygon data source
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
│   └── test_strategies.py       # Strategy tests
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

See `app/backtesting/DECISION.md` for detailed rationale and limitations.

### Risk Management

- **Risk Levels**: Low, Medium, High with configurable guardrails
- **Position Sizing**: Maximum position size as % of portfolio
- **Loss Limits**: Maximum loss per trade and daily loss limits
- **Strategy Restrictions**: Different strategies allowed per risk level
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
   curl http://localhost:8000/health
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

5. **Access API documentation**
   - Swagger UI: http://localhost:8000/docs
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
   python -m app.core.main
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
python -m app.core.main --mode paper
```

**Live Trading Mode** (requires explicit user approval):
```bash
python -m app.core.main --mode live --approve-live-trading
```

## API Endpoints

### Health Check

```
GET /health
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

```
GET /api/api/dashboard/?user_id={user_id}
```

Get complete dashboard data including portfolio, watchlist, opportunities, trades, news, and risk settings.

```
GET /api/api/dashboard/portfolio?user_id={user_id}
```

Get portfolio summary (total value, cash, positions, P&L).

```
GET /api/api/dashboard/watchlist?user_id={user_id}
```

Get user's watchlist with current prices and data freshness.

```
POST /api/api/dashboard/watchlist/add?user_id={user_id}&symbol={symbol}
```

Add a symbol to watchlist.

```
POST /api/api/dashboard/watchlist/remove?user_id={user_id}&symbol={symbol}
```

Remove a symbol from watchlist.

```
POST /api/api/dashboard/watchlist/validate?symbol={symbol}
```

Validate a stock symbol format.

```
GET /api/api/dashboard/opportunities?user_id={user_id}&limit=10
```

Get top ranked trading opportunities.

```
GET /api/api/dashboard/risk-settings?user_id={user_id}
```

Get user's risk settings and available risk levels.

```
POST /api/api/dashboard/risk-settings/update?user_id={user_id}&risk_level={risk_level}&confirmed={confirmed}
```

Update user's risk level.

## Configuration

The application supports three environments: `dev`, `test`, and `prod`. Configuration is managed via environment variables (see `.env.example`).

### Environment Variables

- `ENVIRONMENT`: Application environment (dev/test/prod, default: dev)
- `DEBUG`: Enable debug mode (default: True in dev)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Secret key for session management
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `LOG_LEVEL`: Logging level (INFO/DEBUG/WARNING/ERROR, default: INFO)
- `API_BASE_URL`: Base URL for API (default: http://localhost:8000/api)
- `DASHBOARD_PREFIX`: Dashboard route prefix (default: /api/dashboard)
- `DEMO_USER_ID`: Demo user ID for local development (default: 1)
- `DATA_PROVIDER`: Data provider to use (yfinance/alpha_vantage/polygon/finnhub)
- `ALPHAVANTAGE_API_KEY`: Alpha Vantage API key
- `POLYGON_API_KEY`: Polygon API key
- `NEWS_API_KEY`: News API key
- `FINNHUB_API_KEY`: Finnhub API key

See `.env.example` for all available configuration options.

## Error Handling

The application includes comprehensive error handling:

- **Validation Errors** (400): Invalid request data
- **Unauthorized** (401): Missing or invalid authentication
- **Forbidden** (403): Insufficient permissions
- **Not Found** (404): Resource not found
- **Internal Server Error** (500): Unexpected server errors

All errors return a consistent JSON response:
```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "status_code": 400
}
```

## MVP User Flow

The MVP defines a complete user journey from authentication through paper trade execution and position tracking. This flow ensures every screen has a defined purpose and no real-money trading occurs.

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ SCREEN 1: LOGIN                                                 │
│ Purpose: Authenticate user and establish session                │
│ User Action: Enter credentials                                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCREEN 2: DASHBOARD OVERVIEW                                    │
│ Purpose: View portfolio, watchlist, opportunities, and trades   │
│ User Action: Review dashboard; manage watchlist; view signals   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCREEN 3: RISK LEVEL SELECTION                                  │
│ Purpose: User defines risk tolerance for scoring algorithm      │
│ User Action: Select Low, Medium, or High risk profile           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCREEN 4: SIGNAL REVIEW & EXPLANATION                           │
│ Purpose: User reviews top-ranked opportunity with full          │
│          breakdown of score factors and estimated downside      │
│ User Action: Review explanation; approve or reject trade        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCREEN 5: PAPER TRADE APPROVAL                                  │
│ Purpose: Confirm paper trade execution (no real money)          │
│ User Action: Approve paper trade entry                          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCREEN 6: POSITION TRACKING                                     │
│ Purpose: Monitor open paper trade position in real-time         │
│ User Action: View P&L, Greeks, and position details             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCREEN 7: TRADE HISTORY & ANALYSIS                              │
│ Purpose: Review closed trades and backtest results              │
│ User Action: Analyze performance; validate strategy             │
└─────────────────────────────────────────────────────────────────┘
```

## Development Workflow

### Code Style

The project uses:
- **Black** for code formatting
- **Flake8** for linting
- **MyPy** for type checking

```bash
# Format code
black app/ services/ tests/

# Lint code
flake8 app/ services/ tests/

# Type check
mypy app/ services/
```

### Adding a New Strategy

1. Create a new file in `app/strategies/` (e.g., `my_strategy.py`)
2. Implement the `Strategy` base class
3. Implement the `generate()` method
4. Register the strategy in the strategy registry
5. Add tests in `tests/test_strategies.py`

Example:
```python
from app.strategies.strategy import Strategy, StrategySignal, MarketData

class MyStrategy(Strategy):
    def __init__(self):
        super().__init__(name="my_strategy")
    
    def generate(self, symbol, market_data, options_chain, news_context=None, risk_profile=None):
        # Implement your strategy logic
        # Return StrategySignal or None
        pass
```

### Adding a New Data Provider

1. Create a new file in `app/data_sources/` (e.g., `my_provider.py`)
2. Implement the `DataProvider` abstract base class
3. Implement required methods: `get_price()`, `get_options_chain()`, `get_news()`
4. Register in configuration
5. Add tests in `tests/test_data_providers.py`

## Backtesting

The project includes a backtesting engine for strategy validation:

```python
from app.backtesting.covered_call_backtest import CoveredCallBacktester
import pandas as pd

# Load historical price data
price_data = pd.read_csv('AAPL_daily.csv', index_col='date', parse_dates=True)

# Run backtest
backtester = CoveredCallBacktester()
result = backtest.backtest('AAPL', price_data)

print(result)
# Output:
# BacktestResult(covered_call on AAPL)
#   Period: 2023-01-01 to 2024-01-01
#   Initial: $100,000.00 -> Final: $112,345.67
#   Return: 12.35% (annualized: 12.35%)
#   Sharpe: 1.23 | Max DD: 8.45%
#   Trades: 12 | Win Rate: 83.33%
```

See `app/backtesting/DECISION.md` for detailed information about the backtesting library choice and limitations.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run tests and linting
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

**This application is for educational and research purposes only.** Options trading involves substantial risk of loss. Past performance does not guarantee future results. The application does not provide financial advice. Users are solely responsible for their trading decisions and must understand the risks involved. Always paper trade first and never risk more than you can afford to lose.
