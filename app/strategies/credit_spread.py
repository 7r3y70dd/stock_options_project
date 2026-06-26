"""Credit spread strategy implementation.

Generates defined-risk premium-selling trades using credit spreads.
Supports both bull put spreads (bearish) and bear call spreads (bullish).
"""

from typing import Optional, List
from datetime import datetime, timedelta
import logging

from app.strategies.strategy import Strategy, StrategySignal, MarketData, NewsContext
from services.options_service import OptionContract, ScoredOption
from services import RiskLevel
from app.core.config import config

logger = logging.getLogger(__name__)


class CreditSpreadStrategy(Strategy):
    """Credit spread strategy for defined-risk premium-selling trades.
    
    Generates bull put spreads (bearish) or bear call spreads (bullish) by:
    1. Selecting a short option (OTM)
    2. Selecting a protective long option farther out-of-the-money
    3. Calculating net credit, max loss, and breakeven
    4. Validating liquidity and spread width
    5. Ensuring no naked short options are generated
    """

    def __init__(self, name: str = "credit_spread", enabled: bool = True):
        """Initialize credit spread strategy.
        
        Args:
            name: Strategy identifier
            enabled: Whether strategy is active
        """
        super().__init__(name=name, enabled=enabled)

    def generate(
        self,
        symbol: str,
        market_data: MarketData,
        options_chain: List[OptionContract],
        news_context: Optional[NewsContext] = None,
        risk_profile: RiskLevel = RiskLevel.MEDIUM,
    ) -> Optional[StrategySignal]:
        """Generate a credit spread signal.
        
        Args:
            symbol: Stock symbol to analyze
            market_data: Current market data including price
            options_chain: Available option contracts
            news_context: Optional news sentiment
            risk_profile: User's risk tolerance
            
        Returns:
            StrategySignal if a spread opportunity is identified, None otherwise
        """
        if not options_chain:
            return None

        current_price = market_data.current_price
        
        # Determine spread direction based on sentiment and risk profile
        is_bearish = self._should_be_bearish(news_context, risk_profile)
        
        if is_bearish:
            spread = self._generate_bull_put_spread(symbol, current_price, options_chain)
        else:
            spread = self._generate_bear_call_spread(symbol, current_price, options_chain)
        
        if spread is None:
            return None
        
        # Validate spread width and liquidity
        if not self._validate_spread_quality(spread):
            logger.debug(
                f"Spread rejected for {symbol}: poor quality "
                f"(width: {spread['spread_width']:.2f}, liquidity: {spread['avg_liquidity_score']:.1f})"
            )
            return None
        
        # Create signal
        signal = StrategySignal(
            symbol=symbol,
            strategy_type="credit_spread",
            risk_level=risk_profile,
            score=self._calculate_score(spread),
            expected_profit=spread["net_credit"],
            max_loss=spread["max_loss"],
            probability_estimate=self._estimate_probability(spread),
            reason=self._generate_reason(spread, is_bearish),
            option_contracts=[
                ScoredOption(
                    contract=spread["short_option"],
                    score=0.8,
                    liquidity_score=spread["short_option"].liquidity_score,
                ),
                ScoredOption(
                    contract=spread["long_option"],
                    score=0.8,
                    liquidity_score=spread["long_option"].liquidity_score,
                ),
            ],
            breakdown={
                "net_credit": spread["net_credit"],
                "max_loss": spread["max_loss"],
                "max_profit": spread["net_credit"],  # Max profit is the credit received
                "breakeven": spread["breakeven"],
                "spread_width": spread["spread_width"],
                "short_strike": spread["short_option"].strike,
                "long_strike": spread["long_option"].strike,
                "days_to_expiration": spread["short_option"].days_to_expiration,
                "return_on_risk": spread["return_on_risk"],
            },
        )
        
        return signal

    def _should_be_bearish(self, news_context: Optional[NewsContext], risk_profile: RiskLevel) -> bool:
        """Determine if spread should be bearish or bullish.
        
        Args:
            news_context: Optional news sentiment
            risk_profile: User's risk tolerance
            
        Returns:
            True for bearish (bull put), False for bullish (bear call)
        """
        # Default to bearish if no news context
        if news_context is None or news_context.sentiment_score is None:
            return True
        
        # Use sentiment to determine direction
        return news_context.sentiment_score < 0.0

    def _generate_bull_put_spread(
        self,
        symbol: str,
        current_price: float,
        options_chain: List[OptionContract],
    ) -> Optional[dict]:
        """Generate a bull put spread (bearish, short put + long put).
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            options_chain: Available options
            
        Returns:
            Spread details dict or None if no valid spread found
        """
        # Filter puts with valid expiration and liquidity
        puts = [
            opt for opt in options_chain
            if opt.contract_type == "put"
            and config.CREDIT_SPREAD_MIN_DTE <= opt.days_to_expiration <= config.CREDIT_SPREAD_MAX_DTE
            and opt.volume >= config.CREDIT_SPREAD_MIN_VOLUME
            and opt.open_interest >= config.CREDIT_SPREAD_MIN_OPEN_INTEREST
            and opt.liquidity_score >= config.CREDIT_SPREAD_MIN_LIQUIDITY_SCORE
        ]
        
        if len(puts) < 2:
            return None
        
        # Sort by strike descending
        puts.sort(key=lambda x: x.strike, reverse=True)
        
        # Find short put (OTM, higher strike)
        short_put = None
        for put in puts:
            if put.strike < current_price * (1 - config.CREDIT_SPREAD_SHORT_OTM_THRESHOLD):
                short_put = put
                break
        
        if short_put is None:
            return None
        
        # Find long put (OTM, lower strike, protective)
        long_put = None
        min_strike_diff = current_price * 0.01  # Minimum $0.01 difference
        for put in puts:
            if (
                put.strike < short_put.strike - min_strike_diff
                and put.strike < current_price * (1 - config.CREDIT_SPREAD_LONG_OTM_THRESHOLD)
                and put.bid > 0  # Ensure bid exists
            ):
                long_put = put
                break
        
        if long_put is None:
            return None
        
        # Calculate spread metrics
        short_credit = (short_put.bid + short_put.ask) / 2
        long_cost = (long_put.bid + long_put.ask) / 2
        net_credit = short_credit - long_cost
        
        # Reject if net credit is negative or too low
        if net_credit <= 0 or net_credit < config.CREDIT_SPREAD_MIN_CREDIT:
            return None
        
        spread_width = short_put.strike - long_put.strike
        max_loss = spread_width - net_credit
        breakeven = short_put.strike - net_credit
        return_on_risk = net_credit / max_loss if max_loss > 0 else 0
        
        return {
            "type": "bull_put",
            "short_option": short_put,
            "long_option": long_put,
            "net_credit": net_credit,
            "max_loss": max_loss,
            "breakeven": breakeven,
            "spread_width": spread_width,
            "return_on_risk": return_on_risk,
            "avg_liquidity_score": (short_put.liquidity_score + long_put.liquidity_score) / 2,
        }

    def _generate_bear_call_spread(
        self,
        symbol: str,
        current_price: float,
        options_chain: List[OptionContract],
    ) -> Optional[dict]:
        """Generate a bear call spread (bullish, short call + long call).
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            options_chain: Available options
            
        Returns:
            Spread details dict or None if no valid spread found
        """
        # Filter calls with valid expiration and liquidity
        calls = [
            opt for opt in options_chain
            if opt.contract_type == "call"
            and config.CREDIT_SPREAD_MIN_DTE <= opt.days_to_expiration <= config.CREDIT_SPREAD_MAX_DTE
            and opt.volume >= config.CREDIT_SPREAD_MIN_VOLUME
            and opt.open_interest >= config.CREDIT_SPREAD_MIN_OPEN_INTEREST
            and opt.liquidity_score >= config.CREDIT_SPREAD_MIN_LIQUIDITY_SCORE
        ]
        
        if len(calls) < 2:
            return None
        
        # Sort by strike ascending
        calls.sort(key=lambda x: x.strike)
        
        # Find short call (OTM, lower strike)
        short_call = None
        for call in calls:
            if call.strike > current_price * (1 + config.CREDIT_SPREAD_SHORT_OTM_THRESHOLD):
                short_call = call
                break
        
        if short_call is None:
            return None
        
        # Find long call (OTM, higher strike, protective)
        long_call = None
        min_strike_diff = current_price * 0.01
        for call in calls:
            if (
                call.strike > short_call.strike + min_strike_diff
                and call.strike > current_price * (1 + config.CREDIT_SPREAD_LONG_OTM_THRESHOLD)
                and call.bid > 0
            ):
                long_call = call
                break
        
        if long_call is None:
            return None
        
        # Calculate spread metrics
        short_credit = (short_call.bid + short_call.ask) / 2
        long_cost = (long_call.bid + long_call.ask) / 2
        net_credit = short_credit - long_cost
        
        # Reject if net credit is negative or too low
        if net_credit <= 0 or net_credit < config.CREDIT_SPREAD_MIN_CREDIT:
            return None
        
        spread_width = long_call.strike - short_call.strike
        max_loss = spread_width - net_credit
        breakeven = short_call.strike + net_credit
        return_on_risk = net_credit / max_loss if max_loss > 0 else 0
        
        return {
            "type": "bear_call",
            "short_option": short_call,
            "long_option": long_call,
            "net_credit": net_credit,
            "max_loss": max_loss,
            "breakeven": breakeven,
            "spread_width": spread_width,
            "return_on_risk": return_on_risk,
            "avg_liquidity_score": (short_call.liquidity_score + long_call.liquidity_score) / 2,
        }

    def _validate_spread_quality(self, spread: dict) -> bool:
        """Validate that spread meets quality requirements.
        
        Args:
            spread: Spread details dict
            
        Returns:
            True if spread quality is acceptable, False otherwise
        """
        # Check spread width is not too wide (low liquidity)
        if spread["spread_width"] > config.CREDIT_SPREAD_MAX_WIDTH:
            return False
        
        # Check average liquidity score
        if spread["avg_liquidity_score"] < config.CREDIT_SPREAD_MIN_LIQUIDITY_SCORE:
            return False
        
        # Check return on risk ratio
        if spread["return_on_risk"] < config.CREDIT_SPREAD_MIN_RETURN_ON_RISK:
            return False
        
        return True

    def _calculate_score(self, spread: dict) -> float:
        """Calculate signal score based on spread metrics.
        
        Args:
            spread: Spread details dict
            
        Returns:
            Score from 0.0 to 1.0
        """
        # Score based on return on risk and liquidity
        ror_score = min(spread["return_on_risk"] / 0.5, 1.0)  # Cap at 1.0
        liquidity_score = spread["avg_liquidity_score"] / 100.0  # Normalize to 0-1
        
        return (ror_score * 0.6 + liquidity_score * 0.4)

    def _estimate_probability(self, spread: dict) -> float:
        """Estimate probability of profit.
        
        Args:
            spread: Spread details dict
            
        Returns:
            Probability estimate from 0.0 to 1.0
        """
        # Simple heuristic: higher return on risk suggests better probability
        # Assume 50% base probability, adjusted by return on risk
        base_probability = 0.50
        ror_adjustment = min(spread["return_on_risk"] * 0.1, 0.25)  # Cap adjustment at 0.25
        return min(base_probability + ror_adjustment, 0.95)  # Cap at 0.95

    def _generate_reason(self, spread: dict, is_bearish: bool) -> str:
        """Generate explanation for the signal.
        
        Args:
            spread: Spread details dict
            is_bearish: Whether spread is bearish
            
        Returns:
            Explanation string
        """
        spread_type = "bull put" if is_bearish else "bear call"
        short_strike = spread["short_option"].strike
        long_strike = spread["long_option"].strike
        net_credit = spread["net_credit"]
        max_loss = spread["max_loss"]
        
        return (
            f"Defined-risk {spread_type} spread: "
            f"Sell ${short_strike:.2f} / Buy ${long_strike:.2f}. "
            f"Net credit: ${net_credit:.2f}, Max loss: ${max_loss:.2f}. "
            f"Return on risk: {spread['return_on_risk']:.2%}."
        )
