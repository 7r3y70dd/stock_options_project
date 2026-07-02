"""Backtesting module for strategy evaluation.

Provides backtesting engine and related utilities.
Note: vectorbt is lazily imported to avoid initialization errors during test collection.
"""

# Lazy imports to avoid requiring vectorbt during test collection
def __getattr__(name):
    """Lazy load backtesting components."""
    if name == "BacktestEngine":
        from app.backtesting.engine import BacktestEngine
        return BacktestEngine
    elif name == "BacktestResult":
        from app.backtesting.engine import BacktestResult
        return BacktestResult
    elif name == "SimulatedTrade":
        from app.backtesting.engine import SimulatedTrade
        return SimulatedTrade
    elif name == "PaperTradingComparison":
        from app.backtesting.engine import PaperTradingComparison
        return PaperTradingComparison
    elif name == "StrategyBacktester":
        from app.backtesting.strategy_backtester import StrategyBacktester
        return StrategyBacktester
    elif name == "CoveredCallBacktester":
        from app.backtesting.covered_call_backtest import CoveredCallBacktester
        return CoveredCallBacktester
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "SimulatedTrade",
    "PaperTradingComparison",
    "StrategyBacktester",
    "CoveredCallBacktester",
]
