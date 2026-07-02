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
        avg_win: Average profit on winning trades
        avg_loss: Average loss on losing trades
        expected_value: Expected value per trade (avg_win * win_rate + avg_loss * (1 - win_rate))
        avg_holding_period: Average number of days holding per trade
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
    avg_win: float
    avg_loss: float
    expected_value: float
    avg_holding_period: float
    trades: Optional[pd.DataFrame] = None
    equity_curve: Optional[pd.Series] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_losing_strategy(self) -> bool:
        """Check if strategy is losing (negative total return).
        
        Returns:
            True if total_return is negative, False otherwise
        """
        return self.total_return < 0.0

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
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "expected_value": self.expected_value,
            "avg_holding_period": self.avg_holding_period,
            "is_losing_strategy": self.is_losing_strategy(),
        }

    def __str__(self) -> str:
        """String representation of backtest result."""
        losing_marker = " [LOSING STRATEGY]" if self.is_losing_strategy() else ""
        return (
            f"BacktestResult({self.strategy_name} on {self.symbol}){losing_marker}\n"
            f"  Period: {self.start_date.date()} to {self.end_date.date()}\n"
            f"  Initial: ${self.initial_cash:,.2f} -> Final: ${self.final_value:,.2f}\n"
            f"  Return: {self.total_return:.2%} (annualized: {self.annual_return:.2%})\n"
            f"  Sharpe: {self.sharpe_ratio:.2f} | Max DD: {self.max_drawdown:.2%}\n"
            f"  Trades: {self.total_trades} | Win Rate: {self.win_rate:.2%}\n"
            f"  Avg Trade: ${self.avg_trade_profit:,.2f} | Avg Win: ${self.avg_win:,.2f} | Avg Loss: ${self.avg_loss:,.2f}\n"
            f"  Profit Factor: {self.profit_factor:.2f} | Expected Value: ${self.expected_value:,.2f}\n"
            f"  Avg Holding Period: {self.avg_holding_period:.1f} days"
        )


@dataclass
class SimulatedTrade:
    """A single simulated trade from historical replay.
    
    Attributes:
        entry_date: Date when trade was entered
        entry_price: Price at entry
        exit_date: Date when trade was exited (None if still open)
        exit_price: Price at exit (None if still open)
        quantity: Number of shares/contracts
        pnl: Realized P&L (None if still open)
        pnl_pct: P&L as percentage (None if still open)
        reason: Reason for entry (from signal)
        signal_score: Score of the signal that triggered entry
    """
    entry_date: datetime
    entry_price: float
    exit_date: Optional[datetime]
    exit_price: Optional[float]
    quantity: int
    pnl: Optional[float]
    pnl_pct: Optional[float]
    reason: str
    signal_score: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entry_date": self.entry_date.isoformat(),
            "entry_price": self.entry_price,
            "exit_date": self.exit_date.isoformat() if self.exit_date else None,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "reason": self.reason,
            "signal_score": self.signal_score,
        }


class BacktestEngine:
    """Vectorized backtesting engine using VectorBT.
    
    Provides high-performance backtesting for trading strategies with support for:
    - Multiple strategy variations and parameter optimization
    - Detailed performance metrics and risk analysis
    - Trade-level analysis and equity curve tracking
    - Vectorized operations for speed
    - Historical signal replay with look-ahead bias prevention
    
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
            trade_returns = trades["return"]
            
            # Win rate and trade statistics
            winning_trades = np.sum(trade_pnl > 0)
            losing_trades = np.sum(trade_pnl < 0)
            win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
            
            # Average win and loss
            winning_pnl = trade_pnl[trade_pnl > 0]
            losing_pnl = trade_pnl[trade_pnl < 0]
            avg_win = np.mean(winning_pnl) if len(winning_pnl) > 0 else 0.0
            avg_loss = np.mean(losing_pnl) if len(losing_pnl) > 0 else 0.0
            
            # Average trade profit
            avg_trade_profit = np.mean(trade_pnl) if len(trade_pnl) > 0 else 0.0
            
            # Best and worst trades
            best_trade = np.max(trade_pnl) if len(trade_pnl) > 0 else 0.0
            worst_trade = np.min(trade_pnl) if len(trade_pnl) > 0 else 0.0
            
            # Profit factor
            gross_profit = np.sum(trade_pnl[trade_pnl > 0])
            gross_loss = np.abs(np.sum(trade_pnl[trade_pnl < 0]))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
            
            # Expected value per trade
            expected_value = (avg_win * win_rate) + (avg_loss * (1 - win_rate))
            
            # Average holding period (in days)
            entry_dates = trades["entry_idx"]
            exit_dates = trades["exit_idx"]
            holding_periods = exit_dates - entry_dates
            avg_holding_period = np.mean(holding_periods) if len(holding_periods) > 0 else 0.0
        else:
            win_rate = 0.0
            avg_win = 0.0
            avg_loss = 0.0
            avg_trade_profit = 0.0
            best_trade = 0.0
            worst_trade = 0.0
            profit_factor = 0.0
            expected_value = 0.0
            avg_holding_period = 0.0

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
            avg_win=float(avg_win),
            avg_loss=float(avg_loss),
            expected_value=float(expected_value),
            avg_holding_period=float(avg_holding_period),
            equity_curve=equity_curve,
        )

        logger.info(f"Backtest completed: {result}")
        return result

    def replay_signals_day_by_day(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        signal_generator_fn,
        strategy_name: str = "strategy",
    ) -> Tuple[BacktestResult, List[SimulatedTrade]]:
        """Replay historical signals day-by-day to avoid look-ahead bias.
        
        This method simulates signal generation as if the strategy were running
        in real-time, using only data available up to each day. This prevents
        look-ahead bias where future data would influence past decisions.
        
        Args:
            symbol: Stock symbol
            price_data: DataFrame with OHLCV data (index=date, columns=[open, high, low, close, volume])
            signal_generator_fn: Callable that takes (symbol, price_data_up_to_date) and returns signal (1, -1, or 0)
            strategy_name: Name of strategy being tested
            
        Returns:
            Tuple of (BacktestResult, List[SimulatedTrade])
            
        Raises:
            ValueError: If price_data is invalid
        """
        if price_data.empty:
            raise ValueError("price_data cannot be empty")
        
        # Initialize tracking
        signals = []
        simulated_trades: List[SimulatedTrade] = []
        current_position = None  # Track open position
        portfolio_value = self.initial_cash
        equity_values = []
        
        # Replay day by day
        for i in range(len(price_data)):
            # Get data up to current day (no look-ahead)
            current_date = price_data.index[i]
            price_data_up_to = price_data.iloc[:i+1]
            
            # Generate signal using only available data
            signal = signal_generator_fn(symbol, price_data_up_to)
            signals.append(signal)
            
            current_price = price_data["close"].iloc[i]
            
            # Handle entry signal
            if signal == 1 and current_position is None:
                current_position = {
                    "entry_date": current_date,
                    "entry_price": current_price,
                    "quantity": int(portfolio_value / current_price),
                }
            
            # Handle exit signal
            elif signal == -1 and current_position is not None:
                exit_date = current_date
                exit_price = current_price
                entry_price = current_position["entry_price"]
                quantity = current_position["quantity"]
                
                # Calculate P&L
                pnl = (exit_price - entry_price) * quantity
                pnl_pct = (exit_price - entry_price) / entry_price if entry_price > 0 else 0.0
                
                # Calculate holding period
                holding_days = (exit_date - current_position["entry_date"]).days
                
                # Create trade record
                trade = SimulatedTrade(
                    entry_date=current_position["entry_date"],
                    entry_price=entry_price,
                    exit_date=exit_date,
                    exit_price=exit_price,
                    quantity=quantity,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    reason="signal",
                    signal_score=0.0,
                )
                simulated_trades.append(trade)
                
                # Update portfolio value
                portfolio_value += pnl
                current_position = None
            
            equity_values.append(portfolio_value)
        
        # Close any open position at end
        if current_position is not None:
            exit_date = price_data.index[-1]
            exit_price = price_data["close"].iloc[-1]
            entry_price = current_position["entry_price"]
            quantity = current_position["quantity"]
            
            pnl = (exit_price - entry_price) * quantity
            pnl_pct = (exit_price - entry_price) / entry_price if entry_price > 0 else 0.0
            
            trade = SimulatedTrade(
                entry_date=current_position["entry_date"],
                entry_price=entry_price,
                exit_date=exit_date,
                exit_price=exit_price,
                quantity=quantity,
                pnl=pnl,
                pnl_pct=pnl_pct,
                reason="end_of_period",
                signal_score=0.0,
            )
            simulated_trades.append(trade)
            portfolio_value += pnl
        
        # Convert signals to DataFrame
        signals_df = pd.Series(signals, index=price_data.index)
        
        # Run backtest with generated signals
        result = self.backtest(
            symbol=symbol,
            price_data=price_data,
            signals=signals_df,
            strategy_name=strategy_name,
        )
        
        return result, simulated_trades
