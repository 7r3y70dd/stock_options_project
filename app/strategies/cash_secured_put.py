"""Cash-secured put strategy implementation.

Generates put-selling ideas only when the user has enough cash to buy shares if assigned.
Selects out-of-the-money puts, estimates assignment risk and breakeven, and validates cash requirements.
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


class CashSecuredPutStrategy(Strategy):
    """Cash-secured put strategy for generating income from available cash.
    
    A cash-secured put is a strategy where:
    1. Investor has sufficient cash to buy shares if assigned
    2. Sells (writes) put options on those shares
    3. Collects premium income
    4. Accepts assignment risk (must buy shares at strike price if assigned)
    
    This strategy only generates signals when sufficient cash is available.
    """

    # Configuration parameters
    MIN_CASH_REQUIRED = 10000.0  # Minimum cash to write puts
    OTM_THRESHOLD = 0.02  # Minimum % below current price for OTM puts (2%)
    MAX_OTM_THRESHOLD = 0.15  # Maximum % below current price (15%)
    MIN_DAYS_TO_EXPIRATION = 7  # Minimum days until expiration
    MAX_DAYS_TO_EXPIRATION = 60  # Maximum days until expiration
    MIN_VOLUME = 10  # Minimum volume for liquidity
    MIN_OPEN_INTEREST = 20  # Minimum open interest for liquidity
    MAX_BID_ASK_SPREAD_PCT = 0.05  # Maximum bid-ask spread as % of mid-price (5%)
    CASH_REQUIREMENT_MULTIPLIER = 1.0  # 100% of strike * 100 shares per contract
    DEFAULT_LIQUIDITY_SCORE = 50.0  # Default liquidity score if not provided

    def __init__(self, name: str = "cash_secured_put", enabled: bool = True):
        """Initialize cash-secured put strategy.
        
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
        available_cash: float = 0.0,
    ) -> Optional[StrategySignal]:
        """Generate cash-secured put signal if sufficient cash is available.
        
        Args:
            symbol: Stock symbol to analyze
            market_data: Current market data including price history
            options_chain: Available option contracts for the symbol
            news_context: Optional news sentiment and articles
            risk_profile: User's risk tolerance level
            available_cash: Amount of cash available (required for this strategy)
            
        Returns:
            StrategySignal if cash-secured put opportunity identified, None otherwise.
            Signal includes:
            - reason: Explanation of the opportunity
            - max_loss: Maximum loss estimate (strike price if assigned)
            - expected_profit: Premium income
            - assignment_risk: Probability of assignment
            - breakeven: Breakeven price if assigned
        """
        # Check if user has sufficient cash
        if available_cash < self.MIN_CASH_REQUIRED:
            logger.debug(
                f"Cash-secured put strategy skipped for {symbol}: "
                f"insufficient cash (${available_cash:.2f} < ${self.MIN_CASH_REQUIRED:.2f})"
            )
            return None

        # Filter for suitable put options
        suitable_puts = self._filter_suitable_puts(
            symbol=symbol,
            current_price=market_data.current_price,
            options_chain=options_chain,
        )

        if not suitable_puts:
            logger.debug(f"No suitable puts found for {symbol}")
            return None

        # Score and rank puts
        scored_puts = self._score_puts(
            symbol=symbol,
            current_price=market_data.current_price,
            puts=suitable_puts,
            available_cash=available_cash,
            risk_profile=risk_profile,
        )

        if not scored_puts:
            return None

        # Select best opportunity
        best_put = scored_puts[0]

        # Calculate metrics
        premium_income = self._calculate_premium_income(best_put)
        assignment_risk = self._calculate_assignment_risk(best_put)
        cash_requirement = self._calculate_cash_requirement(best_put.strike)
        breakeven = self._calculate_breakeven(best_put.strike, premium_income)
        annualized_return = self._calculate_annualized_return(
            premium_income=premium_income,
            strike=best_put.strike,
            days_to_expiration=best_put.days_to_expiration or 30,
        )
        max_loss = self._calculate_max_loss(best_put.strike, premium_income)

        # Verify cash requirement is acceptable
        if cash_requirement > available_cash:
            logger.debug(
                f"Cash-secured put rejected for {symbol}: "
                f"cash requirement (${cash_requirement:.2f}) exceeds available cash (${available_cash:.2f})"
            )
            return None

        # Build explanation
        reason = self._build_reason(
            symbol=symbol,
            strike=best_put.strike,
            expiration=best_put.expiration,
            premium_income=premium_income,
            annualized_return=annualized_return,
            assignment_risk=assignment_risk,
            cash_requirement=cash_requirement,
            breakeven=breakeven,
        )

        # Get liquidity score with fallback
        liquidity_score = self._get_liquidity_score(best_put)

        # Create signal
        signal = StrategySignal(
            symbol=symbol,
            strategy_type="cash_secured_put",
            risk_level=risk_profile,
            score=best_put.score,
            expected_profit=premium_income,
            max_loss=max_loss,
            probability_estimate=1.0 - assignment_risk,  # Probability of keeping premium
            reason=reason,
            option_contracts=[best_put],
            breakdown={
                "premium_income": premium_income,
                "annualized_return": annualized_return,
                "assignment_risk": assignment_risk,
                "cash_requirement": cash_requirement,
                "breakeven": breakeven,
                "max_loss": max_loss,
                "liquidity_score": liquidity_score,
            },
        )

        logger.info(
            f"Generated cash-secured put signal for {symbol}: "
            f"strike=${best_put.strike:.2f}, premium=${premium_income:.2f}, "
            f"annualized_return={annualized_return:.1%}, "
            f"cash_required=${cash_requirement:.2f}"
        )

        return signal

    def _filter_suitable_puts(
        self,
        symbol: str,
        current_price: float,
        options_chain: List[OptionContract],
    ) -> List[OptionContract]:
        """Filter for suitable out-of-the-money put options.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            options_chain: All available options
            
        Returns:
            List of suitable put options
        """
        suitable = []

        for contract in options_chain:
            # Must be a put
            if contract.contract_type.lower() != "put":
                continue

            # Must be out-of-the-money (strike < current price)
            if contract.strike >= current_price:
                continue

            # Check OTM threshold
            otm_pct = (current_price - contract.strike) / current_price
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

    def _score_puts(
        self,
        symbol: str,
        current_price: float,
        puts: List[OptionContract],
        available_cash: float,
        risk_profile: RiskLevel,
    ) -> List[ScoredOption]:
        """Score and rank put options by annualized return and probability.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            puts: Suitable put options to score
            available_cash: Available cash for assignment
            risk_profile: User's risk tolerance
            
        Returns:
            List of scored options, sorted by score (highest first)
        """
        scored = []

        for put in puts:
            # Calculate metrics
            premium = self._calculate_premium_income(put)
            cash_req = self._calculate_cash_requirement(put.strike)
            assignment_risk = self._calculate_assignment_risk(put)
            annualized_return = self._calculate_annualized_return(
                premium_income=premium,
                strike=put.strike,
                days_to_expiration=put.days_to_expiration or 30,
            )
            breakeven = self._calculate_breakeven(put.strike, premium)

            # Check if cash requirement is acceptable
            if cash_req > available_cash:
                logger.debug(
                    f"Skipping {symbol} ${put.strike} put: "
                    f"cash requirement ${cash_req:.2f} exceeds available ${available_cash:.2f}"
                )
                continue

            # Get liquidity score with fallback
            liquidity_score = self._get_liquidity_score(put)

            # Calculate score (0-1)
            # Higher annualized return = higher score
            # Lower assignment risk = higher score
            # Better liquidity = higher score
            # Lower cash requirement relative to available = higher score
            return_score = min(annualized_return / 0.50, 1.0)  # 50% annualized = perfect score
            risk_score = 1.0 - assignment_risk
            liquidity_score_normalized = liquidity_score / 100.0
            cash_efficiency = 1.0 - (cash_req / available_cash)  # Higher score if less cash required

            # Weighted score
            score = (
                return_score * 0.4 +  # 40% weight on return
                risk_score * 0.3 +  # 30% weight on low assignment risk
                liquidity_score_normalized * 0.2 +  # 20% weight on liquidity
                cash_efficiency * 0.1  # 10% weight on cash efficiency
            )

            # Build explanation
            explanation = (
                f"Sell {symbol} ${put.strike} put expiring {put.expiration}. "
                f"Collect ${premium:.2f} premium ({annualized_return:.1%} annualized). "
                f"Assignment risk: {assignment_risk:.1%}. "
                f"Breakeven: ${breakeven:.2f}. "
                f"Cash required: ${cash_req:.2f}."
            )

            # Calculate max loss as % of position
            max_loss_pct = (put.strike / current_price - 1.0) * 100 if current_price > 0 else 0
            position_size_pct = (cash_req / available_cash) * 100

            scored_option = ScoredOption(
                symbol=symbol,
                expiration=put.expiration,
                strike=put.strike,
                contract_type="put",
                strategy="cash_secured_put",
                score=score,
                grade="candidate" if score > 0.6 else "watchlist",
                breakdown={
                    "return_score": return_score,
                    "risk_score": risk_score,
                    "liquidity_score": liquidity_score_normalized,
                    "cash_efficiency": cash_efficiency,
                },
                warnings=[],
                explanation=explanation,
                max_loss_pct=max_loss_pct,
                position_size_pct=position_size_pct,
                liquidity_score=liquidity_score,
                implied_volatility=put.implied_volatility,
            )
            scored.append(scored_option)

        # Sort by score (highest first)
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored

    def _get_liquidity_score(self, contract: OptionContract) -> float:
        """Get liquidity score from contract, with fallback calculation.
        
        Args:
            contract: OptionContract to get liquidity score from
            
        Returns:
            Liquidity score 0-100
        """
        # If contract has liquidity_score attribute, use it
        if hasattr(contract, 'liquidity_score') and contract.liquidity_score is not None:
            return contract.liquidity_score
        
        # Otherwise calculate from bid/ask spread, volume, and open interest
        return self._calculate_liquidity_score(contract)

    def _calculate_liquidity_score(self, contract: OptionContract) -> float:
        """Calculate liquidity score from contract metrics.
        
        Args:
            contract: OptionContract to score
            
        Returns:
            Liquidity score 0-100
        """
        score = 0.0
        
        # Bid-ask spread component (0-25 points)
        if contract.bid and contract.ask:
            mid_price = (contract.bid + contract.ask) / 2
            if mid_price > 0:
                spread_pct = (contract.ask - contract.bid) / mid_price
                # Tight spread (< 1%) = 25 points, wide spread (> 5%) = 0 points
                if spread_pct < 0.01:
                    score += 25.0
                elif spread_pct > 0.05:
                    score += 0.0
                else:
                    score += 25.0 * (1.0 - (spread_pct - 0.01) / 0.04)
        
        # Volume component (0-25 points)
        volume = contract.volume or 0
        if volume >= 100:
            score += 25.0
        elif volume >= 10:
            score += 25.0 * (volume / 100.0)
        
        # Open interest component (0-25 points)
        oi = contract.open_interest or 0
        if oi >= 500:
            score += 25.0
        elif oi >= 20:
            score += 25.0 * (oi / 500.0)
        
        # Days to expiration component (0-25 points)
        dte = contract.days_to_expiration or 30
        # Optimal window: 15-45 days
        if 15 <= dte <= 45:
            score += 25.0
        elif 7 <= dte < 15 or 45 < dte <= 60:
            score += 12.5  # Acceptable but not optimal
        
        return min(score, 100.0)

    def _calculate_premium_income(self, contract: OptionContract) -> float:
        """Calculate premium income from bid price.
        
        Args:
            contract: OptionContract to calculate from
            
        Returns:
            Premium income per contract (bid price * 100)
        """
        if contract.bid is None:
            return 0.0
        return contract.bid * 100.0

    def _calculate_assignment_risk(self, contract: OptionContract) -> float:
        """Estimate probability of assignment.
        
        For OTM puts, assignment risk is roughly delta (probability ITM at expiration).
        
        Args:
            contract: OptionContract to estimate from
            
        Returns:
            Assignment risk as probability (0.0 to 1.0)
        """
        if contract.delta is not None:
            # For puts, delta is negative; use absolute value
            return abs(contract.delta)
        
        # Fallback: estimate from strike vs current price
        if contract.underlying_price and contract.strike:
            otm_pct = (contract.underlying_price - contract.strike) / contract.underlying_price
            # Rough estimate: 2% OTM ≈ 20% assignment risk, 15% OTM ≈ 5% risk
            if otm_pct <= 0.02:
                return 0.20
            elif otm_pct >= 0.15:
                return 0.05
            else:
                return 0.20 - (otm_pct - 0.02) / 0.13 * 0.15
        
        return 0.10  # Default estimate

    def _calculate_cash_requirement(self, strike: float) -> float:
        """Calculate cash required to cover assignment.
        
        Args:
            strike: Strike price
            
        Returns:
            Cash required (strike * 100 shares per contract)
        """
        return strike * 100.0 * self.CASH_REQUIREMENT_MULTIPLIER

    def _calculate_breakeven(self, strike: float, premium_income: float) -> float:
        """Calculate breakeven price if assigned.
        
        Args:
            strike: Strike price
            premium_income: Premium collected
            
        Returns:
            Breakeven price
        """
        return strike - (premium_income / 100.0)

    def _calculate_annualized_return(self, premium_income: float, strike: float, days_to_expiration: int) -> float:
        """Calculate annualized return on cash requirement.
        
        Args:
            premium_income: Premium collected
            strike: Strike price
            days_to_expiration: Days until expiration
            
        Returns:
            Annualized return as decimal (e.g., 0.25 for 25%)
        """
        cash_req = self._calculate_cash_requirement(strike)
        if cash_req <= 0:
            return 0.0
        
        return_pct = premium_income / cash_req
        annualized = return_pct * (365.0 / max(days_to_expiration, 1))
        return annualized

    def _calculate_max_loss(self, strike: float, premium_income: float) -> float:
        """Calculate maximum loss if assigned.
        
        Args:
            strike: Strike price
            premium_income: Premium collected
            
        Returns:
            Maximum loss (strike * 100 - premium collected)
        """
        return (strike * 100.0) - premium_income

    def _build_reason(self, symbol: str, strike: float, expiration: str, premium_income: float,
                      annualized_return: float, assignment_risk: float, cash_requirement: float,
                      breakeven: float) -> str:
        """Build explanation for the signal.
        
        Args:
            symbol: Stock symbol
            strike: Strike price
            expiration: Expiration date
            premium_income: Premium collected
            annualized_return: Annualized return
            assignment_risk: Assignment risk
            cash_requirement: Cash required
            breakeven: Breakeven price
            
        Returns:
            Explanation string
        """
        return (
            f"Cash-secured put opportunity: Sell {symbol} ${strike:.2f} put expiring {expiration}. "
            f"Collect ${premium_income:.2f} premium ({annualized_return:.1%} annualized return). "
            f"Assignment risk: {assignment_risk:.1%}. "
            f"Breakeven: ${breakeven:.2f}. "
            f"Cash required: ${cash_requirement:.2f}."
        )
