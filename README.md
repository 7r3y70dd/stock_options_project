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
|--------|---------|-----------|------------||
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
- Expiration window: 7–60 days
- Strike selection: Near-the-money only (0.95–1.05 moneyness)
- Min liquidity score: 70/100

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
- Expiration window: 3–90 days
- Strike selection: Slightly wider range (0.90–1.10 moneyness)
- Min liquidity score: 50/100

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
- Expiration window: 1–120 days
- Strike selection: Wider range for directional plays (0.80–1.20 moneyness)
- Min liquidity score: 30/100

## Risk Level Implementation

This section documents how risk levels are implemented in the service layer and how they affect strategy filtering, scoring, and position sizing.

### Risk Level Configuration

Each risk level is defined by a `RiskLevelConfig` object in `services/__init__.py` that specifies:

1. **Allowed Strategies**: List of strategy types permitted at this risk level
   - Low: covered calls, cash-secured puts, defined-risk spreads
   - Medium: spreads, earnings-aware trades, credit/debit spreads
   - High: long calls/puts, short-duration trades, high-IV opportunities

2. **Position Sizing Limits**:
   - Max position size as % of portfolio
   - Max loss per trade as % of portfolio
   - Recommended position size based on max loss

3. **Expiration & Strike Filters**:
   - Min/max days to expiration
   - Moneyness range (strike / underlying price)
   - Min liquidity score threshold

4. **Scoring Weights**: Risk-level-specific factor weights
   - Low: Emphasizes liquidity (30%) and spread tightness (25%)
   - Medium: Balanced across all factors
   - High: Emphasizes volatility (30%) and time decay (30%)

5. **Warning Thresholds**: Risk-level-specific alert triggers
   - Wide spread threshold
   - Low volume/open interest thresholds
   - High IV rank threshold

### Scoring Algorithm

The `OptionsService` class in `services/options_service.py` implements risk-level-aware scoring:

1. **Contract Filtering**: Contracts are filtered by strategy type, expiration, and moneyness
2. **Component Scoring**: Five factors are scored independently:
   - Liquidity (volume + open interest)
   - Spread tightness (bid-ask width)
   - Moneyness (distance from ATM)
   - Implied volatility (moderate IV preferred)
   - Time decay (7–30 days optimal)
3. **Risk-Weighted Scoring**: Component scores are weighted by risk level
4. **Grade Assignment**: Scores are mapped to grades (watchlist, candidate, avoid)
5. **Max Loss Calculation**: Strategy-specific max loss is calculated
6. **Position Sizing**: Recommended position size is derived from max loss

### Acceptance Criteria Fulfillment

✅ **Risk level changes actual strategy filters**: Each risk level has a distinct `allowed_strategies` list. Contracts are filtered by strategy type before scoring.

✅ **Risk level changes max loss limits**: Each risk level defines `max_loss_per_trade_pct` and `max_position_size_pct`. Position sizing is calculated based on these limits.

✅ **Risk level changes expiration/strike filters**: Each risk level defines `min_days_to_expiration`, `max_days_to_expiration`, and `moneyness_range`. Contracts outside these ranges are rejected.

## Core Features

### Watchlist

Users can add stocks they want the app to monitor.

### Market Data

The app can source data from free or low-cost APIs such as:

- Alpha Vantage
- yfinance
- Finnhub
- MarketAux
- Alpaca
- Tradier Sandbox

### News Analysis

The app collects relevant financial news for watchlist symbols and can use sentiment scoring to determine whether the news appears bullish, bearish, or neutral.

### Options Analysis

The app analyzes options using:

- Bid/ask spread
- Volume
- Open interest
- Implied volatility
- Historical volatility
- Greeks
- Expiration date
- Strike price
- Max profit
- Max loss
- Breakeven price

### Signal Scoring

Each risk-scored opportunity receives a score based on:

- Liquidity
- Risk/reward ratio
- Probability estimate
- News sentiment
- Volatility profile
- Event risk
- User risk level

**Every recommendation includes estimated downside risk.** Scores are explainable and transparent; users can see the breakdown of factors contributing to each score.

### Paper Trading (Required First Step)

**Paper trading is the first and required mode.** Users must validate their strategy and risk management in paper trading before considering live execution.

Paper trading allows users to:

- Test strategies without risking real money
- Validate signal quality and timing
- Practice risk management
- Build confidence in their approach

### Live Trading (Disabled by Default)

Live trading is **disabled by default** and requires explicit user opt-in after:

1. Completing paper trading validation
2. Acknowledging all risk disclaimers
3. Confirming understanding of max loss per trade
4. Setting position size limits

**Warning**: Enabling live trading means real money is at risk. Users are solely responsible for their trading decisions and losses.

## Suggested Tech Stack

### Backend

- Python
- Flask or FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Celery or RQ

### Frontend

- React, Next.js, or simple server-rendered templates
- Tailwind CSS or Bootstrap

### Data / Analysis

- pandas
- numpy
- scipy
- yfinance
- QuantLib
- Backtrader or VectorBT
- FinBERT or another finance sentiment model

### Deployment

- Docker
- Kubernetes or simple VPS
- GitHub Actions for CI/CD
