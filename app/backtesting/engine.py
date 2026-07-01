"""Core backtesting engine using VectorBT.

Provides vectorized backtesting for trading strategies with support for
multiple strategy variations, parameter optimization, and detailed performance metrics.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import vectorbt as vbt

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Results from a backtest run.
    
    Attributes:
        strategy_name: Name of the strategy tested
        symbol: Stock symbol tested
        start_date: Backtest start date
        end_date: Backtest end date
        initial_cash: Starting capital
        final_value: Final portfolio value
        total_return: Total return percentage
        annual_return: Annualized return percentage
        sharpe_ratio: Sharpe ratio (risk-adjusted return)
        max_drawdown: Maximum drawdown percentage
        win_rate: Percentage of winning trades
        total_trades: Number of trades executed
        avg_trade_profit: Average profit per trade
        best_trade: Best single trade profit
        worst_trade: Worst single trade loss
        profit_factor: Gross profit / gross loss
        trades: DataFrame with individual trade details
        equity_curve: Series with daily portfolio values
        metadata: Additional metadata from backtest
    """
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_cash: float
    final_value: float
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    avg_trade_profit: float
    best_trade: float
    worst_trade: float
    profit_factor: float
    trades: Optional[pd.DataFrame] = None
    equity_curve: Optional[pd.Series] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "initial_cash": self.initial_cash,
            "final_value": self.final_value,
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "avg_trade_profit": self.avg_trade_profit,
            "best_trade": self.best_trade,
            "worst_trade": self.worst_trade,
            "profit_factor": self.profit_factor,
        }

    def __str__(self) -> str:
        """String representation of backtest result."""
        return (
            f"BacktestResult({self.strategy_name} on {self.symbol})\n"
            f"  Period: {self.start_date.date()} to {self.end_date.date()}\n"
            f"  Initial: ${self.initial_cash:,.2f} -> Final: ${self.final_value:,.2f}\n"
            f"  Return: {self.total_return:.2%} (annualized: {self.annual_return:.2%})\n"
            f"  Sharpe: {self.sharpe_ratio:.2f} | Max DD: {self.max_drawdown:.2%}\n"
            f"  Trades: {self.total_trades} | Win Rate: {self.win_rate:.2%}\n"
            f"  Avg Trade: ${self.avg_trade_profit:,.2f} | Profit Factor: {self.profit_factor:.2f}"
        )


class BacktestEngine:
    """Vectorized backtesting engine using VectorBT.
    
    Provides high-performance backtesting for trading strategies with support for:
    - Multiple strategy variations and parameter optimization
    - Detailed performance metrics and risk analysis
    - Trade-level analysis and equity curve tracking
    - Vectorized operations for speed
    
    Limitations for options backtesting:
    - Does not model option Greeks (delta, gamma, theta, vega)
    - Assumes constant bid-ask spreads (no dynamic slippage)
    - Does not model early assignment for American options
    - Does not account for dividend adjustments on options
    - Simplified volatility modeling (no stochastic volatility)
    - No support for complex multi-leg strategies with dynamic hedging
    """

    def __init__(
        self,
        initial_cash: float = 100000.0,
        commission: float = 0.001,  # 0.1% per trade
        slippage: float = 0.0005,  # 0.05% slippage
        risk_free_rate: float = 0.05,  # 5% annual
    ):
        """Initialize backtesting engine.
        
        Args:
            initial_cash: Starting capital in dollars
            commission: Commission per trade as decimal (0.001 = 0.1%)
            slippage: Slippage per trade as decimal (0.0005 = 0.05%)
            risk_free_rate: Risk-free rate for Sharpe ratio calculation
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage
        self.risk_free_rate = risk_free_rate

    def backtest(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        signals: pd.DataFrame,
        strategy_name: str = "strategy",
    ) -> BacktestResult:
        """Run backtest on price data with trading signals.
        
        Args:
            symbol: Stock symbol
            price_data: DataFrame with OHLCV data (index=date, columns=[open, high, low, close, volume])
            signals: DataFrame with trading signals (1=buy, -1=sell, 0=hold)
            strategy_name: Name of strategy being tested
            
        Returns:
            BacktestResult with performance metrics
            
        Raises:
            ValueError: If price_data or signals are invalid
        """
        if price_data.empty:
            raise ValueError("price_data cannot be empty")
        if signals.empty:
            raise ValueError("signals cannot be empty")
        if len(price_data) != len(signals):
            raise ValueError("price_data and signals must have same length")

        # Extract close prices
        close_prices = price_data["close"].values
        
        # Create portfolio using VectorBT
        try:
            portfolio = vbt.Portfolio.from_signals(
                close=close_prices,
                entries=signals == 1,
                exits=signals == -1,
                init_cash=self.initial_cash,
                fees=self.commission,
                freq="D",  # Daily frequency
            )
        except Exception as e:
            logger.error(f"Error creating portfolio: {e}")
            raise

        # Calculate metrics
        start_date = price_data.index[0]
        end_date = price_data.index[-1]
        final_value = portfolio.final_value()
        total_return = portfolio.total_return()
        annual_return = portfolio.annualized_return()
        sharpe_ratio = portfolio.sharpe_ratio(risk_free_rate=self.risk_free_rate)
        max_drawdown = portfolio.max_drawdown()
        
        # Trade analysis
        trades = portfolio.trades.records
        total_trades = len(trades) if trades is not None else 0
        
        if total_trades > 0:
            trade_pnl = trades["pnl"]
            winning_trades = np.sum(trade_pnl > 0)
            win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
            avg_trade_profit = np.mean(trade_pnl) if len(trade_pnl) > 0 else 0.0
            best_trade = np.max(trade_pnl) if len(trade_pnl) > 0 else 0.0
            worst_trade = np.min(trade_pnl) if len(trade_pnl) > 0 else 0.0
            
            gross_profit = np.sum(trade_pnl[trade_pnl > 0])
            gross_loss = np.abs(np.sum(trade_pnl[trade_pnl < 0]))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        else:
            win_rate = 0.0
            avg_trade_profit = 0.0
            best_trade = 0.0
            worst_trade = 0.0
            profit_factor = 0.0

        # Get equity curve
        equity_curve = pd.Series(
            portfolio.value(),
            index=price_data.index,
            name="equity",
        )

        result = BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_cash=self.initial_cash,
            final_value=float(final_value),
            total_return=float(total_return),
            annual_return=float(annual_return),
            sharpe_ratio=float(sharpe_ratio),
            max_drawdown=float(max_drawdown),
            win_rate=float(win_rate),
            total_trades=int(total_trades),
            avg_trade_profit=float(avg_trade_profit),
            best_trade=float(best_trade),
            worst_trade=float(worst_trade),
            profit_factor=float(profit_factor),
            equity_curve=equity_curve,
        )

        logger.info(f"Backtest completed: {result}")
        return result
