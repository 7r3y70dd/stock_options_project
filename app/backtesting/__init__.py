"""Backtesting engine for strategy validation.

This module provides backtesting capabilities for trading strategies using VectorBT.
VectorBT is chosen for its vectorized performance, pandas integration, and ability to
test multiple strategy variations quickly.

Key classes:
- BacktestEngine: Main backtesting orchestrator
- BacktestResult: Results from a single backtest run
- StrategyBacktester: Base class for strategy-specific backtests
"""

from app.backtesting.engine import BacktestEngine, BacktestResult
from app.backtesting.strategy_backtester import StrategyBacktester

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "StrategyBacktester",
]
