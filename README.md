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

## Quick Start

### Prerequisites

- Python 3.9+
- pip or conda
- Docker and Docker Compose (optional, for containerized setup)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/options-tracker.git
   cd options-tracker
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

5. **Run tests**
   ```bash
   pytest -v
   ```

6. **Start the application**
   ```bash
   python -m uvicorn app.main:app --reload
   ```
   The app will be available at `http://localhost:8000`

### Docker Setup

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```
   The app will be available at `http://localhost:8000`

2. **Stop the application**
   ```bash
   docker-compose down
   ```

## Environment Configuration

Create a `.env` file in the project root (see `.env.example` for template):

```bash
# API Keys (required for data fetching)
ALPHAVANTAGE_API_KEY=your_key_here
POLYGON_API_KEY=your_key_here
NEWS_API_KEY=your_key_here

# Database
DATABASE_URL=sqlite:///./options_tracker.db

# Application
DEBUG=False
LOG_LEVEL=INFO

# Paper Trading (enabled by default)
PAPER_TRADING_ENABLED=True
INITIAL_PORTFOLIO_VALUE=100000

# Live Trading (disabled by default)
LIVE_TRADING_ENABLED=False
BROKER_API_KEY=your_broker_key_here
BROKER_SECRET_KEY=your_broker_secret_here
```

## Project Structure

```
options-tracker/
├── app/                          # Main application package
│   ├── api/                      # API routes and endpoints
│   ├── core/                     # Core configuration and utilities
│   ├── data_sources/             # Market data, options chains, news integrations
│   ├── models/                   # Data models (options, positions, trades)
│   ├── news/                     # News analysis and sentiment scoring
│   ├── options/                  # Options analysis and scoring
│   ├── risk/                     # Risk management and guardrails
│   ├── strategies/               # Trading strategies and signal generation
│   ├── trading/                  # Paper and live trading execution
│   ├── backtesting/              # Backtesting engine and historical analysis
│   ├── workers/                  # Background workers and async tasks
│   └── main.py                   # Application entry point
├── services/                     # Legacy services (risk configs, options service)
│   ├── __init__.py
│   ├── options_service.py
│   └── test_risk_guardrails.py
├── tests/                        # Test suite
│   └── __init__.py
├── scripts/                      # Utility scripts
├── docker-compose.yml            # Docker Compose configuration
├── Dockerfile                    # Docker image definition
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
├── README.md                     # This file
└── .gitignore                    # Git ignore rules
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
- **Explainability**: Screens 5 and 8 show reasoning (score breakdown, exit rationale) so users understand why the app recommends each action.
- **Risk Awareness**: Screen 3 and Screen 5 emphasize risk level and estimated downside before any trade is approved.

## Risk Levels

The app supports three risk profiles. Each profile scores opportunities by expected return, probability estimate, liquidity, volatility, and news sentiment:

### Low Risk

Focuses on defined-risk or asset-backed strategies such as:

- Covered calls
- Cash-secured puts
- Conservative spreads
- Higher-liquidity contracts
- Lower max loss per trade

**Estimated Downside**: Max loss is capped by the strategy structure (e.g., premium received for covered calls).

**Concrete Filters**:
- Allowed strategies: covered calls, cash-secured puts, defined-risk spreads only
- Max position size: 5% of portfolio
- Max loss per trade: 2% of portfolio
- Max daily loss: 3% of portfolio
- Expiration window: 7–60 days
- Strike selection: Near-the-money only (0.95–1.05 moneyness)
- Min liquidity score: 70/100
- Min volume: 50 contracts
- Min open interest: 100 contracts
- Max bid-ask spread: 5% of mid price
- Earnings buffer: 5 days before/after earnings
- Max open positions: 5

### Medium Risk

Allows more directional exposure and moderate risk, such as:

- Debit spreads
- Credit spreads
- Earnings-aware trades
- Moderate expiration windows
- Medium position sizing

**Estimated Downside**: Max loss is defined by the spread width or debit paid; users should size positions accordingly.

**Concrete Filters**:
- Allowed strategies: covered calls, cash-secured puts, spreads, earnings-aware trades
- Max position size: 10% of portfolio
- Max loss per trade: 5% of portfolio
- Max daily loss: 5% of portfolio
- Expiration window: 3–90 days
- Strike selection: Slightly wider range (0.90–1.10 moneyness)
- Min liquidity score: 50/100
- Min volume: 20 contracts
- Min open interest: 50 contracts
- Max bid-ask spread: 8% of mid price
- Earnings buffer: 3 days before/after earnings
- Max open positions: 10

### High Risk

Allows more aggressive trades, such as:

- Long calls
- Long puts
- Shorter expiration contracts
- Higher volatility opportunities
- Larger potential reward with higher probability of loss
- **Note**: No naked short calls (unlimited risk strategies are excluded)

**Estimated Downside**: Max loss can be substantial (up to 100% of premium paid for long options).

**Concrete Filters**:
- Allowed strategies: long calls, long puts, short-duration trades, high-IV opportunities (but no naked short calls)
- Max position size: 15% of portfolio
- Max loss per trade: 10% of portfolio
- Max daily loss: 10% of portfolio
- Expiration window: 1–120 days
- Strike selection: Wider range for directional plays (0.80–1.20 moneyness)
- Min liquidity score: 30/100
- Min volume: 5 contracts
- Min open interest: 10 contracts
- Max bid-ask spread: 12% of mid price
- Earnings buffer: 1 day before/after earnings
- Max open positions: 15

## Risk Level Implementation

This section documents how risk levels are implemented in the service layer and how they affect strategy filtering, scoring, and position sizing.

### Risk Level Configuration

Each risk level is defined by a `RiskLevelConfig` object in `services/__init__.py` that specifies:

1. **Allowed Strategies**: List of strategy types permitted at this risk level
   - Low: covered calls, cash-secured puts, defined-risk spreads
   - Medium: spreads, earnings-aware trades, credit/debit spreads
   - High: long calls/puts, short-duration trades, high-IV opportunities

2. **Position Sizing**: Maximum position size as a percentage of portfolio
   - Low: 5%
   - Medium: 10%
   - High: 15%

3. **Loss Limits**: Maximum loss per trade and per day
   - Low: 2% per trade, 3% per day
   - Medium: 5% per trade, 5% per day
   - High: 10% per trade, 10% per day

4. **Liquidity Requirements**: Minimum volume, open interest, and bid-ask spread
   - Low: Strictest requirements (50 vol, 100 OI, 5% spread)
   - Medium: Moderate requirements (20 vol, 50 OI, 8% spread)
   - High: Relaxed requirements (5 vol, 10 OI, 12% spread)

5. **Scoring Weights**: How different factors contribute to the overall score
   - Low: Emphasizes liquidity and spread (55% combined)
   - Medium: Balanced across all factors
   - High: Emphasizes volatility and time decay (60% combined)

## Testing

Run the test suite to verify the application:

```bash
# Run all tests
pytest -v

# Run specific test file
pytest services/test_risk_guardrails.py -v

# Run with coverage
pytest --cov=services --cov=app tests/
```

## Development

### Adding New Features

1. Create feature branch: `git checkout -b feature/your-feature`
2. Implement changes in appropriate `app/` subdirectory
3. Add tests in `tests/` directory
4. Run tests and ensure they pass
5. Submit pull request

### Code Style

This project follows PEP 8. Use `black` for formatting:

```bash
black app/ services/ tests/
```

## Troubleshooting

### Import Errors

Ensure the virtual environment is activated and dependencies are installed:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Database Issues

Reset the database:

```bash
rm options_tracker.db
python -c "from app.core.database import init_db; init_db()"
```

### API Key Issues

Verify your `.env` file has valid API keys for all required services.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
