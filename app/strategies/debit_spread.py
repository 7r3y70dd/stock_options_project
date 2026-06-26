"""Debit spread strategy implementation.

Generates defined-risk directional trades by combining long and short options.
Selects long option and short option farther out-of-the-money, calculates net debit,
max profit, max loss, and breakeven, and validates reward/risk ratio.
"""

import logging
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
import math

from app.strategies.strategy import (
    Strategy,
    StrategySignal,
    MarketData,
    NewsContext,
    OptionContract,
)
from services import RiskLevel
from services.options_service import ScoredOption

logger = logging.getLogger(__name__)


class DebitSpreadStrategy(Strategy):
    """Debit spread strategy for generating defined-risk directional trades.
    
    A debit spread is a strategy where:
    1. Buy (long) an option at a lower strike
    2. Sell (short) an option at a higher strike (for calls) or lower strike (for puts)
    3. Both options have the same expiration
    4. Net cost (debit) is limited and known upfront
    5. Maximum profit and loss are both defined
    
    This strategy generates signals when reward/risk ratio is acceptable.
    """

    # Configuration parameters
    MIN_REWARD_RISK_RATIO = 1.0  # Minimum reward/risk ratio (1:1 or better)
    MIN_SPREAD_WIDTH = 0.5  # Minimum spread width in dollars
    MAX_SPREAD_WIDTH = 5.0  # Maximum spread width in dollars
    MIN_DAYS_TO_EXPIRATION = 7  # Minimum days until expiration
    MAX_DAYS_TO_EXPIRATION = 60  # Maximum days until expiration
    MIN_VOLUME = 10  # Minimum volume for liquidity
    MIN_OPEN_INTEREST = 20  # Minimum open interest for liquidity
    MAX_BID_ASK_SPREAD_PCT = 0.05  # Maximum bid-ask spread as % of mid-price (5%)
    MAX_NET_DEBIT_PCT = 0.05  # Maximum net debit as % of underlying price (5%)

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
        """Generate debit spread signal if suitable opportunity identified.
        
        Args:
            symbol: Stock symbol to analyze
            market_data: Current market data including price history
            options_chain: Available option contracts for the symbol
            news_context: Optional news sentiment and articles
            risk_profile: User's risk tolerance level
            
        Returns:
            StrategySignal if debit spread opportunity identified, None otherwise.
            Signal includes:
            - reason: Explanation of the opportunity
            - max_loss: Maximum loss (net debit paid)
            - expected_profit: Maximum profit potential
            - net_debit: Cost to enter the spread
            - breakeven: Breakeven price at expiration
        """
        current_price = market_data.current_price
        
        # Determine spread direction based on market sentiment and risk profile
        spread_direction = self._determine_spread_direction(
            market_data=market_data,
            news_context=news_context,
            risk_profile=risk_profile,
        )
        
        if spread_direction is None:
            logger.debug(f"No clear directional bias for {symbol}")
            return None
        
        # Filter for suitable options
        if spread_direction == "bullish":
            suitable_spreads = self._find_call_spreads(
                symbol=symbol,
                current_price=current_price,
                options_chain=options_chain,
            )
        else:  # bearish
            suitable_spreads = self._find_put_spreads(
                symbol=symbol,
                current_price=current_price,
                options_chain=options_chain,
            )
        
        if not suitable_spreads:
            logger.debug(f"No suitable {spread_direction} spreads found for {symbol}")
            return None
        
        # Score and rank spreads
        scored_spreads = self._score_spreads(
            symbol=symbol,
            current_price=current_price,
            spreads=suitable_spreads,
            risk_profile=risk_profile,
        )
        
        if not scored_spreads:
            return None
        
        # Select best opportunity
        best_spread = scored_spreads[0]
        long_option = best_spread["long_option"]
        short_option = best_spread["short_option"]
        
        # Calculate metrics
        net_debit = self._calculate_net_debit(long_option, short_option)
        max_profit = self._calculate_max_profit(long_option, short_option, net_debit)
        max_loss = self._calculate_max_loss(long_option, short_option, net_debit)
        breakeven = self._calculate_breakeven(
            long_option=long_option,
            short_option=short_option,
            net_debit=net_debit,
            spread_direction=spread_direction,
        )
        reward_risk_ratio = self._calculate_reward_risk_ratio(max_profit, max_loss)
        
        # Validate reward/risk ratio
        if reward_risk_ratio < self.MIN_REWARD_RISK_RATIO:
            logger.debug(
                f"Debit spread rejected for {symbol}: "
                f"reward/risk ratio {reward_risk_ratio:.2f} < {self.MIN_REWARD_RISK_RATIO}"
            )
            return None
        
        # Build explanation
        reason = self._build_reason(
            symbol=symbol,
            spread_direction=spread_direction,
            long_option=long_option,
            short_option=short_option,
            net_debit=net_debit,
            max_profit=max_profit,
            max_loss=max_loss,
            breakeven=breakeven,
            reward_risk_ratio=reward_risk_ratio,
        )
        
        # Calculate score based on reward/risk and Greeks
        score = self._calculate_score(
            reward_risk_ratio=reward_risk_ratio,
            long_option=long_option,
            short_option=short_option,
        )
        
        # Create signal
        signal = StrategySignal(
            symbol=symbol,
            strategy_type="debit_spread",
            risk_level=risk_profile,
            score=score,
            expected_profit=max_profit,
            max_loss=max_loss,
            probability_estimate=self._estimate_probability(
                long_option=long_option,
                short_option=short_option,
                spread_direction=spread_direction,
            ),
            reason=reason,
            option_contracts=[long_option, short_option],
            breakdown={
                "net_debit": net_debit,
                "max_profit": max_profit,
                "max_loss": max_loss,
                "breakeven": breakeven,
                "reward_risk_ratio": reward_risk_ratio,
                "spread_width": abs(long_option.strike - short_option.strike),
                "long_delta": long_option.delta or 0.0,
                "short_delta": short_option.delta or 0.0,
            },
        )
        
        logger.info(
            f"Generated {spread_direction} debit spread signal for {symbol}: "
            f"long ${long_option.strike} {long_option.contract_type}, "
            f"short ${short_option.strike} {short_option.contract_type}, "
            f"net_debit=${net_debit:.2f}, max_profit=${max_profit:.2f}, "
            f"reward/risk={reward_risk_ratio:.2f}"
        )
        
        return signal

    def _determine_spread_direction(
        self,
        market_data: MarketData,
        news_context: Optional[NewsContext],
        risk_profile: RiskLevel,
    ) -> Optional[str]:
        """Determine whether to use bullish or bearish spread.
        
        Args:
            market_data: Current market data
            news_context: Optional news sentiment
            risk_profile: User's risk tolerance
            
        Returns:
            "bullish", "bearish", or None if no clear bias
        """
        # Simple heuristic: use news sentiment if available
        if news_context and news_context.sentiment_score is not None:
            if news_context.sentiment_score > 0.1:
                return "bullish"
            elif news_context.sentiment_score < -0.1:
                return "bearish"
        
        # Default to bullish for medium risk profile
        if risk_profile == RiskLevel.MEDIUM:
            return "bullish"
        elif risk_profile == RiskLevel.LOW:
            return "bearish"  # Bearish spreads are more conservative
        else:
            return "bullish"  # High risk prefers bullish

    def _find_call_spreads(
        self,
        symbol: str,
        current_price: float,
        options_chain: List[OptionContract],
    ) -> List[Tuple[OptionContract, OptionContract]]:
        """Find suitable bull call spreads (long lower strike, short higher strike).
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            options_chain: All available options
            
        Returns:
            List of (long_call, short_call) tuples
        """
        # Filter for suitable calls
        calls = [
            c for c in options_chain
            if c.contract_type.lower() == "call"
            and self._is_liquid_option(c)
            and self._is_in_expiration_window(c)
        ]
        
        if len(calls) < 2:
            return []
        
        spreads = []
        
        # Find pairs where long strike < short strike
        for i, long_call in enumerate(calls):
            for short_call in calls[i+1:]:
                # Long call should be lower strike (closer to current price)
                if long_call.strike >= short_call.strike:
                    continue
                
                # Check spread width
                spread_width = short_call.strike - long_call.strike
                if spread_width < self.MIN_SPREAD_WIDTH or spread_width > self.MAX_SPREAD_WIDTH:
                    continue
                
                # Both should be out-of-the-money or at-the-money
                if long_call.strike < current_price * 0.95:
                    continue
                
                spreads.append((long_call, short_call))
        
        return spreads

    def _find_put_spreads(
        self,
        symbol: str,
        current_price: float,
        options_chain: List[OptionContract],
    ) -> List[Tuple[OptionContract, OptionContract]]:
        """Find suitable bear put spreads (long lower strike, short higher strike).
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            options_chain: All available options
            
        Returns:
            List of (long_put, short_put) tuples
        """
        # Filter for suitable puts
        puts = [
            p for p in options_chain
            if p.contract_type.lower() == "put"
            and self._is_liquid_option(p)
            and self._is_in_expiration_window(p)
        ]
        
        if len(puts) < 2:
            return []
        
        spreads = []
        
        # Find pairs where long strike < short strike
        for i, long_put in enumerate(puts):
            for short_put in puts[i+1:]:
                # Long put should be lower strike
                if long_put.strike >= short_put.strike:
                    continue
                
                # Check spread width
                spread_width = short_put.strike - long_put.strike
                if spread_width < self.MIN_SPREAD_WIDTH or spread_width > self.MAX_SPREAD_WIDTH:
                    continue
                
                # Both should be out-of-the-money or at-the-money
                if short_put.strike > current_price * 1.05:
                    continue
                
                spreads.append((long_put, short_put))
        
        return spreads

    def _is_liquid_option(self, option: OptionContract) -> bool:
        """Check if option meets liquidity requirements.
        
        Args:
            option: OptionContract to check
            
        Returns:
            True if option is liquid enough
        """
        if (option.volume or 0) < self.MIN_VOLUME:
            return False
        if (option.open_interest or 0) < self.MIN_OPEN_INTEREST:
            return False
        
        if option.bid and option.ask:
            mid_price = (option.bid + option.ask) / 2
            spread_pct = (option.ask - option.bid) / mid_price if mid_price > 0 else 1.0
            if spread_pct > self.MAX_BID_ASK_SPREAD_PCT:
                return False
        
        return True

    def _is_in_expiration_window(self, option: OptionContract) -> bool:
        """Check if option is in acceptable expiration window.
        
        Args:
            option: OptionContract to check
            
        Returns:
            True if option expiration is acceptable
        """
        dte = option.days_to_expiration or 30
        return self.MIN_DAYS_TO_EXPIRATION <= dte <= self.MAX_DAYS_TO_EXPIRATION

    def _score_spreads(
        self,
        symbol: str,
        current_price: float,
        spreads: List[Tuple[OptionContract, OptionContract]],
        risk_profile: RiskLevel,
    ) -> List[Dict]:
        """Score and rank spreads by reward/risk and Greeks.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            spreads: List of (long, short) option tuples
            risk_profile: User's risk tolerance
            
        Returns:
            List of scored spreads, sorted by score (highest first)
        """
        scored = []
        
        for long_option, short_option in spreads:
            net_debit = self._calculate_net_debit(long_option, short_option)
            max_profit = self._calculate_max_profit(long_option, short_option, net_debit)
            max_loss = self._calculate_max_loss(long_option, short_option, net_debit)
            reward_risk_ratio = self._calculate_reward_risk_ratio(max_profit, max_loss)
            
            # Skip if reward/risk is too low
            if reward_risk_ratio < self.MIN_REWARD_RISK_RATIO:
                continue
            
            # Check net debit is reasonable
            net_debit_pct = net_debit / current_price if current_price > 0 else 1.0
            if net_debit_pct > self.MAX_NET_DEBIT_PCT:
                continue
            
            score = self._calculate_score(
                reward_risk_ratio=reward_risk_ratio,
                long_option=long_option,
                short_option=short_option,
            )
            
            scored.append({
                "long_option": long_option,
                "short_option": short_option,
                "score": score,
                "net_debit": net_debit,
                "max_profit": max_profit,
                "max_loss": max_loss,
                "reward_risk_ratio": reward_risk_ratio,
            })
        
        # Sort by score (highest first)
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def _calculate_net_debit(
        self,
        long_option: OptionContract,
        short_option: OptionContract,
    ) -> float:
        """Calculate net debit (cost to enter spread).
        
        Args:
            long_option: Long option (we buy)
            short_option: Short option (we sell)
            
        Returns:
            Net debit in dollars (per contract, multiply by 100 for actual cost)
        """
        long_cost = (long_option.ask or long_option.last or 0.0) * 100
        short_credit = (short_option.bid or short_option.last or 0.0) * 100
        return long_cost - short_credit

    def _calculate_max_profit(
        self,
        long_option: OptionContract,
        short_option: OptionContract,
        net_debit: float,
    ) -> float:
        """Calculate maximum profit at expiration.
        
        Args:
            long_option: Long option
            short_option: Short option
            net_debit: Net debit paid
            
        Returns:
            Maximum profit in dollars
        """
        spread_width = abs(short_option.strike - long_option.strike) * 100
        max_profit = spread_width - net_debit
        return max(max_profit, 0.0)

    def _calculate_max_loss(
        self,
        long_option: OptionContract,
        short_option: OptionContract,
        net_debit: float,
    ) -> float:
        """Calculate maximum loss at expiration.
        
        Args:
            long_option: Long option
            short_option: Short option
            net_debit: Net debit paid
            
        Returns:
            Maximum loss in dollars (positive number)
        """
        return net_debit

    def _calculate_breakeven(
        self,
        long_option: OptionContract,
        short_option: OptionContract,
        net_debit: float,
        spread_direction: str,
    ) -> float:
        """Calculate breakeven price at expiration.
        
        Args:
            long_option: Long option
            short_option: Short option
            net_debit: Net debit paid
            spread_direction: "bullish" or "bearish"
            
        Returns:
            Breakeven price
        """
        net_debit_per_share = net_debit / 100
        
        if spread_direction == "bullish":
            # Bull call spread: breakeven = long strike + net debit per share
            return long_option.strike + net_debit_per_share
        else:
            # Bear put spread: breakeven = short strike - net debit per share
            return short_option.strike - net_debit_per_share

    def _calculate_reward_risk_ratio(
        self,
        max_profit: float,
        max_loss: float,
    ) -> float:
        """Calculate reward/risk ratio.
        
        Args:
            max_profit: Maximum profit
            max_loss: Maximum loss
            
        Returns:
            Reward/risk ratio (profit per dollar of risk)
        """
        if max_loss <= 0:
            return 0.0
        return max_profit / max_loss

    def _calculate_score(
        self,
        reward_risk_ratio: float,
        long_option: OptionContract,
        short_option: OptionContract,
    ) -> float:
        """Calculate overall score for spread.
        
        Args:
            reward_risk_ratio: Reward/risk ratio
            long_option: Long option
            short_option: Short option
            
        Returns:
            Score from 0.0 to 1.0
        """
        # Reward/risk score: 2:1 ratio = perfect score
        reward_risk_score = min(reward_risk_ratio / 2.0, 1.0)
        
        # Liquidity score
        long_liquidity = (long_option.liquidity_score or 50) / 100.0
        short_liquidity = (short_option.liquidity_score or 50) / 100.0
        liquidity_score = (long_liquidity + short_liquidity) / 2.0
        
        # Combined score
        score = reward_risk_score * 0.7 + liquidity_score * 0.3
        return min(score, 1.0)

    def _estimate_probability(
        self,
        long_option: OptionContract,
        short_option: OptionContract,
        spread_direction: str,
    ) -> float:
        """Estimate probability of profit at expiration.
        
        Args:
            long_option: Long option
            short_option: Short option
            spread_direction: "bullish" or "bearish"
            
        Returns:
            Probability estimate from 0.0 to 1.0
        """
        # Use delta as proxy for probability
        if spread_direction == "bullish":
            # Bull call: probability = short call delta (probability it expires worthless)
            return 1.0 - (abs(short_option.delta or 0.5))
        else:
            # Bear put: probability = short put delta (probability it expires worthless)
            return 1.0 - (abs(short_option.delta or 0.5))

    def _build_reason(
        self,
        symbol: str,
        spread_direction: str,
        long_option: OptionContract,
        short_option: OptionContract,
        net_debit: float,
        max_profit: float,
        max_loss: float,
        breakeven: float,
        reward_risk_ratio: float,
    ) -> str:
        """Build explanation for the signal.
        
        Args:
            symbol: Stock symbol
            spread_direction: "bullish" or "bearish"
            long_option: Long option
            short_option: Short option
            net_debit: Net debit paid
            max_profit: Maximum profit
            max_loss: Maximum loss
            breakeven: Breakeven price
            reward_risk_ratio: Reward/risk ratio
            
        Returns:
            Explanation string
        """
        if spread_direction == "bullish":
            spread_name = "bull call spread"
            action = "Buy"
            action2 = "sell"
        else:
            spread_name = "bear put spread"
            action = "Buy"
            action2 = "sell"
        
        return (
            f"Execute {spread_name} on {symbol}: "
            f"{action} ${long_option.strike} {long_option.contract_type} and "
            f"{action2} ${short_option.strike} {short_option.contract_type} "
            f"expiring {long_option.expiration}. "
            f"Net debit: ${net_debit:.2f}. "
            f"Max profit: ${max_profit:.2f}. "
            f"Max loss: ${max_loss:.2f}. "
            f"Breakeven: ${breakeven:.2f}. "
            f"Reward/risk ratio: {reward_risk_ratio:.2f}:1. "
            f"Every spread has known max loss of ${max_loss:.2f}."
        )
