"""Backtesting engine for strategy evaluation.

Provides:
- BacktestEngine: Main backtesting orchestrator
- BacktestResult: Metrics and performance data
- SimulatedTrade: Individual trade record
- PaperTradingComparison: Comparison between backtest and live trading
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Callable, List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np

# Lazy import for vectorbt to avoid initialization errors during test collection
vectorbt = None

def _ensure_vectorbt():
    """Lazy load vectorbt only when needed."""
    global vectorbt
    if vectorbt is None:
        try:
            import vectorbt as vbt
            vectorbt = vbt
        except (ImportError, SystemError) as e:
            raise ImportError(
                "vectorbt is required for backtesting. "
                "Install it with: pip install vectorbt. "
                f"Error: {e}"
            )
    return vectorbt


@dataclass
class SimulatedTrade:
    """Record of a simulated trade."""
    entry_date: datetime
    entry_price: float
    exit_date: datetime
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float = 0.0
    reason: str = ""
    signal_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    strategy_name: str
    symbol: str
    initial_cash: float
    final_value: float
    start_date: datetime
    end_date: datetime
    total_trades: int
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    avg_holding_period: float = 0.0
    expected_fill_rate: float = 1.0
    trades: List[SimulatedTrade] = field(default_factory=list)

    @property
    def total_return(self) -> float:
        """Calculate total return percentage."""
        if self.initial_cash <= 0:
            return 0.0
        return ((self.final_value - self.initial_cash) / self.initial_cash) * 100

    @property
    def expected_value(self) -> float:
        """Calculate expected value per trade."""
        if self.total_trades == 0:
            return 0.0
        total_pnl = sum(t.pnl for t in self.trades)
        return total_pnl / self.total_trades

    def is_losing_strategy(self) -> bool:
        """Check if strategy is losing."""
        return self.final_value < self.initial_cash

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["total_return"] = self.total_return
        result["expected_value"] = self.expected_value
        result["is_losing_strategy"] = self.is_losing_strategy()
        result["trades"] = [t.to_dict() for t in self.trades]
        return result

    def __str__(self) -> str:
        """String representation."""
        losing_marker = "LOSING STRATEGY" if self.is_losing_strategy() else ""
        return (
            f"BacktestResult({self.strategy_name}, {self.symbol}) "
            f"Return: {self.total_return:.2f}% "
            f"Trades: {self.total_trades} "
            f"Win Rate: {self.win_rate:.2%} "
            f"{losing_marker}"
        )


@dataclass
class PaperTradingComparison:
    """Comparison between backtest and paper trading results."""
    backtest_result: BacktestResult
    paper_trades: List[Dict[str, Any]]
    backtest_return: float = 0.0
    paper_return: float = 0.0
    return_difference: float = 0.0
    execution_quality: float = 0.0
    slippage_estimate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "backtest_result": self.backtest_result.to_dict(),
            "paper_trades": self.paper_trades,
            "backtest_return": self.backtest_return,
            "paper_return": self.paper_return,
            "return_difference": self.return_difference,
            "execution_quality": self.execution_quality,
            "slippage_estimate": self.slippage_estimate,
        }


class BacktestEngine:
    """Engine for backtesting trading strategies."""

    def __init__(self, initial_cash: float = 100000.0):
        """Initialize backtest engine.
        
        Args:
            initial_cash: Starting capital for backtest
        """
        self.initial_cash = initial_cash

    def backtest(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        signals: pd.Series,
        strategy_name: str = "strategy",
    ) -> BacktestResult:
        """Run backtest on price data with signals.
        
        Args:
            symbol: Stock symbol
            price_data: DataFrame with OHLCV data
            signals: Series with trade signals (1=buy, -1=sell, 0=hold)
            strategy_name: Name of strategy
            
        Returns:
            BacktestResult with performance metrics
            
        Raises:
            ValueError: If data is invalid
        """
        if price_data.empty:
            raise ValueError("price_data cannot be empty")
        
        if len(price_data) != len(signals):
            raise ValueError("price_data and signals must have same length")
        
        # Initialize tracking variables
        cash = self.initial_cash
        position = 0
        trades: List[SimulatedTrade] = []
        entry_price = 0.0
        entry_date = None
        
        close_prices = price_data["close"].values
        dates = price_data.index
        
        # Process signals
        for i, signal in enumerate(signals):
            current_price = close_prices[i]
            current_date = dates[i]
            
            if signal == 1 and position == 0:  # Buy signal
                position = 1
                entry_price = current_price
                entry_date = current_date
            
            elif signal == -1 and position == 1:  # Sell signal
                exit_price = current_price
                pnl = (exit_price - entry_price)
                pnl_pct = (pnl / entry_price) if entry_price > 0 else 0.0
                
                trade = SimulatedTrade(
                    entry_date=entry_date,
                    entry_price=entry_price,
                    exit_date=current_date,
                    exit_price=exit_price,
                    quantity=1.0,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                )
                trades.append(trade)
                position = 0
        
        # Close any open position at end
        if position == 1:
            exit_price = close_prices[-1]
            pnl = (exit_price - entry_price)
            pnl_pct = (pnl / entry_price) if entry_price > 0 else 0.0
            
            trade = SimulatedTrade(
                entry_date=entry_date,
                entry_price=entry_price,
                exit_date=dates[-1],
                exit_price=exit_price,
                quantity=1.0,
                pnl=pnl,
                pnl_pct=pnl_pct,
            )
            trades.append(trade)
        
        # Calculate metrics
        winning_trades = sum(1 for t in trades if t.pnl > 0)
        losing_trades = sum(1 for t in trades if t.pnl < 0)
        total_trades = len(trades)
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        total_pnl = sum(t.pnl for t in trades)
        final_value = self.initial_cash + total_pnl
        
        avg_win = sum(t.pnl for t in trades if t.pnl > 0) / winning_trades if winning_trades > 0 else 0.0
        avg_loss = sum(t.pnl for t in trades if t.pnl < 0) / losing_trades if losing_trades > 0 else 0.0
        
        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        avg_holding_period = 0.0
        if trades:
            holding_periods = [(t.exit_date - t.entry_date).days for t in trades]
            avg_holding_period = sum(holding_periods) / len(holding_periods)
        
        return BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            initial_cash=self.initial_cash,
            final_value=final_value,
            start_date=dates[0],
            end_date=dates[-1],
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            avg_holding_period=avg_holding_period,
            expected_fill_rate=1.0,
            trades=trades,
        )

    def replay_signals_day_by_day(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        signal_generator_fn: Callable[[str, pd.DataFrame], int],
        strategy_name: str = "strategy",
    ) -> Tuple[BacktestResult, List[SimulatedTrade]]:
        """Replay signals day-by-day to avoid look-ahead bias.
        
        Args:
            symbol: Stock symbol
            price_data: DataFrame with OHLCV data
            signal_generator_fn: Function that generates signals from historical data
            strategy_name: Name of strategy
            
        Returns:
            Tuple of (BacktestResult, list of SimulatedTrade)
        """
        if price_data.empty:
            raise ValueError("price_data cannot be empty")
        
        cash = self.initial_cash
        position = 0
        trades: List[SimulatedTrade] = []
        entry_price = 0.0
        entry_date = None
        
        close_prices = price_data["close"].values
        dates = price_data.index
        
        # Replay day by day
        for i in range(len(price_data)):
            # Only provide data up to current day (no look-ahead)
            historical_data = price_data.iloc[:i+1]
            
            # Generate signal based only on historical data
            signal = signal_generator_fn(symbol, historical_data)
            
            current_price = close_prices[i]
            current_date = dates[i]
            
            if signal == 1 and position == 0:  # Buy signal
                position = 1
                entry_price = current_price
                entry_date = current_date
            
            elif signal == -1 and position == 1:  # Sell signal
                exit_price = current_price
                pnl = (exit_price - entry_price)
                pnl_pct = (pnl / entry_price) if entry_price > 0 else 0.0
                
                trade = SimulatedTrade(
                    entry_date=entry_date,
                    entry_price=entry_price,
                    exit_date=current_date,
                    exit_price=exit_price,
                    quantity=1.0,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                )
                trades.append(trade)
                position = 0
        
        # Close any open position at end
        if position == 1:
            exit_price = close_prices[-1]
            pnl = (exit_price - entry_price)
            pnl_pct = (pnl / entry_price) if entry_price > 0 else 0.0
            
            trade = SimulatedTrade(
                entry_date=entry_date,
                entry_price=entry_price,
                exit_date=dates[-1],
                exit_price=exit_price,
                quantity=1.0,
                pnl=pnl,
                pnl_pct=pnl_pct,
            )
            trades.append(trade)
        
        # Calculate metrics
        winning_trades = sum(1 for t in trades if t.pnl > 0)
        losing_trades = sum(1 for t in trades if t.pnl < 0)
        total_trades = len(trades)
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        total_pnl = sum(t.pnl for t in trades)
        final_value = self.initial_cash + total_pnl
        
        avg_win = sum(t.pnl for t in trades if t.pnl > 0) / winning_trades if winning_trades > 0 else 0.0
        avg_loss = sum(t.pnl for t in trades if t.pnl < 0) / losing_trades if losing_trades > 0 else 0.0
        
        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        avg_holding_period = 0.0
        if trades:
            holding_periods = [(t.exit_date - t.entry_date).days for t in trades]
            avg_holding_period = sum(holding_periods) / len(holding_periods)
        
        result = BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            initial_cash=self.initial_cash,
            final_value=final_value,
            start_date=dates[0],
            end_date=dates[-1],
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            avg_holding_period=avg_holding_period,
            expected_fill_rate=1.0,
            trades=trades,
        )
        
        return result, trades

    def compare_paper_trading(
        self,
        backtest_result: BacktestResult,
        paper_trades: List[Dict[str, Any]],
    ) -> PaperTradingComparison:
        """Compare backtest results with paper trading results.
        
        Args:
            backtest_result: BacktestResult from backtest
            paper_trades: List of paper trading trade records
            
        Returns:
            PaperTradingComparison with comparison metrics
        """
        backtest_return = backtest_result.total_return
        
        # Calculate paper trading return
        paper_pnl = sum(t.get("pnl", 0) for t in paper_trades)
        paper_return = (paper_pnl / self.initial_cash * 100) if self.initial_cash > 0 else 0.0
        
        return_difference = paper_return - backtest_return
        
        # Estimate execution quality and slippage
        execution_quality = 1.0 - (abs(return_difference) / max(abs(backtest_return), 0.01))
        execution_quality = max(0.0, min(1.0, execution_quality))
        
        slippage_estimate = return_difference
        
        return PaperTradingComparison(
            backtest_result=backtest_result,
            paper_trades=paper_trades,
            backtest_return=backtest_return,
            paper_return=paper_return,
            return_difference=return_difference,
            execution_quality=execution_quality,
            slippage_estimate=slippage_estimate,
        )
