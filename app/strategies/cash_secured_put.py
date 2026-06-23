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
                "liquidity_score": best_put.liquidity_score,
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

            # Calculate score (0-1)
            # Higher annualized return = higher score
            # Lower assignment risk = higher score
            # Better liquidity = higher score
            # Lower cash requirement relative to available = higher score
            return_score = min(annualized_return / 0.50, 1.0)  # 50% annualized = perfect score
            risk_score = 1.0 - assignment_risk
            liquidity_score = (put.liquidity_score or 50) / 100.0
            cash_efficiency = 1.0 - (cash_req / available_cash)  # Higher score if less cash required

            # Weighted score
            score = (
                return_score * 0.4 +  # 40% weight on return
                risk_score * 0.3 +  # 30% weight on low assignment risk
                liquidity_score * 0.2 +  # 20% weight on liquidity
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
                    "liquidity_score": liquidity_score,
                    "cash_efficiency": cash_efficiency,
                    "annualized_return": annualized_return,
                    "assignment_risk": assignment_risk,
                },
                warnings=self._generate_warnings(put, assignment_risk, cash_req, available_cash),
                explanation=explanation,
                max_loss_pct=max_loss_pct,
                position_size_pct=position_size_pct,
                liquidity_score=put.liquidity_score or 50,
                implied_volatility=put.implied_volatility,
                delta=put.delta,
                theta=put.theta,
            )

            scored.append(scored_option)

        # Sort by score (highest first)
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored

    def _calculate_premium_income(self, put: OptionContract) -> float:
        """Calculate premium income from selling a put.
        
        Args:
            put: Put option contract
            
        Returns:
            Premium income in dollars (bid price * 100 shares per contract)
        """
        if put.bid is None:
            return 0.0
        return put.bid * 100  # 1 contract = 100 shares

    def _calculate_cash_requirement(self, strike: float) -> float:
        """Calculate cash required to cover assignment.
        
        Args:
            strike: Strike price of the put
            
        Returns:
            Cash required in dollars (strike * 100 shares per contract)
        """
        return strike * 100 * self.CASH_REQUIREMENT_MULTIPLIER

    def _calculate_assignment_risk(self, put: OptionContract) -> float:
        """Estimate probability of assignment.
        
        Uses delta as proxy for assignment probability.
        For puts, delta ranges from -1 to 0, so we use absolute value.
        
        Args:
            put: Put option contract
            
        Returns:
            Assignment probability (0.0 to 1.0)
        """
        if put.delta is None:
            # Estimate from moneyness if delta not available
            return 0.3  # Default 30% assignment risk
        # For puts, delta is negative; use absolute value
        return abs(put.delta)

    def _calculate_breakeven(self, strike: float, premium: float) -> float:
        """Calculate breakeven price if assigned.
        
        Args:
            strike: Strike price of the put
            premium: Premium collected
            
        Returns:
            Breakeven price per share
        """
        premium_per_share = premium / 100  # Convert to per-share basis
        return strike - premium_per_share

    def _calculate_max_loss(self, strike: float, premium: float) -> float:
        """Calculate maximum loss if assigned.
        
        Args:
            strike: Strike price of the put
            premium: Premium collected
            
        Returns:
            Maximum loss in dollars
        """
        # Max loss is strike * 100 shares minus premium collected
        return (strike * 100) - premium

    def _calculate_annualized_return(self, premium_income: float, strike: float, days_to_expiration: int) -> float:
        """Calculate annualized return on cash requirement.
        
        Args:
            premium_income: Premium collected in dollars
            strike: Strike price of the put
            days_to_expiration: Days until expiration
            
        Returns:
            Annualized return as decimal (e.g., 0.25 for 25%)
        """
        if days_to_expiration <= 0:
            return 0.0
        
        cash_required = strike * 100
        if cash_required <= 0:
            return 0.0
        
        # Return on cash requirement
        return_pct = premium_income / cash_required
        
        # Annualize
        days_per_year = 365
        annualized = return_pct * (days_per_year / days_to_expiration)
        
        return annualized

    def _generate_warnings(self, put: OptionContract, assignment_risk: float, cash_req: float, available_cash: float) -> List[str]:
        """Generate warnings for a put option.
        
        Args:
            put: Put option contract
            assignment_risk: Probability of assignment
            cash_req: Cash required for assignment
            available_cash: Available cash
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        if assignment_risk > 0.5:
            warnings.append(f"High assignment risk: {assignment_risk:.1%}")
        
        if cash_req > available_cash * 0.8:
            warnings.append(f"High cash requirement: {cash_req / available_cash:.1%} of available cash")
        
        if put.implied_volatility and put.implied_volatility < 0.15:
            warnings.append("Low implied volatility - premium may be limited")
        
        if put.volume and put.volume < 20:
            warnings.append("Low volume - may have difficulty closing position")
        
        return warnings

    def _build_reason(self, symbol: str, strike: float, expiration: str, premium_income: float, annualized_return: float, assignment_risk: float, cash_requirement: float, breakeven: float) -> str:
        """Build explanation for the signal.
        
        Args:
            symbol: Stock symbol
            strike: Strike price
            expiration: Expiration date
            premium_income: Premium collected
            annualized_return: Annualized return
            assignment_risk: Assignment probability
            cash_requirement: Cash required
            breakeven: Breakeven price
            
        Returns:
            Explanation string
        """
        return (
            f"Sell {symbol} ${strike:.2f} put expiring {expiration}. "
            f"Collect ${premium_income:.2f} premium ({annualized_return:.1%} annualized return). "
            f"Assignment risk: {assignment_risk:.1%}. "
            f"Breakeven: ${breakeven:.2f}. "
            f"Cash required: ${cash_requirement:.2f}. "
            f"If assigned, you will buy 100 shares at ${strike:.2f}."
        )
