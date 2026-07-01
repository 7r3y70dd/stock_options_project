"""Base class for strategy-specific backtesting implementations.

Provides framework for testing individual strategies with their own
data preparation, signal generation, and analysis logic.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from app.backtesting.engine import BacktestEngine, BacktestResult

logger = logging.getLogger(__name__)


class StrategyBacktester(ABC):
    """Abstract base class for strategy-specific backtesting.
    
    Subclasses implement strategy-specific signal generation and analysis.
    """

    def __init__(
        self,
        strategy_name: str,
        engine: Optional[BacktestEngine] = None,
    ):
        """Initialize strategy backtester.
        
        Args:
            strategy_name: Name of the strategy
            engine: BacktestEngine instance (creates default if None)
        """
        self.strategy_name = strategy_name
        self.engine = engine or BacktestEngine()

    @abstractmethod
    def generate_signals(
        self,
        price_data: pd.DataFrame,
        **kwargs,
    ) -> pd.DataFrame:
        """Generate trading signals from price data.
        
        Args:
            price_data: DataFrame with OHLCV data
            **kwargs: Strategy-specific parameters
            
        Returns:
            DataFrame with trading signals (1=buy, -1=sell, 0=hold)
        """
        pass

    def backtest(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        **kwargs,
    ) -> BacktestResult:
        """Run backtest for this strategy.
        
        Args:
            symbol: Stock symbol
            price_data: DataFrame with OHLCV data
            **kwargs: Strategy-specific parameters
            
        Returns:
            BacktestResult with performance metrics
        """
        # Generate signals
        signals = self.generate_signals(price_data, **kwargs)
        
        # Run backtest
        result = self.engine.backtest(
            symbol=symbol,
            price_data=price_data,
            signals=signals,
            strategy_name=self.strategy_name,
        )
        
        return result
