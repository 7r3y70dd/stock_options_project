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
- **Web Interface**: Server-rendered HTML pages for dashboard, portfolio, watchlist, trades, and more

## Technology Stack

- **Backend Framework**: FastAPI (async, typed, auto-docs)
- **Web Server**: Uvicorn
- **Frontend**: Server-rendered HTML with Jinja2 templates and vanilla JavaScript
- **Database**: PostgreSQL 13+
- **Cache**: Redis 6+
- **Task Queue**: Celery with Redis broker
- **Backtesting**: VectorBT (vectorized, high-performance)
- **Data Sources**: yfinance, Alpha Vantage, Polygon, Finnhub
- **Testing**: pytest with async support

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
│   │   ├── main.py              # Application entry point with route definitions
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
│   └── frontend/                # Frontend components
│       ├── templates/           # Jinja2 HTML templates
│       │   ├── base.html        # Base layout template
│       │   ├── dashboard.html   # Dashboard page
│       │   ├── opportunities.html # Opportunities list page
│       │   ├── opportunity_detail.html # Opportunity detail page
│       │   ├── portfolio.html   # Portfolio page
│       │   ├── watchlist.html   # Watchlist page
│       │   ├── risk_settings.html # Risk settings page
│       │   ├── trades.html      # Trades list page
│       │   ├── trade_detail.html # Trade detail page
│       │   ├── news.html        # News page
│       │   └── status.html      # System status page
│       ├── static/              # Static assets (CSS, JS)
│       │   ├── app.css          # Main application styles
│       │   ├── app.js           # Main application JavaScript
│       │   └── ...              # Additional CSS/JS files
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
├── scripts/                     # Development scripts
│   ├── dev_dump_frontend_json.py # Dump frontend JSON data
│   ├── dev_ingest_and_recommend.py # Ingest data and generate recommendations
│   └── dev_reseed_database.py   # Reseed database with test data
├── docker-compose.yml           # Docker Compose configuration
├── Dockerfile                   # Docker image definition
├── .env.example                 # Environment variables template
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Key Features

### Web Interface

The application provides a server-rendered HTML interface with the following pages:

- **Dashboard** (`/dashboard`): Comprehensive overview with portfolio summary, watchlist, top opportunities, open trades, recent news, and risk settings
- **Opportunities** (`/opportunities`): Browse and filter trading signals with detailed scoring
- **Opportunity Detail** (`/opportunities/{signal_id}`): Detailed view of a specific trading signal
- **Portfolio** (`/portfolio`): Portfolio overview with positions and performance metrics
- **Watchlist** (`/watchlist`): Manage stock watchlist with add/remove functionality
- **Risk Settings** (`/risk-settings`): Configure risk level and trading mode
- **Trades** (`/trades`): View open and closed trades with P&L tracking
- **Trade Detail** (`/trades/{trade_id}`): Detailed view of a specific trade
- **News** (`/news`): Recent news articles with sentiment analysis
- **Status** (`/status`): System health and status information

All pages use Jinja2 templates with a shared base layout (`base.html`) for consistent navigation and styling.

### Dashboard

The dashboard provides a comprehensive overview of:
- **Portfolio Summary**: Total value, cash, positions, open P&L, and trade counts
- **Watchlist**: Symbols with current prices and data freshness
- **Top Opportunities**: Risk-scored trading signals ranked by confidence
- **Open Trades**: Active positions with entry prices, current P&L, and Greeks
- **Recent News**: Stock news with sentiment analysis
- **Risk Settings**: Current risk level and trading mode configuration

### Frontend Architecture

- **Server-Rendered HTML**: Pages are rendered server-side using Jinja2 templates
- **Static Assets**: CSS and JavaScript files served from `app/frontend/static/`
- **API Communication**: Frontend JavaScript fetches data from REST API endpoints
- **Responsive Design**: Mobile-friendly layout with modern CSS
- **No Build Step**: Pure HTML/CSS/JS without Node.js or bundlers

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
- **Kill Switch**: Emergency trading halt capability

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
   - Web Interface: http://localhost:8000/dashboard
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
# Live trading must be enabled in risk settings via the web interface
# or by setting live_trading_approved=True in the database
python -m uvicorn app.core.main:app --reload
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

Returns complete dashboard data including portfolio summary, watchlist, opportunities, trades, news, and risk settings.

**Query Parameters:**
- `user_id` (required): User ID
- `watchlist_id` (optional): Specific watchlist ID

**Response:**
```json
{
  "portfolio_summary": {
    "total_value": 10000.0,
    "cash": 10000.0,
    "positions_value": 0.0,
    "open_pl": 0.0,
    "open_pl_pct": 0.0,
    "num_open_trades": 0,
    "num_open_signals": 10
  },
  "watchlist": [
    {
      "symbol": "AAPL",
      "current_price": 150.0,
      "added_at": "2024-01-15T10:00:00",
      "last_updated": "2024-01-15T10:30:00",
      "data_freshness_seconds": 300
    }
  ],
  "top_opportunities": [
    {
      "signal_id": 1,
      "symbol": "AAPL",
      "strategy_type": "covered_call",
      "score": 75.5,
      "expected_profit": 100.0,
      "max_loss": -50.0,
      "probability_estimate": 0.65,
      "reason": "High IV with stable price action",
      "status": "pending",
      "created_at": "2024-01-15T10:00:00",
      "breakdown": {
        "liquidity": 80.0,
        "volatility": 70.0,
        "risk": 75.0
      }
    }
  ],
  "open_trades": [
    {
      "trade_id": 1,
      "symbol": "AAPL",
      "strategy_type": "covered_call",
      "entry_price": 2.50,
      "current_price": 2.30,
      "quantity": 1,
      "entry_date": "2024-01-10T10:00:00",
      "current_pl": 20.0,
      "current_pl_pct": 0.08,
      "status": "open"
    }
  ],
  "recent_news": [
    {
      "article_id": 1,
      "symbol": "AAPL",
      "title": "Apple announces new product",
      "description": "Apple unveils latest innovation",
      "url": "https://example.com/article",
      "source": "Example News",
      "published_at": "2024-01-15T09:00:00",
      "sentiment": "positive",
      "sentiment_score": 0.8,
      "event_type": "product_launch"
    }
  ],
  "risk_settings": {
    "risk_level": "medium",
    "paper_trading_enabled": true,
    "live_trading_enabled": false,
    "live_trading_approved": false,
    "risk_levels_info": [
      {
        "level": "low",
        "description": "Conservative strategies",
        "max_position_size_pct": 5.0,
        "allowed_strategies": ["covered_call", "cash_secured_put"],
        "max_loss_per_trade_pct": 2.0,
        "requires_confirmation": false
      }
    ]
  },
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

#### Get Recent News

```
GET /api/api/dashboard/news?user_id={user_id}&limit={limit}
```

#### Get Risk Settings

```
GET /api/api/dashboard/risk-settings?user_id={user_id}
```

#### Update Risk Settings

```
POST /api/api/dashboard/risk-settings/update?user_id={user_id}&risk_level={risk_level}&confirmed={confirmed}
```

## Configuration

The application is configured via environment variables. Copy `.env.example` to `.env` and configure:

### Database

```env
DATABASE_URL=postgresql://user:password@localhost:5432/options_tracker
```

### Redis

```env
REDIS_URL=redis://localhost:6379/0
```

### Data Provider API Keys

```env
ALPHAVANTAGE_API_KEY=your_key_here
POLYGON_API_KEY=your_key_here
NEWS_API_KEY=your_key_here
FINNHUB_API_KEY=your_key_here
```

### Application Settings

```env
ENVIRONMENT=development
LOG_LEVEL=INFO
VERSION=0.1.0
```

### Risk Management

```env
DEFAULT_RISK_LEVEL=medium
PAPER_TRADING_ENABLED=true
LIVE_TRADING_ENABLED=false
```

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
2. Implement the `Strategy` base class
3. Register the strategy in the strategy registry
4. Add tests in `tests/test_strategies.py`

Example:

```python
from app.strategies.strategy import Strategy, StrategySignal, MarketData, NewsContext
from services import RiskLevel
from typing import Optional, List
from services.options_service import OptionContract

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
        pass
```

### Adding a New Data Provider

1. Create a new file in `app/data_sources/` (e.g., `new_provider.py`)
2. Implement the `DataProvider` interface
3. Add configuration for API keys
4. Add tests in `tests/test_data_providers.py`

### Development Scripts

```bash
# Dump frontend JSON data for testing
python scripts/dev_dump_frontend_json.py

# Ingest data and generate recommendations
python scripts/dev_ingest_and_recommend.py

# Reseed database with test data
python scripts/dev_reseed_database.py
```

## Backtesting

Run backtests using the backtesting engine:

```python
from app.backtesting.engine import BacktestEngine
import pandas as pd

# Initialize engine
engine = BacktestEngine(initial_cash=100000.0)

# Load price data
price_data = pd.DataFrame({
    'date': [...],
    'open': [...],
    'high': [...],
    'low': [...],
    'close': [...],
    'volume': [...]
})
price_data.set_index('date', inplace=True)

# Generate signals (1=buy, -1=sell, 0=hold)
signals = pd.Series([...])

# Run backtest
result = engine.backtest(
    symbol='AAPL',
    price_data=price_data,
    signals=signals,
    strategy_name='my_strategy'
)

print(result)
print(f"Total Return: {result.total_return:.2f}%")
print(f"Win Rate: {result.win_rate:.2%}")
print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Contribution Guidelines

- Write tests for new features
- Follow PEP 8 style guidelines
- Add docstrings to all functions and classes
- Update README.md if adding new features
- Ensure all tests pass before submitting PR

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and research purposes only. It is not financial advice. Options trading involves substantial risk of loss. Past performance does not guarantee future results. Always consult with a qualified financial advisor before making investment decisions. The authors and contributors are not responsible for any financial losses incurred through the use of this software.
