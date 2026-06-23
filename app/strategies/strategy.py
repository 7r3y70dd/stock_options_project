"""Strategy interface and base classes for trading strategy implementations.

Each strategy plugs into the same engine and generates Signal candidates.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.data_sources import DataProvider
from services.options_service import OptionContract, ScoredOption
from services import RiskLevel


@dataclass
class MarketData:
    """Market data context for strategy generation."""
    symbol: str
    current_price: float
    price_history: List[Dict[str, Any]]  # List of price bars with OHLCV data
    quote_timestamp: datetime


@dataclass
class NewsContext:
    """News context for strategy generation."""
    symbol: str
    articles: List[Dict[str, Any]]  # List of news articles with title, sentiment, etc.
    sentiment_score: Optional[float] = None  # Aggregate sentiment (-1.0 to 1.0)


@dataclass
class StrategySignal:
    """Output from a strategy - becomes a Signal candidate."""
    symbol: str
    strategy_type: str  # Name of the strategy that generated this
    risk_level: RiskLevel
    score: float  # 0.0 to 1.0
    expected_profit: float  # In dollars
    max_loss: float  # In dollars (required)
    probability_estimate: float  # 0.0 to 1.0
    reason: str  # Explanation (required)
    option_contracts: Optional[List[ScoredOption]] = None  # Associated options
    breakdown: Optional[Dict[str, float]] = None  # Factor scores for transparency


class Strategy(ABC):
    """Abstract base class for trading strategies.
    
    Each strategy implements the generate() method to analyze market conditions
    and produce Signal candidates. Strategies are pluggable and can be
    enabled/disabled via configuration.
    """

    def __init__(self, name: str, enabled: bool = True):
        """Initialize strategy.
        
        Args:
            name: Unique strategy identifier
            enabled: Whether this strategy is active
        """
        self.name = name
        self.enabled = enabled

    @abstractmethod
    def generate(
        self,
        symbol: str,
        market_data: MarketData,
        options_chain: List[OptionContract],
        news_context: Optional[NewsContext] = None,
        risk_profile: RiskLevel = RiskLevel.MEDIUM,
    ) -> Optional[StrategySignal]:
        """Generate a trading signal from market analysis.
        
        Args:
            symbol: Stock symbol to analyze
            market_data: Current market data including price history
            options_chain: Available option contracts for the symbol
            news_context: Optional news sentiment and articles
            risk_profile: User's risk tolerance level
            
        Returns:
            StrategySignal if a trade opportunity is identified, None otherwise.
            Every signal must include:
            - reason: Explanation of the signal
            - max_loss: Maximum loss estimate in dollars
            - score: Confidence score 0.0-1.0
            - expected_profit: Expected profit in dollars
        """
        pass

    def is_enabled(self) -> bool:
        """Check if strategy is enabled.
        
        Returns:
            True if strategy is active, False otherwise
        """
        return self.enabled

    def enable(self) -> None:
        """Enable this strategy."""
        self.enabled = True

    def disable(self) -> None:
        """Disable this strategy."""
        self.enabled = False


class StrategyRegistry:
    """Registry for managing strategy instances and their lifecycle.
    
    Maintains a collection of strategies, tracks which are enabled,
    and provides methods to execute strategies and collect signals.
    """

    def __init__(self):
        """Initialize empty strategy registry."""
        self._strategies: Dict[str, Strategy] = {}

    def register(self, strategy: Strategy) -> None:
        """Register a strategy.
        
        Args:
            strategy: Strategy instance to register
            
        Raises:
            ValueError: If strategy with same name already registered
        """
        if strategy.name in self._strategies:
            raise ValueError(f"Strategy '{strategy.name}' already registered")
        self._strategies[strategy.name] = strategy

    def unregister(self, strategy_name: str) -> None:
        """Unregister a strategy.
        
        Args:
            strategy_name: Name of strategy to unregister
            
        Raises:
            KeyError: If strategy not found
        """
        del self._strategies[strategy_name]

    def get(self, strategy_name: str) -> Optional[Strategy]:
        """Get a strategy by name.
        
        Args:
            strategy_name: Name of strategy to retrieve
            
        Returns:
            Strategy instance or None if not found
        """
        return self._strategies.get(strategy_name)

    def list_strategies(self) -> List[str]:
        """List all registered strategy names.
        
        Returns:
            List of strategy names
        """
        return list(self._strategies.keys())

    def list_enabled_strategies(self) -> List[str]:
        """List enabled strategy names.
        
        Returns:
            List of enabled strategy names
        """
        return [name for name, strategy in self._strategies.items() if strategy.is_enabled()]

    def enable_strategy(self, strategy_name: str) -> None:
        """Enable a strategy.
        
        Args:
            strategy_name: Name of strategy to enable
            
        Raises:
            KeyError: If strategy not found
        """
        self._strategies[strategy_name].enable()

    def disable_strategy(self, strategy_name: str) -> None:
        """Disable a strategy.
        
        Args:
            strategy_name: Name of strategy to disable
            
        Raises:
            KeyError: If strategy not found
        """
        self._strategies[strategy_name].disable()

    def generate_signals(
        self,
        symbol: str,
        market_data: MarketData,
        options_chain: List[OptionContract],
        news_context: Optional[NewsContext] = None,
        risk_profile: RiskLevel = RiskLevel.MEDIUM,
    ) -> List[StrategySignal]:
        """Generate signals from all enabled strategies.
        
        Args:
            symbol: Stock symbol to analyze
            market_data: Current market data
            options_chain: Available option contracts
            news_context: Optional news context
            risk_profile: User's risk tolerance
            
        Returns:
            List of StrategySignal objects from enabled strategies
        """
        signals = []
        for strategy in self._strategies.values():
            if not strategy.is_enabled():
                continue
            try:
                signal = strategy.generate(
                    symbol=symbol,
                    market_data=market_data,
                    options_chain=options_chain,
                    news_context=news_context,
                    risk_profile=risk_profile,
                )
                if signal is not None:
                    signals.append(signal)
            except Exception as e:
                # Log error but continue with other strategies
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"Error generating signal from strategy '{strategy.name}': {e}",
                    exc_info=True,
                )
        return signals


# Global registry instance
_strategy_registry: Optional[StrategyRegistry] = None


def get_strategy_registry() -> StrategyRegistry:
    """Get or initialize the global strategy registry.
    
    Returns:
        StrategyRegistry instance
    """
    global _strategy_registry
    if _strategy_registry is None:
        _strategy_registry = StrategyRegistry()
    return _strategy_registry


def set_strategy_registry(registry: StrategyRegistry) -> None:
    """Set the global strategy registry.
    
    Args:
        registry: StrategyRegistry instance to use
    """
    global _strategy_registry
    _strategy_registry = registry
