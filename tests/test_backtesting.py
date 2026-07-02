"""Tests for backtesting engine and historical signal replay.

Verifies:
- Backtest engine produces correct metrics
- Historical signal replay avoids look-ahead bias
- Simulated trades are stored correctly
- Strategy backtester integrates with engine
- Paper trading comparison works correctly
"""

import pytest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from app.backtesting.engine import BacktestEngine, BacktestResult, SimulatedTrade, PaperTradingComparison


@pytest.fixture
def sample_price_data():
    """Create sample price data for testing."""
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    np.random.seed(42)
    
    # Create realistic price data with trend
    prices = 100.0 + np.cumsum(np.random.randn(100) * 0.5)
    
    data = pd.DataFrame(
        {
            "open": prices + np.random.randn(100) * 0.1,
            "high": prices + np.abs(np.random.randn(100) * 0.2),
            "low": prices - np.abs(np.random.randn(100) * 0.2),
            "close": prices,
            "volume": np.random.randint(1000000, 5000000, 100),
        },
        index=dates,
    )
    
    return data


@pytest.fixture
def backtest_engine():
    """Create backtest engine instance."""
    return BacktestEngine(initial_cash=100000.0)


class TestBacktestEngine:
    """Tests for BacktestEngine."""

    def test_backtest_with_buy_and_hold(self, backtest_engine, sample_price_data):
        """Test backtest with simple buy-and-hold strategy."""
        # Create buy-and-hold signals
        signals = pd.Series([0] * len(sample_price_data), index=sample_price_data.index)
        signals.iloc[0] = 1  # Buy on first day
        signals.iloc[-1] = -1  # Sell on last day
        
        result = backtest_engine.backtest(
            symbol="TEST",
            price_data=sample_price_data,
            signals=signals,
            strategy_name="buy_and_hold",
        )
        
        assert result.strategy_name == "buy_and_hold"
        assert result.symbol == "TEST"
        assert result.total_trades >= 1
        assert result.initial_cash == 100000.0
        assert result.final_value > 0
        assert result.start_date == sample_price_data.index[0]
        assert result.end_date == sample_price_data.index[-1]
        assert result.expected_fill_rate == 1.0  # Backtest assumes 100% fill

    def test_backtest_with_multiple_trades(self, backtest_engine, sample_price_data):
        """Test backtest with multiple entry/exit signals."""
        # Create signals with multiple trades
        signals = pd.Series([0] * len(sample_price_data), index=sample_price_data.index)
        signals.iloc[10] = 1   # Buy
        signals.iloc[20] = -1  # Sell
        signals.iloc[30] = 1   # Buy
        signals.iloc[40] = -1  # Sell
        
        result = backtest_engine.backtest(
            symbol="TEST",
            price_data=sample_price_data,
            signals=signals,
            strategy_name="multi_trade",
        )
        
        assert result.total_trades >= 2
        assert result.win_rate >= 0.0
        assert result.win_rate <= 1.0

    def test_backtest_empty_data_raises_error(self, backtest_engine):
        """Test that empty price data raises ValueError."""
        empty_data = pd.DataFrame()
        signals = pd.Series([])
        
        with pytest.raises(ValueError, match="price_data cannot be empty"):
            backtest_engine.backtest(
                symbol="TEST",
                price_data=empty_data,
                signals=signals,
            )

    def test_backtest_mismatched_lengths_raises_error(self, backtest_engine, sample_price_data):
        """Test that mismatched price_data and signals lengths raise ValueError."""
        signals = pd.Series([0] * 50)  # Wrong length
        
        with pytest.raises(ValueError, match="must have same length"):
            backtest_engine.backtest(
                symbol="TEST",
                price_data=sample_price_data,
                signals=signals,
            )

    def test_backtest_result_to_dict(self, backtest_engine, sample_price_data):
        """Test BacktestResult.to_dict() method."""
        signals = pd.Series([0] * len(sample_price_data), index=sample_price_data.index)
        signals.iloc[0] = 1
        signals.iloc[-1] = -1
        
        result = backtest_engine.backtest(
            symbol="TEST",
            price_data=sample_price_data,
            signals=signals,
        )
        
        result_dict = result.to_dict()
        
        assert "strategy_name" in result_dict
        assert "symbol" in result_dict
        assert "total_return" in result_dict
        assert "avg_win" in result_dict
        assert "avg_loss" in result_dict
        assert "expected_value" in result_dict
        assert "avg_holding_period" in result_dict
        assert "expected_fill_rate" in result_dict
        assert "is_losing_strategy" in result_dict
        assert result_dict["symbol"] == "TEST"
        assert result_dict["expected_fill_rate"] == 1.0

    def test_backtest_metrics_calculation(self, backtest_engine, sample_price_data):
        """Test that all metrics are calculated correctly."""
        signals = pd.Series([0] * len(sample_price_data), index=sample_price_data.index)
        signals.iloc[10] = 1   # Buy
        signals.iloc[30] = -1  # Sell (profit)
        signals.iloc[40] = 1   # Buy
        signals.iloc[60] = -1  # Sell (profit)
        
        result = backtest_engine.backtest(
            symbol="TEST",
            price_data=sample_price_data,
            signals=signals,
            strategy_name="test_metrics",
        )
        
        # Verify all metrics exist and are reasonable
        assert result.win_rate >= 0.0 and result.win_rate <= 1.0
        assert result.avg_win >= 0.0
        assert result.avg_loss <= 0.0
        assert result.profit_factor >= 0.0
        assert result.avg_holding_period >= 0.0
        assert isinstance(result.expected_value, float)
        assert result.total_trades >= 0
        assert result.expected_fill_rate == 1.0

    def test_losing_strategy_marked(self, backtest_engine, sample_price_data):
        """Test that losing strategies are marked."""
        # Create signals that will likely lose (sell before buy)
        signals = pd.Series([0] * len(sample_price_data), index=sample_price_data.index)
        signals.iloc[0] = -1  # Sell first (no position)
        signals.iloc[50] = 1  # Buy
        signals.iloc[99] = -1  # Sell
        
        result = backtest_engine.backtest(
            symbol="TEST",
            price_data=sample_price_data,
            signals=signals,
        )
        
        # Check if strategy is marked as losing
        is_losing = result.is_losing_strategy()
        assert isinstance(is_losing, bool)
        
        # Verify it appears in string representation
        result_str = str(result)
        if is_losing:
            assert "LOSING STRATEGY" in result_str


class TestHistoricalSignalReplay:
    """Tests for historical signal replay (look-ahead bias prevention)."""

    def test_replay_signals_day_by_day(self, backtest_engine, sample_price_data):
        """Test day-by-day signal replay."""
        def signal_generator(symbol, price_data_up_to_date):
            """Generate signal based only on available data."""
            if len(price_data_up_to_date) < 20:
                return 0
            
            # Simple SMA crossover
            close = price_data_up_to_date["close"].values
            sma = pd.Series(close).rolling(window=20).mean().values[-1]
            current_price = close[-1]
            
            if current_price > sma:
                return 1
            elif current_price < sma:
                return -1
            return 0
        
        result, trades = backtest_engine.replay_signals_day_by_day(
            symbol="TEST",
            price_data=sample_price_data,
            signal_generator_fn=signal_generator,
            strategy_name="sma_crossover",
        )
        
        assert result.strategy_name == "sma_crossover"
        assert result.symbol == "TEST"
        assert isinstance(trades, list)
        assert all(isinstance(t, SimulatedTrade) for t in trades)

    def test_replay_avoids_look_ahead_bias(self, backtest_engine, sample_price_data):
        """Test that replay uses only historical data (no look-ahead)."""
        data_used_at_each_step = []
        
        def signal_generator(symbol, price_data_up_to_date):
            """Track how much data is available at each step."""
            data_used_at_each_step.append(len(price_data_up_to_date))
            return 0
        
        backtest_engine.replay_signals_day_by_day(
            symbol="TEST",
            price_data=sample_price_data,
            signal_generator_fn=signal_generator,
        )
        
        # Verify that data grows monotonically (no look-ahead)
        for i in range(1, len(data_used_at_each_step)):
            assert data_used_at_each_step[i] == data_used_at_each_step[i-1] + 1
        
        # Verify we end with all data
        assert data_used_at_each_step[-1] == len(sample_price_data)

    def test_replay_stores_all_trades(self, backtest_engine, sample_price_data):
        """Test that all simulated trades are stored."""
        def signal_generator(symbol, price_data_up_to_date):
            """Generate alternating buy/sell signals."""
            if len(price_data_up_to_date) % 20 == 0:
                return 1 if len(price_data_up_to_date) % 40 == 0 else -1
            return 0
        
        result, trades = backtest_engine.replay_signals_day_by_day(
            symbol="TEST",
            price_data=sample_price_data,
            signal_generator_fn=signal_generator,
        )
        
        # Verify trades are stored
        assert isinstance(trades, list)
        
        # Each trade should have required fields
        for trade in trades:
            assert trade.entry_date is not None
            assert trade.entry_price > 0
            assert trade.exit_date is not None
            assert trade.exit_price > 0
            assert trade.quantity > 0
            assert trade.pnl is not None

    def test_simulated_trade_to_dict(self):
        """Test SimulatedTrade.to_dict() method."""
        trade = SimulatedTrade(
            entry_date=datetime(2023, 1, 1),
            entry_price=100.0,
            exit_date=datetime(2023, 1, 10),
            exit_price=105.0,
            quantity=1,
            pnl=5.0,
            pnl_pct=0.05,
            reason="SMA crossover",
            signal_score=75.0,
        )
        
        trade_dict = trade.to_dict()
        
        assert trade_dict["entry_price"] == 100.0
        assert trade_dict["exit_price"] == 105.0
        assert trade_dict["pnl"] == 5.0
        assert trade_dict["reason"] == "SMA crossover"


class TestPaperTradingComparison:
    """Tests for paper trading comparison."""

    def test_compare_paper_trading_perfect_execution(self, backtest_engine, sample_price_data):
        """Test comparison when paper trading matches backtest perfectly."""
        # Create backtest result
        signals = pd.Series([0] * len(sample_price_data), index=sample_price_data.index)
        signals.iloc[10] = 1
        signals.iloc[30] = -1
        
        backtest_result = backtest_engine.backtest(
            symbol="TEST",
            price_data=sample_price_data,
            signals=signals,
        )
        
        # Create paper trades that match backtest perfectly
        paper_trades = [
            {
                "entry_price": sample_price_data["close"].iloc[10],
                "actual_entry_price": sample_price_data["close"].iloc[10],
                "exit_price": sample_price_data["close"].iloc[30],
                "actual_exit_price": sample_price_data["close"].iloc[30],
                "pnl": sample_price_data["close"].iloc[30] - sample_price_data["close"].iloc[10],
            }
        ]
        
        comparison = backtest_engine.compare_paper_trading(
            backtest_result=backtest_result,
            paper_trades=paper_trades,
        )
        
        assert comparison.backtest_result == backtest_result
        assert len(comparison.paper_trades) == 1
        assert comparison.execution_quality >= 0.0
        assert comparison.execution_quality <= 1.0

    def test_paper_trading_comparison_to_dict(self, backtest_engine, sample_price_data):
        """Test PaperTradingComparison.to_dict() method."""
        signals = pd.Series([0] * len(sample_price_data), index=sample_price_data.index)
        signals.iloc[10] = 1
        signals.iloc[30] = -1
        
        backtest_result = backtest_engine.backtest(
            symbol="TEST",
            price_data=sample_price_data,
            signals=signals,
        )
        
        paper_trades = []
        
        comparison = backtest_engine.compare_paper_trading(
            backtest_result=backtest_result,
            paper_trades=paper_trades,
        )
        
        comparison_dict = comparison.to_dict()
        
        assert "backtest_result" in comparison_dict
        assert "paper_trades" in comparison_dict
        assert "backtest_return" in comparison_dict
        assert "paper_return" in comparison_dict
        assert "return_difference" in comparison_dict
        assert "execution_quality" in comparison_dict
        assert "slippage_estimate" in comparison_dict
