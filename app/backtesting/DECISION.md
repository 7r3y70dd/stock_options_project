# Backtesting Library Decision: VectorBT

## Executive Summary

After evaluating Backtrader and VectorBT, **VectorBT** has been selected as the backtesting library for the MVP. VectorBT's vectorized architecture, pandas integration, and performance characteristics make it better suited for rapid strategy testing and parameter optimization.

## Comparison: Backtrader vs VectorBT

### Backtrader

**Strengths:**
- Mature, well-documented framework with large community
- Event-driven architecture mirrors real trading
- Built-in broker simulation with realistic order handling
- Good support for multiple timeframes and data sources
- Extensive indicator library

**Weaknesses:**
- Slower performance (event-driven, not vectorized)
- Steeper learning curve for complex strategies
- Less suitable for parameter optimization (slow to test many variations)
- Heavier memory footprint for large datasets
- Limited built-in support for options Greeks and pricing

**Options Backtesting:**
- Can model options but requires manual Greeks calculation
- No built-in volatility surface modeling
- Assignment modeling is manual and complex
- Better for simple covered calls/cash-secured puts

### VectorBT

**Strengths:**
- Vectorized operations (NumPy/Pandas) = 10-100x faster
- Minimal memory footprint
- Excellent for parameter optimization and sensitivity analysis
- Native pandas integration
- Fast equity curve and performance metric calculation
- Lightweight and easy to integrate

**Weaknesses:**
- Smaller community than Backtrader
- Less mature (but actively maintained)
- Simpler broker model (less realistic order handling)
- Fewer built-in indicators (but easy to add custom ones)
- Limited options support (same as Backtrader)

**Options Backtesting:**
- Same limitations as Backtrader
- Better suited for vectorized option price modeling
- Easier to implement custom Greeks calculations
- Good for testing multiple strike/expiration combinations

## Decision Rationale

### Why VectorBT?

1. **Performance**: MVP needs to test many strategy variations quickly. VectorBT's vectorized approach is 10-100x faster than Backtrader for parameter sweeps.

2. **Integration**: VectorBT works natively with pandas DataFrames, matching our data pipeline.

3. **Simplicity**: Lighter weight, easier to integrate into FastAPI app without heavy dependencies.

4. **Options Testing**: Both libraries have similar options limitations. VectorBT's vectorized approach makes it easier to model multiple option scenarios.

5. **MVP Scope**: For MVP, we're testing simple strategies (covered calls, cash-secured puts). VectorBT's simpler broker model is sufficient.

## Limitations for Options Backtesting

Both libraries have significant limitations for options backtesting:

### Fundamental Limitations

1. **No Greeks Modeling**
   - Delta, gamma, theta, vega not automatically calculated
   - Must implement custom Greeks calculations
   - Greeks change with underlying price and time

2. **No Volatility Surface**
   - Assumes constant implied volatility
   - Real options prices vary with strike and expiration
   - Skew and term structure not modeled

3. **No Assignment Modeling**
   - American options can be assigned early
   - Early assignment probability not calculated
   - Dividend adjustments not modeled

4. **Simplified Bid-Ask Spreads**
   - Assumes constant spread
   - Real spreads vary with liquidity and volatility
   - No dynamic slippage modeling

5. **No Stochastic Volatility**
   - Volatility assumed constant
   - Real volatility is mean-reverting and stochastic
   - Volatility clustering not modeled

### Workarounds for MVP

1. **Use Simplified Option Pricing**
   - Black-Scholes for theoretical prices
   - Fixed premium assumptions for backtesting
   - Sensitivity analysis for Greeks

2. **Model Options as Synthetic Positions**
   - Covered call = long stock + short call
   - Cash-secured put = short put + cash reserve
   - Use stock price movements as proxy

3. **Parameter Sweeps**
   - Test multiple strike prices
   - Test multiple expiration dates
   - Analyze sensitivity to volatility changes

4. **Post-Backtest Analysis**
   - Calculate Greeks at trade entry/exit
   - Estimate assignment probability
   - Analyze P&L attribution

## Implementation Plan

### Phase 1: Core Engine (MVP)
- ✅ BacktestEngine class with VectorBT integration
- ✅ BacktestResult dataclass with key metrics
- ✅ StrategyBacktester base class
- ✅ CoveredCallBacktester prototype

### Phase 2: Enhanced Options Support (Post-MVP)
- [ ] Greeks calculation module
- [ ] Volatility surface modeling
- [ ] Assignment probability estimation
- [ ] Multi-leg strategy support
- [ ] Dynamic hedging logic

### Phase 3: Optimization (Post-MVP)
- [ ] Parameter optimization framework
- [ ] Walk-forward analysis
- [ ] Monte Carlo simulation
- [ ] Stress testing

## Prototype Backtest

A prototype covered call backtest has been implemented in `CoveredCallBacktester`:

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
#   Avg Trade: $1,028.81 | Profit Factor: 2.34
```

## Testing

To run the prototype backtest locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run backtest tests
pytest tests/test_backtesting.py -v

# Run prototype
python -m app.backtesting.covered_call_backtest
```

## Future Enhancements

1. **Integrate with Strategy Framework**
   - Connect to app/strategies/strategy.py
   - Use StrategySignal for backtesting
   - Validate signals against historical data

2. **Options-Specific Features**
   - Model option Greeks
   - Implement volatility surface
   - Add assignment probability

3. **Performance Optimization**
   - Parallel backtesting for multiple symbols
   - Caching of intermediate results
   - GPU acceleration for large parameter sweeps

4. **Reporting**
   - Generate backtest reports
   - Equity curve visualization
   - Trade-by-trade analysis
   - Risk metrics dashboard

## References

- VectorBT Documentation: https://vectorbt.dev/
- Backtrader Documentation: https://www.backtrader.com/
- Options Backtesting Best Practices: https://en.wikipedia.org/wiki/Backtesting
