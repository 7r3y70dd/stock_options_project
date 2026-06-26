"""Strategy implementations and registry.

Provides strategy interface, signal generation, and strategy management.
"""

from app.strategies.strategy import (
    MarketData,
    NewsContext,
    StrategySignal,
    Strategy,
    StrategyRegistry,
    get_strategy_registry,
    set_strategy_registry,
)
from app.strategies.covered_call import CoveredCallStrategy
from app.strategies.cash_secured_put import CashSecuredPutStrategy
from app.strategies.debit_spread import DebitSpreadStrategy

__all__ = [
    "MarketData",
    "NewsContext",
    "StrategySignal",
    "Strategy",
    "StrategyRegistry",
    "get_strategy_registry",
    "set_strategy_registry",
    "CoveredCallStrategy",
    "CashSecuredPutStrategy",
    "DebitSpreadStrategy",
]
