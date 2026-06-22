# Options Tracker

A stock options research and paper-trading application that helps users find, score, and track options opportunities based on their selected risk level.

⚠️ **IMPORTANT DISCLAIMER**: This app does **not** promise guaranteed profits or "sure bets." Options trading is inherently risky. All signals and recommendations should be treated as research ideas for educational purposes only, not as financial advice. Past performance does not guarantee future results. Users must understand the risks of options trading, including the potential loss of the entire investment. Always paper trade first before considering any live trading.

## Overview

Options Tracker allows users to:

- Create a stock watchlist
- Fetch stock price and options-chain data
- Pull relevant stock news
- Analyze options opportunities
- Score risk-scored opportunities based on risk, liquidity, volatility, and news sentiment
- Choose a risk level: low, medium, or high
- **Paper trade first** to test strategies without risking real money
- Backtest strategies
- Track open and closed trades

**Live trading is disabled by default.** Users must explicitly enable live trading after understanding the risks and completing paper trading validation.

## Technology Stack

- **Backend Framework**: FastAPI (async, typed, auto-docs)
- **Web Server**: Uvicorn
- **Database**: PostgreSQL
- **Cache**: Redis
- **Testing**: pytest

## Project Structure

```
options-tracker/
├── app/
│   ├── api/                 # REST API endpoints
│   ├── core/                # Core application logic, config, error handling
│   ├── data_sources/        # External data fetching (market data, news)
│   ├── models/              # Data models and schemas
│   ├── news/                # News analysis and sentiment
│   ├── options/             # Options-specific logic
│   ├── risk/                # Risk management and guardrails
│   ├── strategies/          # Trading strategy definitions
│   ├── trading/             # Trade execution and management
│   ├── backtesting/         # Backtesting engine
│   ├── workers/             # Background job workers
│   └── frontend/            # Frontend assets and templates
├── services/                # Service layer (risk configs, scoring)
├── tests/                   # Test suite
├── scripts/                 # Utility scripts
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # Docker image definition
├── .env.example             # Environment variables template
├── requirements.txt         # Python dependencies
├── README.md                # This file
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for containerized setup)
- PostgreSQL 13+ (if running without Docker)
- Redis 6+ (if running without Docker)

### Local Development Setup

#### Option 1: Using Docker Compose (Recommended)

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

#### Option 2: Local Python Setup

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
   python -m app.core.migrations
   ```

6. **Start Redis** (in a separate terminal)
   ```bash
   redis-server
   ```

7. **Run the application**
   ```bash
   python -m app.core.main
   ```
   The app will start on http://localhost:8000

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test module
python -m pytest services/test_risk_guardrails.py -v

# Run with coverage
python -m pytest --cov=app --cov=services

# Run tests in Docker
docker-compose exec app pytest
```

### Running the Application

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
│ SCREEN 2: WATCHLIST SELECTION                                   │
│ Purpose: User selects which stocks to analyze                   │
│ User Action: Choose from saved watchlist or add new symbols     │
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
│ SCREEN 4: DATA FETCH & RANKING                                  │
│ Purpose: App fetches market/options/news data and ranks         │
│          opportunities by risk-scored signals                   │
│ User Action: Wait for data load; view ranked opportunities      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCREEN 5: SIGNAL REVIEW & EXPLANATION                           │
│ Purpose: User reviews top-ranked opportunity with full          │
│          breakdown of score factors and estimated downside      │
│ User Action: Review explanation; approve or reject trade        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCREEN 6: PAPER TRADE APPROVAL                                  │
│ Purpose: Confirm paper trade execution (no real money)          │
│ User Action: Approve paper trade entry                          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCREEN 7: POSITION TRACKING                                     │
│ Purpose: Monitor open paper trade position in real-time         │
│ User Action: View P&L, Greeks, and position details             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCREEN 8: EXIT RECOMMENDATION                                   │
│ Purpose: App generates exit signal based on price/Greeks/time   │
│ User Action: Review exit recommendation; close paper trade      │
└─────────────────────────────────────────────────────────────────┘
```

### Screen Definitions

| Screen | Purpose | User Input | App Output |
|--------|---------|-----------|------------|
| 1. Login | Authenticate user and establish session | Email/password | Session token; redirect to watchlist |
| 2. Watchlist Selection | User selects which stocks to analyze | Choose symbols from saved list or add new | Selected watchlist symbols |
| 3. Risk Level Selection | User defines risk tolerance for scoring | Select Low / Medium / High | Risk profile stored for scoring |
| 4. Data Fetch & Ranking | App fetches market/options/news; ranks opportunities | None (automatic) | Ranked list of top 5–10 opportunities |
| 5. Signal Review & Explanation | User reviews top opportunity with full breakdown | Approve or reject | Score breakdown, estimated downside, Greeks |
| 6. Paper Trade Approval | Confirm paper trade execution (no real money) | Approve paper trade | Paper trade created; position opened |
| 7. Position Tracking | Monitor open paper trade in real-time | None (view-only) | Live P&L, Greeks, bid/ask, time decay |
| 8. Exit Recommendation | App generates exit signal; user closes trade | Close position | Exit recommendation reason; trade closed |

### Key Constraints

- **No Real-Money Trading**: All trades in MVP are paper trades only. Live trading is disabled by default.
- **Every Screen Has Purpose**: Each screen advances the user toward a complete trade cycle (entry → monitoring → exit).
- **Explainability**: Screens 5 and 8 show reasoning (score breakdown, exit rationale) so users understand the app's logic.
