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
   - Wide spread warnings
   - Low volume warnings
   - Low open interest warnings
   - High IV rank warnings

## Global Risk Guardrails

The app enforces hard constraints to prevent reckless trading. These guardrails are checked before any trade is approved, whether paper or live.

### Guardrail Rules

1. **Max Loss Per Trade**: Trade is rejected if max loss exceeds the risk level's limit
   - Low: 2% of portfolio
   - Medium: 5% of portfolio
   - High: 10% of portfolio

2. **Max Contracts Per Trade**: Hard limit of 10 contracts per trade

3. **Max Daily Loss**: Trade is rejected if projected daily loss would exceed the risk level's limit
   - Low: 3% of portfolio
   - Medium: 5% of portfolio
   - High: 10% of portfolio

4. **Max Open Positions**: Trade is rejected if current open positions meet or exceed the risk level's limit
   - Low: 5 positions
   - Medium: 10 positions
   - High: 15 positions

5. **Bid-Ask Spread**: Trade is rejected if spread exceeds the risk level's maximum
   - Low: 5% of mid price
   - Medium: 8% of mid price
   - High: 12% of mid price

6. **Volume**: Trade is rejected if contract volume is below the risk level's minimum
   - Low: 50 contracts
   - Medium: 20 contracts
   - High: 5 contracts

7. **Open Interest**: Trade is rejected if open interest is below the risk level's minimum
   - Low: 100 contracts
   - Medium: 50 contracts
   - High: 10 contracts

8. **Earnings Window**: Trade is rejected if expiration falls within the earnings buffer window
   - Low: 5 days before/after earnings
   - Medium: 3 days before/after earnings
   - High: 1 day before/after earnings

9. **Live Trading Approval**: Live trades are rejected by default unless user has explicitly approved live trading
   - Paper trades are always allowed
   - Live trades require explicit user opt-in

### Rejection Messages

When a trade is rejected, the app provides a human-readable reason:

- "Max loss per trade (X%) exceeds limit (Y%) for [risk level] risk level."
- "Number of contracts (X) exceeds maximum (10)."
- "Projected daily loss (X%) would exceed limit (Y%) for [risk level] risk level."
- "Current open positions (X) meets or exceeds maximum (Y) for [risk level] risk level."
- "Bid-ask spread (X%) exceeds maximum (Y%) for [risk level] risk level."
- "Contract volume (X) is below minimum (Y) for [risk level] risk level."
- "Contract open interest (X) is below minimum (Y) for [risk level] risk level."
- "Trade is within X days of earnings date (YYYY-MM-DD). Restricted for [risk level] risk level."
- "Live trading is disabled by default. User must explicitly approve live trading before any real-money trades can be executed."

### RiskEngine Implementation

The `RiskEngine` class in `services/options_service.py` validates trades against all guardrails:

```python
engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
guardrail = engine.validate_trade(
    contract,
    max_loss_pct=2.5,
    num_contracts=1,
    current_daily_loss_pct=1.0,
    current_open_positions=3,
    is_live_trading=False,
    user_approved_live_trading=False,
)

if guardrail.passed:
    print("Trade approved!")
else:
    print(f"Trade rejected: {guardrail.message}")
```

## Signal Scoring

Each opportunity is scored on a 0–100 scale based on five factors:

1. **Liquidity** (weight varies by risk level): Volume + open interest
2. **Spread** (weight varies by risk level): Bid-ask spread tightness
3. **Moneyness** (weight varies by risk level): Distance from at-the-money
4. **Volatility** (weight varies by risk level): Implied volatility level
5. **Time Decay** (weight varies by risk level): Days to expiration

Scores are normalized to 0–100 and mapped to grades:

- **Watchlist** (75–100): High-confidence opportunities
- **Candidate** (50–74): Medium-confidence opportunities
- **Avoid** (0–49): Low-confidence opportunities

Each score includes a breakdown showing the contribution of each factor, so users understand why the app ranked an opportunity.

## Paper Trading

**Paper trading is required before live trading.** Paper trades allow users to:

- Test strategies without risking real money
- Validate the app's scoring and recommendations
- Build confidence in the risk level selection
- Understand how positions behave in real market conditions

Paper trades are tracked separately from live trades and do not affect real portfolio performance.

## Live Trading

**Live trading is disabled by default.** To enable live trading, users must:

1. Complete at least one full paper trade cycle (entry → monitoring → exit)
2. Explicitly opt-in to live trading in the app settings
3. Confirm understanding of the risks and disclaimers

Once enabled, live trades are subject to the same guardrails as paper trades. Users can disable live trading at any time.

## Testing

Unit tests cover all risk guardrails and rejection scenarios:

```bash
pytest -q services/test_risk_guardrails.py
```

Tests verify:
- Each guardrail rejects trades correctly
- Rejection messages are human-readable
- Paper trades bypass live trading approval
- Risk level changes affect guardrail thresholds
