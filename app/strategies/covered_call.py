"""Covered call strategy implementation.

Generates covered-call ideas only when the user owns or paper-owns shares.
Selects out-of-the-money calls, estimates premium income and assignment risk,
and ranks by annualized return and probability estimate.
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
from services.options_service import ScoredOption, VolatilityAnalyzer, GreeksAnalyzer

logger = logging.getLogger(__name__)


class CoveredCallStrategy(Strategy):
    """Covered call strategy for generating income from owned shares.
    
    A covered call is a strategy where:
    1. Investor owns shares of the underlying stock
    2. Sells (writes) call options on those shares
    3. Collects premium income
    4. Accepts assignment risk (shares called away at strike price)
    
    This strategy only generates signals when shares are available.
    """

    # Configuration parameters
    MIN_SHARES_REQUIRED = 100  # Minimum shares to write calls (1 contract = 100 shares)
    OTM_THRESHOLD = 0.02  # Minimum % above current price for OTM calls (2%)
    MAX_OTM_THRESHOLD = 0.15  # Maximum % above current price (15%)
    MIN_DAYS_TO_EXPIRATION = 7  # Minimum days until expiration
    MAX_DAYS_TO_EXPIRATION = 60  # Maximum days until expiration
    MIN_VOLUME = 10  # Minimum volume for liquidity
    MIN_OPEN_INTEREST = 20  # Minimum open interest for liquidity
    MAX_BID_ASK_SPREAD_PCT = 0.05  # Maximum bid-ask spread as % of mid-price (5%)

    def __init__(self, name: str = "covered_call", enabled: bool = True):
        """Initialize covered call strategy.
        
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
        share_position: int = 0,
    ) -> Optional[StrategySignal]:
        """Generate covered call signal if shares are available.
        
        Args:
            symbol: Stock symbol to analyze
            market_data: Current market data including price history
            options_chain: Available option contracts for the symbol
            news_context: Optional news sentiment and articles
            risk_profile: User's risk tolerance level
            share_position: Number of shares owned (required for this strategy)
            
        Returns:
            StrategySignal if covered call opportunity identified, None otherwise.
            Signal includes:
            - reason: Explanation of the opportunity
            - max_loss: Maximum loss estimate (negative if shares called away below cost basis)
            - expected_profit: Premium income plus capital gains if called away
            - max_upside: Maximum profit if shares called away at strike
            - opportunity_cost: Foregone gains if stock rises above strike
        """
        # Check if user owns sufficient shares
        if share_position < self.MIN_SHARES_REQUIRED:
            logger.debug(
                f"Covered call strategy skipped for {symbol}: "
                f"insufficient shares ({share_position} < {self.MIN_SHARES_REQUIRED})"
            )
            return None

        # Filter for suitable call options
        suitable_calls = self._filter_suitable_calls(
            symbol=symbol,
            current_price=market_data.current_price,
            options_chain=options_chain,
        )

        if not suitable_calls:
            logger.debug(f"No suitable calls found for {symbol}")
            return None

        # Score and rank calls
        scored_calls = self._score_calls(
            symbol=symbol,
            current_price=market_data.current_price,
            calls=suitable_calls,
            share_position=share_position,
            risk_profile=risk_profile,
        )

        if not scored_calls:
            return None

        # Select best opportunity
        best_call = scored_calls[0]

        # Calculate metrics
        premium_income = self._calculate_premium_income(best_call)
        assignment_risk = self._calculate_assignment_risk(best_call)
        max_upside = self._calculate_max_upside(
            current_price=market_data.current_price,
            strike=best_call.strike,
            premium=premium_income,
            share_position=share_position,
        )
        opportunity_cost = self._calculate_opportunity_cost(
            current_price=market_data.current_price,
            strike=best_call.strike,
            share_position=share_position,
        )
        annualized_return = self._calculate_annualized_return(
            premium_income=premium_income,
            current_price=market_data.current_price,
            days_to_expiration=best_call.days_to_expiration or 30,
        )

        # Build explanation
        reason = self._build_reason(
            symbol=symbol,
            strike=best_call.strike,
            expiration=best_call.expiration,
            premium_income=premium_income,
            annualized_return=annualized_return,
            assignment_risk=assignment_risk,
            share_position=share_position,
        )

        # Create signal
        signal = StrategySignal(
            symbol=symbol,
            strategy_type="covered_call",
            risk_level=risk_profile,
            score=best_call.score,
            expected_profit=max_upside,
            max_loss=0.0,  # Covered calls have limited downside (shares already owned)
            probability_estimate=1.0 - assignment_risk,  # Probability of keeping premium
            reason=reason,
            option_contracts=[best_call],
            breakdown={
                "premium_income": premium_income,
                "annualized_return": annualized_return,
                "assignment_risk": assignment_risk,
                "max_upside": max_upside,
                "opportunity_cost": opportunity_cost,
                "liquidity_score": best_call.liquidity_score,
            },
        )

        logger.info(
            f"Generated covered call signal for {symbol}: "
            f"strike={best_call.strike}, premium=${premium_income:.2f}, "
            f"annualized_return={annualized_return:.1%}"
        )

        return signal

    def _filter_suitable_calls(
        self,
        symbol: str,
        current_price: float,
        options_chain: List[OptionContract],
    ) -> List[OptionContract]:
        """Filter for suitable out-of-the-money call options.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            options_chain: All available options
            
        Returns:
            List of suitable call options
        """
        suitable = []

        for contract in options_chain:
            # Must be a call
            if contract.contract_type.lower() != "call":
                continue

            # Must be out-of-the-money (strike > current price)
            if contract.strike <= current_price:
                continue

            # Check OTM threshold
            otm_pct = (contract.strike - current_price) / current_price
            if otm_pct < self.OTM_THRESHOLD or otm_pct > self.MAX_OTM_THRESHOLD:
                continue

            # Check expiration window
            dte = contract.days_to_expiration or 30
            if dte < self.MIN_DAYS_TO_EXPIRATION or dte > self.MAX_DAYS_TO_EXPIRATION:
                continue

            # Check liquidity
            if (contract.volume or 0) < self.MIN_VOLUME:
                continue
            if (contract.open_interest or 0) < self.MIN_OPEN_INTEREST:
                continue

            # Check bid-ask spread
            if contract.bid and contract.ask:
                mid_price = (contract.bid + contract.ask) / 2
                spread_pct = (contract.ask - contract.bid) / mid_price if mid_price > 0 else 1.0
                if spread_pct > self.MAX_BID_ASK_SPREAD_PCT:
                    continue

            suitable.append(contract)

        return suitable

    def _score_calls(
        self,
        symbol: str,
        current_price: float,
        calls: List[OptionContract],
        share_position: int,
        risk_profile: RiskLevel,
    ) -> List[ScoredOption]:
        """Score and rank call options by annualized return and probability.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            calls: Suitable call options to score
            share_position: Number of shares owned
            risk_profile: User's risk tolerance
            
        Returns:
            List of scored options, sorted by score (highest first)
        """
        scored = []

        for call in calls:
            # Calculate metrics
            premium = self._calculate_premium_income(call)
            annualized_return = self._calculate_annualized_return(
                premium_income=premium,
                current_price=current_price,
                days_to_expiration=call.days_to_expiration or 30,
            )
            assignment_risk = self._calculate_assignment_risk(call)

            # Calculate score (0-1)
            # Higher annualized return = higher score
            # Lower assignment risk = higher score
            # Better liquidity = higher score
            return_score = min(annualized_return / 0.50, 1.0)  # 50% annualized = perfect score
            risk_score = 1.0 - assignment_risk
            liquidity_score = (call.liquidity_score or 50) / 100.0

            # Weighted score
            score = (
                return_score * 0.5 +  # 50% weight on return
                risk_score * 0.3 +  # 30% weight on low assignment risk
                liquidity_score * 0.2  # 20% weight on liquidity
            )

            # Build explanation
            explanation = (
                f"Sell {symbol} ${call.strike} call expiring {call.expiration}. "
                f"Collect ${premium:.2f} premium ({annualized_return:.1%} annualized). "
                f"Assignment risk: {assignment_risk:.1%}."
            )

            # Calculate max loss as % of position
            max_loss_pct = 0.0  # Covered calls have no additional downside
            position_size_pct = (share_position * current_price) / (share_position * current_price) * 100

            scored_option = ScoredOption(
                symbol=symbol,
                expiration=call.expiration,
                strike=call.strike,
                contract_type="call",
                strategy="covered_call",
                score=score,
                grade="candidate" if score > 0.6 else "watchlist",
                breakdown={
                    "return_score": return_score,
                    "risk_score": risk_score,
                    "liquidity_score": liquidity_score,
                    "annualized_return": annualized_return,
                    "assignment_risk": assignment_risk,
                },
                warnings=self._generate_warnings(call, assignment_risk),
                explanation=explanation,
                max_loss_pct=max_loss_pct,
                position_size_pct=position_size_pct,
                liquidity_score=call.liquidity_score or 50,
                implied_volatility=call.implied_volatility,
                delta=call.delta,
                theta=call.theta,
            )

            scored.append(scored_option)

        # Sort by score (highest first)
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored

    def _calculate_premium_income(self, call: OptionContract) -> float:
        """Calculate premium income from selling the call.
        
        Args:
            call: Call option contract
            
        Returns:
            Premium income per share (multiply by 100 for per contract)
        """
        if call.bid and call.ask:
            # Use bid price (what we receive when selling)
            return call.bid * 100  # 1 contract = 100 shares
        elif call.last:
            return call.last * 100
        else:
            # Estimate from mid-price
            mid = ((call.bid or 0) + (call.ask or 0)) / 2
            return mid * 100

    def _calculate_assignment_risk(self, call: OptionContract) -> float:
        """Estimate probability of assignment (call exercised).
        
        Higher delta = higher probability of being in-the-money at expiration.
        
        Args:
            call: Call option contract
            
        Returns:
            Assignment risk as probability (0-1)
        """
        if call.delta is not None:
            # Delta approximates probability of finishing ITM
            return min(call.delta, 1.0)
        else:
            # Estimate from strike vs current price
            # Rough approximation: 50% chance if ATM, higher if ITM
            return 0.5

    def _calculate_max_upside(
        self,
        current_price: float,
        strike: float,
        premium: float,
        share_position: int,
    ) -> float:
        """Calculate maximum profit if shares are called away.
        
        Args:
            current_price: Current stock price
            strike: Call strike price
            premium: Premium collected
            share_position: Number of shares
            
        Returns:
            Maximum profit in dollars
        """
        # Profit = (strike - current_price) * shares + premium
        capital_gain = (strike - current_price) * share_position
        return capital_gain + premium

    def _calculate_opportunity_cost(
        self,
        current_price: float,
        strike: float,
        share_position: int,
    ) -> float:
        """Calculate opportunity cost if stock rises above strike.
        
        Args:
            current_price: Current stock price
            strike: Call strike price
            share_position: Number of shares
            
        Returns:
            Opportunity cost in dollars (foregone gains)
        """
        # If stock rises above strike, we miss gains above strike
        # Estimate: assume stock could rise 10% above strike
        potential_price = strike * 1.10
        foregone_gain = (potential_price - strike) * share_position
        return foregone_gain

    def _calculate_annualized_return(
        self,
        premium_income: float,
        current_price: float,
        days_to_expiration: int,
    ) -> float:
        """Calculate annualized return from premium income.
        
        Args:
            premium_income: Premium collected
            current_price: Current stock price
            days_to_expiration: Days until option expires
            
        Returns:
            Annualized return as decimal (e.g., 0.25 for 25%)
        """
        if current_price <= 0 or days_to_expiration <= 0:
            return 0.0

        # Return for holding period
        holding_return = premium_income / (current_price * 100)

        # Annualize
        periods_per_year = 365 / days_to_expiration
        annualized = holding_return * periods_per_year

        return annualized

    def _generate_warnings(
        self,
        call: OptionContract,
        assignment_risk: float,
    ) -> List[str]:
        """Generate warnings for the call option.
        
        Args:
            call: Call option contract
            assignment_risk: Probability of assignment
            
        Returns:
            List of warning messages
        """
        warnings = []

        if assignment_risk > 0.7:
            warnings.append(
                f"High assignment risk ({assignment_risk:.1%}). "
                "Shares likely to be called away."
            )

        if call.implied_volatility and call.implied_volatility < 0.15:
            warnings.append(
                f"Low implied volatility ({call.implied_volatility:.1%}). "
                "Premium may be limited."
            )

        if call.theta and call.theta < 0.01:
            warnings.append(
                "Low theta decay. Time value eroding slowly."
            )

        return warnings

    def _build_reason(
        self,
        symbol: str,
        strike: float,
        expiration: str,
        premium_income: float,
        annualized_return: float,
        assignment_risk: float,
        share_position: int,
    ) -> str:
        """Build explanation for the signal.
        
        Args:
            symbol: Stock symbol
            strike: Call strike price
            expiration: Expiration date
            premium_income: Premium collected
            annualized_return: Annualized return
            assignment_risk: Assignment probability
            share_position: Number of shares
            
        Returns:
            Explanation string
        """
        return (
            f"Covered call opportunity: Sell {symbol} ${strike} calls expiring {expiration}. "
            f"Collect ${premium_income:.2f} premium ({annualized_return:.1%} annualized return). "
            f"Assignment risk: {assignment_risk:.1%}. "
            f"Position: {share_position} shares. "
            f"Max upside if called away: ${strike * share_position:.2f}. "
            f"Opportunity cost if stock rises above strike: Limited to premium collected."
        )
