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
        expected_fill_rate: Expected fill rate (0.0-1.0) for comparison with paper trading
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
    expected_fill_rate: float = 1.0  # Assume 100% fill rate in backtest
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
            "expected_fill_rate": self.expected_fill_rate,
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
            f"  Avg Holding Period: {self.avg_holding_period:.1f} days | Expected Fill Rate: {self.expected_fill_rate:.1%}"
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


@dataclass
class PaperTradingComparison:
    """Comparison between backtest assumptions and paper trading results.
    
    Attributes:
        strategy_name: Name of the strategy
        symbol: Stock symbol
        backtest_result: BacktestResult from historical backtest
        paper_start_date: Start date of paper trading period
        paper_end_date: End date of paper trading period
        paper_total_trades: Number of trades executed in paper trading
        paper_filled_trades: Number of trades that filled in paper trading
        paper_missed_fills: Number of trades that did not fill
        paper_fill_rate: Actual fill rate in paper trading (0.0-1.0)
        paper_avg_fill_price: Average fill price in paper trading
        paper_expected_fill_price: Expected fill price from backtest
        paper_slippage_per_trade: Average slippage per trade (actual - expected)
        paper_total_pnl: Total P&L from paper trading
        backtest_expected_pnl: Expected P&L from backtest
        pnl_difference: Difference between paper and backtest P&L
        pnl_difference_pct: P&L difference as percentage
        assumptions_too_optimistic: Whether backtest assumptions appear too optimistic
        recommendation: Recommendation for strategy ("enable", "disable", "monitor")
    """
    strategy_name: str
    symbol: str
    backtest_result: BacktestResult
    paper_start_date: datetime
    paper_end_date: datetime
    paper_total_trades: int
    paper_filled_trades: int
    paper_missed_fills: int
    paper_fill_rate: float
    paper_avg_fill_price: float
    paper_expected_fill_price: float
    paper_slippage_per_trade: float
    paper_total_pnl: float
    backtest_expected_pnl: float
    pnl_difference: float
    pnl_difference_pct: float
    assumptions_too_optimistic: bool
    recommendation: str  # "enable", "disable", "monitor"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "paper_start_date": self.paper_start_date.isoformat(),
            "paper_end_date": self.paper_end_date.isoformat(),
            "paper_total_trades": self.paper_total_trades,
            "paper_filled_trades": self.paper_filled_trades,
            "paper_missed_fills": self.paper_missed_fills,
            "paper_fill_rate": self.paper_fill_rate,
            "paper_avg_fill_price": self.paper_avg_fill_price,
            "paper_expected_fill_price": self.paper_expected_fill_price,
            "paper_slippage_per_trade": self.paper_slippage_per_trade,
            "paper_total_pnl": self.paper_total_pnl,
            "backtest_expected_pnl": self.backtest_expected_pnl,
            "pnl_difference": self.pnl_difference,
            "pnl_difference_pct": self.pnl_difference_pct,
            "assumptions_too_optimistic": self.assumptions_too_optimistic,
            "recommendation": self.recommendation,
        }

    def __str__(self) -> str:
        """String representation of comparison."""
        optimism_marker = " [ASSUMPTIONS TOO OPTIMISTIC]" if self.assumptions_too_optimistic else ""
        return (
            f"PaperTradingComparison({self.strategy_name} on {self.symbol}){optimism_marker}\n"
            f"  Period: {self.paper_start_date.date()} to {self.paper_end_date.date()}\n"
            f"  Fill Rate: {self.paper_fill_rate:.1%} ({self.paper_filled_trades}/{self.paper_total_trades} trades)\n"
            f"  Missed Fills: {self.paper_missed_fills}\n"
            f"  Avg Slippage: ${self.paper_slippage_per_trade:,.2f} per trade\n"
            f"  Paper P&L: ${self.paper_total_pnl:,.2f} vs Backtest Expected: ${self.backtest_expected_pnl:,.2f}\n"
            f"  P&L Difference: ${self.pnl_difference:,.2f} ({self.pnl_difference_pct:.2%})\n"
            f"  Recommendation: {self.recommendation.upper()}"
        )


class BacktestEngine:
    """Vectorized backtesting engine using VectorBT.
    
    Provides high-performance backtesting for trading strategies with support for:
    - Multiple strategy variations and parameter optimization
    - Detailed performance metrics and risk analysis
    - Trade-level analysis and equity curve tracking
    - Vectorized operations for speed
    - Historical signal replay with look-ahead bias prevention
    - Paper trading comparison and validation
    
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
            final_value=final_value,
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=total_trades,
            avg_trade_profit=avg_trade_profit,
            best_trade=best_trade,
            worst_trade=worst_trade,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            expected_value=expected_value,
            avg_holding_period=avg_holding_period,
            expected_fill_rate=1.0,  # Backtest assumes 100% fill rate
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
        in real-time, using only data available up to each day.
        
        Args:
            symbol: Stock symbol
            price_data: DataFrame with OHLCV data
            signal_generator_fn: Callable that takes (symbol, price_data_up_to_date) and returns signal
            strategy_name: Name of strategy
            
        Returns:
            Tuple of (BacktestResult, List[SimulatedTrade])
        """
        if price_data.empty:
            raise ValueError("price_data cannot be empty")
        
        trades: List[SimulatedTrade] = []
        signals = []
        current_position = None
        entry_price = None
        entry_date = None
        entry_signal_score = 0.0
        entry_reason = ""
        
        # Generate signals day by day
        for i in range(len(price_data)):
            # Get data available up to current day (no look-ahead)
            price_data_up_to_date = price_data.iloc[:i+1]
            
            # Generate signal using only available data
            signal = signal_generator_fn(symbol, price_data_up_to_date)
            signals.append(signal)
            
            current_price = price_data["close"].iloc[i]
            current_date = price_data.index[i]
            
            # Handle entry signal
            if signal == 1 and current_position is None:
                current_position = "long"
                entry_price = current_price
                entry_date = current_date
                entry_signal_score = 0.0  # Default score
                entry_reason = "signal_generated"
            
            # Handle exit signal
            elif signal == -1 and current_position == "long":
                if entry_price is not None and entry_date is not None:
                    pnl = (current_price - entry_price) * 1  # Assume 1 share
                    pnl_pct = (pnl / entry_price) if entry_price > 0 else 0.0
                    
                    trade = SimulatedTrade(
                        entry_date=entry_date,
                        entry_price=entry_price,
                        exit_date=current_date,
                        exit_price=current_price,
                        quantity=1,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        reason=entry_reason,
                        signal_score=entry_signal_score,
                    )
                    trades.append(trade)
                
                current_position = None
                entry_price = None
                entry_date = None
        
        # Convert signals to DataFrame and run backtest
        signals_df = pd.Series(signals, index=price_data.index)
        result = self.backtest(
            symbol=symbol,
            price_data=price_data,
            signals=signals_df,
            strategy_name=strategy_name,
        )
        
        return result, trades

    def compare_paper_trading(
        self,
        backtest_result: BacktestResult,
        paper_trades: List[Dict[str, Any]],
        fill_rate_threshold: float = 0.95,
        slippage_threshold: float = 0.01,
        pnl_variance_threshold: float = 0.10,
    ) -> PaperTradingComparison:
        """Compare backtest assumptions against paper trading results.
        
        Args:
            backtest_result: BacktestResult from historical backtest
            paper_trades: List of paper trading trades with fields:
                - entry_price: Expected entry price
                - actual_entry_price: Actual fill price
                - exit_price: Expected exit price
                - actual_exit_price: Actual exit fill price
                - filled: Whether trade filled
                - entry_date: Entry date
                - exit_date: Exit date
            fill_rate_threshold: Minimum acceptable fill rate (0.0-1.0)
            slippage_threshold: Maximum acceptable slippage as decimal
            pnl_variance_threshold: Maximum acceptable P&L variance as decimal
            
        Returns:
            PaperTradingComparison with analysis
        """
        if not paper_trades:
            logger.warning("No paper trades provided for comparison")
            paper_trades = []
        
        # Calculate paper trading metrics
        total_trades = len(paper_trades)
        filled_trades = sum(1 for t in paper_trades if t.get("filled", False))
        missed_fills = total_trades - filled_trades
        fill_rate = filled_trades / total_trades if total_trades > 0 else 0.0
        
        # Calculate slippage
        slippages = []
        for trade in paper_trades:
            if trade.get("filled", False):
                entry_slippage = trade.get("actual_entry_price", 0) - trade.get("entry_price", 0)
                exit_slippage = trade.get("actual_exit_price", 0) - trade.get("exit_price", 0)
                slippages.append(entry_slippage + exit_slippage)
        
        avg_slippage = np.mean(slippages) if slippages else 0.0
        
        # Calculate P&L
        paper_pnl = 0.0
        for trade in paper_trades:
            if trade.get("filled", False):
                entry = trade.get("actual_entry_price", 0)
                exit_p = trade.get("actual_exit_price", 0)
                qty = trade.get("quantity", 1)
                paper_pnl += (exit_p - entry) * qty
        
        backtest_pnl = backtest_result.final_value - backtest_result.initial_cash
        pnl_difference = paper_pnl - backtest_pnl
        pnl_difference_pct = (pnl_difference / backtest_pnl) if backtest_pnl != 0 else 0.0
        
        # Determine if assumptions are too optimistic
        assumptions_too_optimistic = (
            fill_rate < fill_rate_threshold or
            abs(avg_slippage) > slippage_threshold or
            pnl_difference_pct < -pnl_variance_threshold
        )
        
        # Generate recommendation
        if assumptions_too_optimistic:
            if fill_rate < fill_rate_threshold * 0.8 or pnl_difference_pct < -pnl_variance_threshold * 2:
                recommendation = "disable"
            else:
                recommendation = "monitor"
        else:
            recommendation = "enable"
        
        # Get average fill prices
        avg_entry_price = np.mean([t.get("entry_price", 0) for t in paper_trades]) if paper_trades else 0.0
        avg_actual_entry = np.mean([t.get("actual_entry_price", 0) for t in paper_trades if t.get("filled")]) if filled_trades > 0 else 0.0
        
        comparison = PaperTradingComparison(
            strategy_name=backtest_result.strategy_name,
            symbol=backtest_result.symbol,
            backtest_result=backtest_result,
            paper_start_date=min([t.get("entry_date") for t in paper_trades], default=datetime.utcnow()),
            paper_end_date=max([t.get("exit_date") for t in paper_trades], default=datetime.utcnow()),
            paper_total_trades=total_trades,
            paper_filled_trades=filled_trades,
            paper_missed_fills=missed_fills,
            paper_fill_rate=fill_rate,
            paper_avg_fill_price=avg_actual_entry,
            paper_expected_fill_price=avg_entry_price,
            paper_slippage_per_trade=avg_slippage,
            paper_total_pnl=paper_pnl,
            backtest_expected_pnl=backtest_pnl,
            pnl_difference=pnl_difference,
            pnl_difference_pct=pnl_difference_pct,
            assumptions_too_optimistic=assumptions_too_optimistic,
            recommendation=recommendation,
        )
        
        logger.info(f"Paper trading comparison: {comparison}")
        return comparison
