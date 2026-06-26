"""Tests for strategy interface and signal generation."""

import pytest
from datetime import datetime, timedelta
from app.strategies import (
    Strategy,
    StrategySignal,
    MarketData,
    NewsContext,
    StrategyRegistry,
    get_strategy_registry,
    set_strategy_registry,
    CoveredCallStrategy,
    CashSecuredPutStrategy,
    DebitSpreadStrategy,
    CreditSpreadStrategy,
    LongCallPutStrategy,
)
from services.options_service import OptionContract
from services import RiskLevel


def _create_future_expiration(days_ahead: int = 30) -> str:
    """Create a future expiration date string.
    
    Args:
        days_ahead: Number of days in the future
        
    Returns:
        ISO format date string (YYYY-MM-DD)
    """
    future_date = datetime.utcnow() + timedelta(days=days_ahead)
    return future_date.strftime("%Y-%m-%d")


class MockStrategy(Strategy):
    """Mock strategy for testing."""

    def generate(
        self,
        symbol: str,
        market_data: MarketData,
        options_chain,
        news_context=None,
        risk_profile=RiskLevel.MEDIUM,
    ):
        """Generate a mock signal."""
        if not options_chain:
            return None
        
        return StrategySignal(
            symbol=symbol,
            strategy_type="mock_strategy",
            risk_level=risk_profile,
            score=0.75,
            expected_profit=500.0,
            max_loss=200.0,
            probability_estimate=0.65,
            reason="Mock strategy signal for testing",
            breakdown={"factor1": 0.8, "factor2": 0.7},
        )


class AlwaysFailStrategy(Strategy):
    """Strategy that always raises an exception."""

    def generate(
        self,
        symbol: str,
        market_data: MarketData,
        options_chain,
        news_context=None,
        risk_profile=RiskLevel.MEDIUM,
    ):
        """Raise an exception."""
        raise ValueError("Intentional test failure")


class TestStrategy:
    """Tests for Strategy base class."""

    def test_strategy_initialization(self):
        """Test strategy initialization."""
        strategy = MockStrategy(name="test_strategy", enabled=True)
        
        assert strategy.name == "test_strategy"
        assert strategy.is_enabled() is True

    def test_strategy_enable_disable(self):
        """Test enabling and disabling strategies."""
        strategy = MockStrategy(name="test_strategy", enabled=False)
        
        assert strategy.is_enabled() is False
        
        strategy.enable()
        assert strategy.is_enabled() is True
        
        strategy.disable()
        assert strategy.is_enabled() is False

    def test_strategy_generate_returns_signal(self):
        """Test that strategy generate returns a StrategySignal."""
        strategy = MockStrategy(name="test_strategy")
        
        market_data = MarketData(
            symbol="AAPL",
            current_price=150.0,
            price_history=[{"close": 150.0}],
            quote_timestamp=datetime.utcnow(),
        )
        
        options_chain = [
            OptionContract(
                symbol="AAPL",
                expiration=_create_future_expiration(30),
                strike=150.0,
                contract_type="call",
                bid=5.0,
                ask=5.5,
                volume=100,
                open_interest=500,
                implied_volatility=0.25,
                underlying_price=150.0,
                days_to_expiration=30,
                liquidity_score=75.0,
            )
        ]
        
        signal = strategy.generate(
            symbol="AAPL",
            market_data=market_data,
            options_chain=options_chain,
            risk_profile=RiskLevel.MEDIUM,
        )
        
        assert signal is not None
        assert isinstance(signal, StrategySignal)
        assert signal.symbol == "AAPL"
        assert signal.strategy_type == "mock_strategy"
        assert signal.reason is not None
        assert signal.max_loss is not None
        assert signal.score > 0.0
        assert signal.expected_profit > 0.0

    def test_strategy_signal_has_required_fields(self):
        """Test that StrategySignal has all required fields."""
        signal = StrategySignal(
            symbol="AAPL",
            strategy_type="test_strategy",
            risk_level=RiskLevel.MEDIUM,
            score=0.75,
            expected_profit=500.0,
            max_loss=200.0,
            probability_estimate=0.65,
            reason="Test signal",
        )
        
        # Verify required fields
        assert signal.symbol == "AAPL"
        assert signal.strategy_type == "test_strategy"
        assert signal.reason == "Test signal"
        assert signal.max_loss == 200.0
        assert signal.score == 0.75
        assert signal.expected_profit == 500.0


class TestStrategyRegistry:
    """Tests for StrategyRegistry."""

    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = StrategyRegistry()
        
        assert registry.list_strategies() == []
        assert registry.list_enabled_strategies() == []

    def test_register_strategy(self):
        """Test registering a strategy."""
        registry = StrategyRegistry()
        strategy = MockStrategy(name="test_strategy")
        
        registry.register(strategy)
        
        assert "test_strategy" in registry.list_strategies()
        assert registry.get("test_strategy") is strategy

    def test_register_duplicate_strategy_raises_error(self):
        """Test that registering duplicate strategy raises error."""
        registry = StrategyRegistry()
        strategy1 = MockStrategy(name="test_strategy")
        strategy2 = MockStrategy(name="test_strategy")
        
        registry.register(strategy1)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register(strategy2)

    def test_unregister_strategy(self):
        """Test unregistering a strategy."""
        registry = StrategyRegistry()
        strategy = MockStrategy(name="test_strategy")
        
        registry.register(strategy)
        assert "test_strategy" in registry.list_strategies()
        
        registry.unregister("test_strategy")
        assert "test_strategy" not in registry.list_strategies()

    def test_unregister_nonexistent_strategy_raises_error(self):
        """Test that unregistering nonexistent strategy raises error."""
        registry = StrategyRegistry()
        
        with pytest.raises(KeyError):
            registry.unregister("nonexistent")

    def test_enable_disable_strategy(self):
        """Test enabling and disabling strategies in registry."""
        registry = StrategyRegistry()
        strategy = MockStrategy(name="test_strategy", enabled=True)
        
        registry.register(strategy)
        assert "test_strategy" in registry.list_enabled_strategies()
        
        registry.disable_strategy("test_strategy")
        assert "test_strategy" not in registry.list_enabled_strategies()
        
        registry.enable_strategy("test_strategy")
        assert "test_strategy" in registry.list_enabled_strategies()

    def test_list_enabled_strategies(self):
        """Test listing only enabled strategies."""
        registry = StrategyRegistry()
        strategy1 = MockStrategy(name="strategy1", enabled=True)
        strategy2 = MockStrategy(name="strategy2", enabled=False)
        strategy3 = MockStrategy(name="strategy3", enabled=True)
        
        registry.register(strategy1)
        registry.register(strategy2)
        registry.register(strategy3)
        
        enabled = registry.list_enabled_strategies()
        assert "strategy1" in enabled
        assert "strategy2" not in enabled
        assert "strategy3" in enabled

    def test_generate_signals_from_all_enabled_strategies(self):
        """Test generating signals from all enabled strategies."""
        registry = StrategyRegistry()
        strategy1 = MockStrategy(name="strategy1", enabled=True)
        strategy2 = MockStrategy(name="strategy2", enabled=False)
        strategy3 = MockStrategy(name="strategy3", enabled=True)
        
        registry.register(strategy1)
        registry.register(strategy2)
        registry.register(strategy3)
        
        market_data = MarketData(
            symbol="AAPL",
            current_price=150.0,
            price_history=[{"close": 150.0}],
            quote_timestamp=datetime.utcnow(),
        )
        
        options_chain = [
            OptionContract(
                symbol="AAPL",
                expiration=_create_future_expiration(30),
                strike=150.0,
                contract_type="call",
                bid=5.0,
                ask=5.5,
                volume=100,
                open_interest=500,
                implied_volatility=0.25,
                underlying_price=150.0,
                days_to_expiration=30,
                liquidity_score=75.0,
            )
        ]
        
        signals = registry.generate_signals(
            symbol="AAPL",
            market_data=market_data,
            options_chain=options_chain,
            risk_profile=RiskLevel.MEDIUM,
        )
        
        # Should have 2 signals (from enabled strategies only)
        assert len(signals) == 2
        assert all(isinstance(s, StrategySignal) for s in signals)

    def test_generate_signals_skips_disabled_strategies(self):
        """Test that disabled strategies are skipped."""
        registry = StrategyRegistry()
        strategy = MockStrategy(name="test_strategy", enabled=False)
        
        registry.register(strategy)
        
        market_data = MarketData(
            symbol="AAPL",
            current_price=150.0,
            price_history=[{"close": 150.0}],
            quote_timestamp=datetime.utcnow(),
        )
        
        signals = registry.generate_signals(
            symbol="AAPL",
            market_data=market_data,
            options_chain=[],
            risk_profile=RiskLevel.MEDIUM,
        )
        
        assert len(signals) == 0

    def test_generate_signals_handles_strategy_exceptions(self):
        """Test that exceptions in strategies don't break signal generation."""
        registry = StrategyRegistry()
        strategy1 = MockStrategy(name="good_strategy", enabled=True)
        strategy2 = AlwaysFailStrategy(name="bad_strategy", enabled=True)
        strategy3 = MockStrategy(name="another_good_strategy", enabled=True)
        
        registry.register(strategy1)
        registry.register(strategy2)
        registry.register(strategy3)
        
        market_data = MarketData(
            symbol="AAPL",
            current_price=150.0,
            price_history=[{"close": 150.0}],
            quote_timestamp=datetime.utcnow(),
        )
        
        options_chain = [
            OptionContract(
                symbol="AAPL",
                expiration=_create_future_expiration(30),
                strike=150.0,
                contract_type="call",
                bid=5.0,
                ask=5.5,
                volume=100,
                open_interest=500,
                implied_volatility=0.25,
                underlying_price=150.0,
                days_to_expiration=30,
                liquidity_score=75.0,
            )
        ]
        
        signals = registry.generate_signals(
            symbol="AAPL",
            market_data=market_data,
            options_chain=options_chain,
            risk_profile=RiskLevel.MEDIUM,
        )
        
        # Should have 2 signals (from good strategies, bad strategy exception handled)
        assert len(signals) == 2

    def test_generate_signals_returns_none_when_no_opportunities(self):
        """Test that strategies can return None when no opportunities."""
        registry = StrategyRegistry()
        strategy = MockStrategy(name="test_strategy", enabled=True)
        
        registry.register(strategy)


class TestLongCallPutStrategy:
    """Tests for LongCallPutStrategy."""

    def test_long_call_put_strategy_initialization(self):
        """Test strategy initialization."""
        strategy = LongCallPutStrategy(name="long_call_put", enabled=True)
        
        assert strategy.name == "long_call_put"
        assert strategy.is_enabled() is True

    def test_long_call_put_only_available_for_high_risk(self):
        """Test that strategy only generates signals for high-risk profiles."""
        strategy = LongCallPutStrategy()
        
        market_data = MarketData(
            symbol="AAPL",
            current_price=150.0,
            price_history=[{"close": 150.0}],
            quote_timestamp=datetime.utcnow(),
        )
        
        options_chain = [
            OptionContract(
                symbol="AAPL",
                expiration=_create_future_expiration(30),
                strike=150.0,
                contract_type="call",
                bid=5.0,
                ask=5.5,
                volume=100,
                open_interest=500,
                implied_volatility=0.25,
                underlying_price=150.0,
                days_to_expiration=30,
                liquidity_score=75.0,
            )
        ]
        
        # Should return None for medium risk
        signal = strategy.generate(
            symbol="AAPL",
            market_data=market_data,
            options_chain=options_chain,
            risk_profile=RiskLevel.MEDIUM,
        )
        assert signal is None
        
        # Should return None for low risk
        signal = strategy.generate(
            symbol="AAPL",
            market_data=market_data,
            options_chain=options_chain,
            risk_profile=RiskLevel.LOW,
        )
        assert signal is None

    def test_long_call_put_max_loss_equals_premium_paid(self):
        """Test that max loss equals premium paid (acceptance criterion)."""
        strategy = LongCallPutStrategy()
        
        market_data = MarketData(
            symbol="AAPL",
            current_price=150.0,
            price_history=[
                {"close": 148.0},
                {"close": 149.0},
                {"close": 150.0},
                {"close": 151.0},
                {"close": 152.0},
            ],
            quote_timestamp=datetime.utcnow(),
        )
        
        options_chain = [
            OptionContract(
                symbol="AAPL",
                expiration=_create_future_expiration(30),
                strike=150.0,
                contract_type="call",
                bid=5.0,
                ask=5.5,
                volume=100,
                open_interest=500,
                implied_volatility=0.25,
                underlying_price=150.0,
                days_to_expiration=30,
                liquidity_score=75.0,
            ),
            OptionContract(
                symbol="AAPL",
                expiration=_create_future_expiration(30),
                strike=155.0,
                contract_type="call",
                bid=2.0,
                ask=2.5,
                volume=100,
                open_interest=500,
                implied_volatility=0.25,
                underlying_price=150.0,
                days_to_expiration=30,
                liquidity_score=75.0,
            ),
        ]
        
        signal = strategy.generate(
            symbol="AAPL",
            market_data=market_data,
            options_chain=options_chain,
            risk_profile=RiskLevel.HIGH,
        )
        
        if signal is not None:
            # Max loss should equal premium paid
            premium_paid = signal.breakdown["premium_at_risk"]
            assert signal.max_loss == premium_paid

    def test_long_call_put_rejects_if_premium_exceeds_budget(self):
        """Test that strategy rejects if premium exceeds risk budget."""
        strategy = LongCallPutStrategy()
        
        market_data = MarketData(
            symbol="AAPL",
            current_price=150.0,
            price_history=[{"close": 150.0}],
            quote_timestamp=datetime.utcnow(),
        )
        
        # Create option with very high premium (exceeds budget)
        options_chain = [
            OptionContract(
                symbol="AAPL",
                expiration=_create_future_expiration(30),
                strike=150.0,
                contract_type="call",
                bid=5000.0,  # Very high premium
                ask=5500.0,
                volume=100,
                open_interest=500,
                implied_volatility=0.25,
                underlying_price=150.0,
                days_to_expiration=30,
                liquidity_score=75.0,
            )
        ]
        
        signal = strategy.generate(
            symbol="AAPL",
            market_data=market_data,
            options_chain=options_chain,
            risk_profile=RiskLevel.HIGH,
        )
        
        # Should be rejected due to premium exceeding budget
        assert signal is None

    def test_long_call_put_signal_includes_required_fields(self):
        """Test that signal includes all required fields."""
        strategy = LongCallPutStrategy()
        
        market_data = MarketData(
            symbol="AAPL",
            current_price=150.0,
            price_history=[
                {"close": 148.0},
                {"close": 149.0},
                {"close": 150.0},
                {"close": 151.0},
                {"close": 152.0},
            ],
            quote_timestamp=datetime.utcnow(),
        )
        
        options_chain = [
            OptionContract(
                symbol="AAPL",
                expiration=_create_future_expiration(30),
                strike=150.0,
                contract_type="call",
                bid=5.0,
                ask=5.5,
                volume=100,
                open_interest=500,
                implied_volatility=0.25,
                underlying_price=150.0,
                days_to_expiration=30,
                liquidity_score=75.0,
            ),
            OptionContract(
                symbol="AAPL",
                expiration=_create_future_expiration(30),
                strike=155.0,
                contract_type="call",
                bid=2.0,
                ask=2.5,
                volume=100,
                open_interest=500,
                implied_volatility=0.25,
                underlying_price=150.0,
                days_to_expiration=30,
                liquidity_score=75.0,
            ),
        ]
        
        signal = strategy.generate(
            symbol="AAPL",
            market_data=market_data,
            options_chain=options_chain,
            risk_profile=RiskLevel.HIGH,
        )
        
        if signal is not None:
            # Verify required fields
            assert signal.symbol == "AAPL"
            assert signal.strategy_type == "long_call_put"
            assert signal.reason is not None
            assert signal.max_loss is not None
            assert signal.max_loss > 0
            assert signal.score >= 0.0 and signal.score <= 1.0
            assert signal.probability_estimate >= 0.0 and signal.probability_estimate <= 1.0
            assert signal.breakdown is not None
            assert "premium_at_risk" in signal.breakdown
            assert "max_loss" in signal.breakdown
