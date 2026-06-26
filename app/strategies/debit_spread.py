"""Debit spread strategy implementation.

Generates defined-risk directional trades using debit spreads.
Supports both bull call spreads (bullish) and bear put spreads (bearish).
"""

from typing import Optional, List
from datetime import datetime, timedelta
import logging

from app.strategies.strategy import Strategy, StrategySignal, MarketData, NewsContext
from services.options_service import OptionContract, ScoredOption
from services import RiskLevel
from app.core.config import config

logger = logging.getLogger(__name__)


class DebitSpreadStrategy(Strategy):
    """Debit spread strategy for defined-risk directional trades.
    
    Generates bull call spreads (bullish) or bear put spreads (bearish) by:
    1. Selecting a long option (ITM or ATM)
    2. Selecting a short option farther out-of-the-money
    3. Calculating net debit, max profit, max loss, and breakeven
    4. Validating reward/risk ratio
    """

    def __init__(self, name: str = "debit_spread", enabled: bool = True):
        """Initialize debit spread strategy.
        
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
        """Generate a debit spread signal.
        
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
        is_bullish = self._should_be_bullish(news_context, risk_profile)
        
        if is_bullish:
            spread = self._generate_bull_call_spread(symbol, current_price, options_chain)
        else:
            spread = self._generate_bear_put_spread(symbol, current_price, options_chain)
        
        if spread is None:
            return None
        
        # Validate reward/risk ratio
        if not self._validate_reward_risk_ratio(spread):
            logger.debug(
                f"Spread rejected for {symbol}: reward/risk ratio too low "
                f"({spread['reward_risk_ratio']:.2f})"
            )
            return None
        
        # Create signal
        signal = StrategySignal(
            symbol=symbol,
            strategy_type="debit_spread",
            risk_level=risk_profile,
            score=self._calculate_score(spread),
            expected_profit=spread["max_profit"],
            max_loss=spread["max_loss"],
            probability_estimate=self._estimate_probability(spread),
            reason=self._generate_reason(spread, is_bullish),
            option_contracts=[
                ScoredOption(
                    contract=spread["long_option"],
                    score=0.8,
                    liquidity_score=spread["long_option"].liquidity_score,
                ),
                ScoredOption(
                    contract=spread["short_option"],
                    score=0.8,
                    liquidity_score=spread["short_option"].liquidity_score,
                ),
            ],
            breakdown={
                "net_debit": spread["net_debit"],
                "max_profit": spread["max_profit"],
                "max_loss": spread["max_loss"],
                "breakeven": spread["breakeven"],
                "reward_risk_ratio": spread["reward_risk_ratio"],
                "long_strike": spread["long_option"].strike,
                "short_strike": spread["short_option"].strike,
                "days_to_expiration": spread["long_option"].days_to_expiration,
            },
        )
        
        return signal

    def _should_be_bullish(self, news_context: Optional[NewsContext], risk_profile: RiskLevel) -> bool:
        """Determine if spread should be bullish or bearish.
        
        Args:
            news_context: Optional news sentiment
            risk_profile: User's risk tolerance
            
        Returns:
            True for bullish (bull call), False for bearish (bear put)
        """
        # Default to bullish if no news context
        if news_context is None or news_context.sentiment_score is None:
            return True
        
        # Use sentiment to determine direction
        return news_context.sentiment_score > 0.0

    def _generate_bull_call_spread(
        self,
        symbol: str,
        current_price: float,
        options_chain: List[OptionContract],
    ) -> Optional[dict]:
        """Generate a bull call spread.
        
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
            and config.DEBIT_SPREAD_MIN_DTE <= opt.days_to_expiration <= config.DEBIT_SPREAD_MAX_DTE
            and opt.volume >= config.DEBIT_SPREAD_MIN_VOLUME
            and opt.open_interest >= config.DEBIT_SPREAD_MIN_OPEN_INTEREST
            and opt.liquidity_score >= config.DEBIT_SPREAD_MIN_LIQUIDITY_SCORE
        ]
        
        if len(calls) < 2:
            return None
        
        # Sort by strike
        calls.sort(key=lambda x: x.strike)
        
        # Find long call (ATM or slightly ITM)
        long_call = None
        for call in calls:
            if call.strike <= current_price * (1 + config.DEBIT_SPREAD_LONG_OTM_THRESHOLD):
                long_call = call
        
        if long_call is None:
            return None
        
        # Find short call (OTM, farther than long)
        short_call = None
        min_strike_diff = current_price * 0.01  # Minimum $0.01 difference
        for call in calls:
            if (
                call.strike > long_call.strike + min_strike_diff
                and call.strike <= current_price * (1 + config.DEBIT_SPREAD_SHORT_OTM_THRESHOLD)
                and call.bid > 0  # Ensure bid exists
            ):
                short_call = call
                break
        
        if short_call is None:
            return None
        
        # Calculate spread metrics
        long_cost = (long_call.bid + long_call.ask) / 2
        short_credit = (short_call.bid + short_call.ask) / 2
        net_debit = long_cost - short_credit
        
        # Reject if net debit is negative or too high
        if net_debit <= 0 or net_debit > config.DEBIT_SPREAD_MAX_DEBIT:
            return None
        
        max_profit = (short_call.strike - long_call.strike) - net_debit
        max_loss = net_debit
        breakeven = long_call.strike + net_debit
        reward_risk_ratio = max_profit / max_loss if max_loss > 0 else 0
        
        return {
            "type": "bull_call",
            "long_option": long_call,
            "short_option": short_call,
            "net_debit": net_debit,
            "max_profit": max_profit,
            "max_loss": max_loss,
            "breakeven": breakeven,
            "reward_risk_ratio": reward_risk_ratio,
        }

    def _generate_bear_put_spread(
        self,
        symbol: str,
        current_price: float,
        options_chain: List[OptionContract],
    ) -> Optional[dict]:
        """Generate a bear put spread.
        
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
            and config.DEBIT_SPREAD_MIN_DTE <= opt.days_to_expiration <= config.DEBIT_SPREAD_MAX_DTE
            and opt.volume >= config.DEBIT_SPREAD_MIN_VOLUME
            and opt.open_interest >= config.DEBIT_SPREAD_MIN_OPEN_INTEREST
            and opt.liquidity_score >= config.DEBIT_SPREAD_MIN_LIQUIDITY_SCORE
        ]
        
        if len(puts) < 2:
            return None
        
        # Sort by strike descending
        puts.sort(key=lambda x: x.strike, reverse=True)
        
        # Find long put (OTM, lower strike)
        long_put = None
        for put in puts:
            if put.strike < current_price * (1 - config.DEBIT_SPREAD_LONG_OTM_THRESHOLD):
                long_put = put
                break
        
        if long_put is None:
            return None
        
        # Find short put (OTM but higher strike than long)
        short_put = None
        min_strike_diff = current_price * 0.01
        for put in puts:
            if (
                put.strike > long_put.strike + min_strike_diff
                and put.strike < current_price * (1 - config.DEBIT_SPREAD_SHORT_OTM_THRESHOLD)
                and put.bid > 0
            ):
                short_put = put
                break
        
        if short_put is None:
            return None
        
        # Calculate spread metrics
        long_cost = (long_put.bid + long_put.ask) / 2
        short_credit = (short_put.bid + short_put.ask) / 2
        net_debit = long_cost - short_credit
        
        # Reject if net debit is negative or too high
        if net_debit <= 0 or net_debit > config.DEBIT_SPREAD_MAX_DEBIT:
            return None
        
        max_profit = (short_put.strike - long_put.strike) - net_debit
        max_loss = net_debit
        breakeven = short_put.strike - net_debit
        reward_risk_ratio = max_profit / max_loss if max_loss > 0 else 0
        
        return {
            "type": "bear_put",
            "long_option": long_put,
            "short_option": short_put,
            "net_debit": net_debit,
            "max_profit": max_profit,
            "max_loss": max_loss,
            "breakeven": breakeven,
            "reward_risk_ratio": reward_risk_ratio,
        }

    def _validate_reward_risk_ratio(self, spread: dict) -> bool:
        """Validate that reward/risk ratio meets minimum threshold.
        
        Args:
            spread: Spread details dict
            
        Returns:
            True if ratio is acceptable, False otherwise
        """
        ratio = spread["reward_risk_ratio"]
        return ratio >= config.DEBIT_SPREAD_MIN_REWARD_RISK_RATIO

    def _calculate_score(self, spread: dict) -> float:
        """Calculate signal score based on spread metrics.
        
        Args:
            spread: Spread details dict
            
        Returns:
            Score from 0.0 to 1.0
        """
        # Score based on reward/risk ratio and liquidity
        ratio_score = min(spread["reward_risk_ratio"] / 2.0, 1.0)  # Cap at 1.0
        liquidity_score = (
            spread["long_option"].liquidity_score
            + spread["short_option"].liquidity_score
        ) / 200.0  # Average and normalize
        
        return (ratio_score * 0.7 + liquidity_score * 0.3)

    def _estimate_probability(self, spread: dict) -> float:
        """Estimate probability of profit.
        
        Args:
            spread: Spread details dict
            
        Returns:
            Probability estimate from 0.0 to 1.0
        """
        # Simple heuristic: higher reward/risk ratio suggests better probability
        ratio = spread["reward_risk_ratio"]
        # Assume 50% base probability, adjusted by ratio
        return min(0.5 + (ratio * 0.1), 0.95)

    def _generate_reason(self, spread: dict, is_bullish: bool) -> str:
        """Generate explanation for the signal.
        
        Args:
            spread: Spread details dict
            is_bullish: Whether spread is bullish
            
        Returns:
            Explanation string
        """
        spread_type = "Bull Call" if is_bullish else "Bear Put"
        long_strike = spread["long_option"].strike
        short_strike = spread["short_option"].strike
        max_profit = spread["max_profit"]
        max_loss = spread["max_loss"]
        ratio = spread["reward_risk_ratio"]
        
        return (
            f"{spread_type} Spread: Buy {long_strike} / Sell {short_strike}. "
            f"Max profit: ${max_profit:.2f}, Max loss: ${max_loss:.2f}, "
            f"Reward/Risk: {ratio:.2f}x"
        )
