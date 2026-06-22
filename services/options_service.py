"""Options analysis service for scoring and filtering option contracts.

Provides risk-level-aware scoring, filtering, and ranking of options opportunities.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import math

from services import RiskLevel, get_risk_config


@dataclass
class OptionContract:
    """Represents a single option contract with market data."""
    symbol: str
    expiration: str  # ISO format date string
    strike: float
    contract_type: str  # "call" or "put"
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    implied_volatility: Optional[float] = None
    underlying_price: Optional[float] = None
    days_to_expiration: Optional[int] = None


@dataclass
class ScoredOption:
    """Represents a scored option contract with explanation."""
    symbol: str
    expiration: str
    strike: float
    contract_type: str
    strategy: str
    score: float
    grade: str  # "watchlist", "candidate", "avoid"
    breakdown: Dict[str, float]  # Factor scores
    warnings: List[str]
    explanation: str
    max_loss_pct: float
    position_size_pct: float


class OptionsService:
    """Service for analyzing and scoring options contracts."""

    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize the options service with a risk level.
        
        Args:
            risk_level: The RiskLevel to use for filtering and scoring.
        """
        self.risk_level = risk_level
        self.config = get_risk_config(risk_level)

    def score_contract(
        self,
        contract: OptionContract,
        underlying_price: Optional[float] = None,
    ) -> Optional[ScoredOption]:
        """Score a single option contract based on risk level.
        
        Args:
            contract: The OptionContract to score.
            underlying_price: Current underlying stock price (overrides contract.underlying_price).
        
        Returns:
            ScoredOption with score breakdown and explanation, or None if contract fails filters.
        """
        # Use provided underlying_price or fall back to contract value
        price = underlying_price or contract.underlying_price
        if price is None:
            return None

        # Apply strategy filters
        strategy = self._determine_strategy(contract, price)
        if strategy not in self.config.allowed_strategies:
            return None

        # Apply expiration filter
        if contract.days_to_expiration is None:
            return None
        if not (
            self.config.min_days_to_expiration
            <= contract.days_to_expiration
            <= self.config.max_days_to_expiration
        ):
            return None

        # Apply moneyness filter
        moneyness = contract.strike / price
        if not (
            self.config.moneyness_range[0]
            <= moneyness
            <= self.config.moneyness_range[1]
        ):
            return None

        # Calculate component scores
        breakdown = {}
        breakdown["liquidity"] = self._score_liquidity(contract)
        breakdown["spread"] = self._score_spread(contract)
        breakdown["moneyness"] = self._score_moneyness(moneyness)
        breakdown["volatility"] = self._score_volatility(contract)
        breakdown["time_decay"] = self._score_time_decay(contract)

        # Apply risk-level-specific weighting
        weighted_score = sum(
            breakdown[factor] * self.config.scoring_weights.get(factor, 0)
            for factor in breakdown
        )

        # Normalize to 0-100 scale
        score = min(100.0, max(0.0, weighted_score))

        # Generate warnings
        warnings = self._generate_warnings(contract, breakdown)

        # Determine grade
        if score >= 75:
            grade = "watchlist"
        elif score >= 50:
            grade = "candidate"
        else:
            grade = "avoid"

        # Calculate max loss and position sizing
        max_loss_pct = self._calculate_max_loss(contract, strategy, price)
        position_size_pct = self._calculate_position_size(max_loss_pct)

        # Generate explanation
        explanation = self._generate_explanation(
            contract, strategy, score, breakdown, warnings, max_loss_pct
        )

        return ScoredOption(
            symbol=contract.symbol,
            expiration=contract.expiration,
            strike=contract.strike,
            contract_type=contract.contract_type,
            strategy=strategy,
            score=score,
            grade=grade,
            breakdown=breakdown,
            warnings=warnings,
            explanation=explanation,
            max_loss_pct=max_loss_pct,
            position_size_pct=position_size_pct,
        )

    def rank_contracts(
        self,
        contracts: List[OptionContract],
        underlying_price: Optional[float] = None,
    ) -> List[ScoredOption]:
        """Score and rank a list of option contracts.
        
        Args:
            contracts: List of OptionContract objects to score.
            underlying_price: Current underlying stock price.
        
        Returns:
            List of ScoredOption objects sorted by score (highest first).
        """
        scored = []
        for contract in contracts:
            scored_option = self.score_contract(contract, underlying_price)
            if scored_option is not None:
                scored.append(scored_option)

        # Sort by score descending
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored

    def _determine_strategy(
        self, contract: OptionContract, underlying_price: float
    ) -> str:
        """Determine the strategy type for a contract.
        
        Args:
            contract: The OptionContract.
            underlying_price: Current underlying price.
        
        Returns:
            Strategy name string.
        """
        moneyness = contract.strike / underlying_price
        is_call = contract.contract_type.lower() == "call"

        # Simple heuristic: classify by moneyness and type
        if 0.98 <= moneyness <= 1.02:
            if is_call:
                return "covered_call"
            else:
                return "cash_secured_put"
        elif moneyness < 1.0:
            if is_call:
                return "bull_call_spread"
            else:
                return "bear_put_spread"
        else:
            if is_call:
                return "bull_call_spread"
            else:
                return "bear_put_spread"

    def _score_liquidity(self, contract: OptionContract) -> float:
        """Score liquidity based on volume and open interest.
        
        Heuristic: Higher volume and open interest indicate better liquidity.
        Score range: 0-25 (component weight in overall score).
        """
        volume = contract.volume or 0
        oi = contract.open_interest or 0

        # Simple heuristic: normalize to 0-25 scale
        liquidity_score = min(25.0, (volume + oi) / 100.0)
        return max(0.0, liquidity_score)

    def _score_spread(self, contract: OptionContract) -> float:
        """Score bid-ask spread tightness.
        
        Heuristic: Tighter spreads are better. Penalize wide spreads.
        Score range: 0-25.
        """
        if contract.bid is None or contract.ask is None:
            return 12.5  # Neutral score if data missing

        if contract.bid <= 0 or contract.ask <= 0:
            return 0.0

        mid = (contract.bid + contract.ask) / 2.0
        spread_pct = (contract.ask - contract.bid) / mid if mid > 0 else 1.0

        # Penalize spreads wider than threshold
        threshold = self.config.warning_thresholds.get("wide_spread", 0.05)
        if spread_pct > threshold:
            return max(0.0, 25.0 * (1.0 - spread_pct / 0.20))
        else:
            return 25.0 * (1.0 - spread_pct / threshold)

    def _score_moneyness(self, moneyness: float) -> float:
        """Score how close the strike is to current price.
        
        Heuristic: ATM (moneyness ~1.0) is ideal for most strategies.
        Score range: 0-20.
        """
        # Distance from 1.0 (ATM)
        distance = abs(moneyness - 1.0)
        # Penalize distance; max penalty at 20% OTM/ITM
        score = 20.0 * max(0.0, 1.0 - distance / 0.20)
        return score

    def _score_volatility(self, contract: OptionContract) -> float:
        """Score implied volatility.
        
        Heuristic: Moderate IV is preferred; very high or very low IV may indicate risk.
        Score range: 0-30.
        """
        if contract.implied_volatility is None:
            return 15.0  # Neutral score

        iv = contract.implied_volatility
        # Prefer IV in 20-80% range; penalize extremes
        if 0.20 <= iv <= 0.80:
            return 30.0
        elif iv < 0.20:
            return 30.0 * (iv / 0.20)
        else:
            return 30.0 * max(0.0, 1.0 - (iv - 0.80) / 0.50)

    def _score_time_decay(self, contract: OptionContract) -> float:
        """Score time decay favorability.
        
        Heuristic: Contracts with 7-30 days to expiration have optimal theta decay.
        Score range: 0-30.
        """
        dte = contract.days_to_expiration or 0
        # Optimal range: 7-30 days
        if 7 <= dte <= 30:
            return 30.0
        elif dte < 7:
            return 30.0 * (dte / 7.0)
        else:
            return 30.0 * max(0.0, 1.0 - (dte - 30) / 60.0)

    def _generate_warnings(self, contract: OptionContract, breakdown: Dict) -> List[str]:
        """Generate warning flags for a contract.
        
        Args:
            contract: The OptionContract.
            breakdown: Score breakdown dict.
        
        Returns:
            List of warning strings.
        """
        warnings = []

        # Check spread width
        if contract.bid and contract.ask:
            mid = (contract.bid + contract.ask) / 2.0
            spread_pct = (contract.ask - contract.bid) / mid if mid > 0 else 1.0
            if spread_pct > self.config.warning_thresholds.get("wide_spread", 0.05):
                warnings.append("wide_spread")

        # Check volume
        if contract.volume and contract.volume < self.config.warning_thresholds.get(
            "low_volume", 50
        ):
            warnings.append("low_volume")

        # Check open interest
        if contract.open_interest and contract.open_interest < self.config.warning_thresholds.get(
            "low_open_interest", 100
        ):
            warnings.append("low_open_interest")

        # Check IV rank
        if contract.implied_volatility and contract.implied_volatility > self.config.warning_thresholds.get(
            "high_iv_rank", 0.80
        ):
            warnings.append("high_iv_rank")

        return warnings

    def _calculate_max_loss(self, contract: OptionContract, strategy: str, price: float) -> float:
        """Calculate maximum loss as percentage of position.
        
        Args:
            contract: The OptionContract.
            strategy: The strategy type.
            price: Current underlying price.
        
        Returns:
            Max loss as percentage (e.g., 5.0 for 5%).
        """
        # Simplified heuristic based on strategy
        if "spread" in strategy:
            # Spread max loss is the debit paid or width of spread
            if contract.ask:
                return min(self.config.max_loss_per_trade_pct, contract.ask * 100 / price)
        elif "covered" in strategy or "secured" in strategy:
            # Covered/secured strategies have limited loss
            return min(self.config.max_loss_per_trade_pct, 2.0)
        else:
            # Long options can lose 100% of premium
            if contract.ask:
                return min(self.config.max_loss_per_trade_pct, contract.ask * 100 / price)

        return self.config.max_loss_per_trade_pct

    def _calculate_position_size(self, max_loss_pct: float) -> float:
        """Calculate recommended position size based on max loss.
        
        Args:
            max_loss_pct: Maximum loss as percentage.
        
        Returns:
            Recommended position size as percentage of portfolio.
        """
        # Position size = max_loss_per_trade / max_loss_pct
        # Capped by max_position_size_pct
        if max_loss_pct > 0:
            size = self.config.max_loss_per_trade_pct / max_loss_pct
            return min(self.config.max_position_size_pct, size)
        return self.config.max_position_size_pct

    def _generate_explanation(self, contract: OptionContract, strategy: str, score: float, breakdown: Dict, warnings: List[str], max_loss_pct: float) -> str:
        """Generate human-readable explanation of the score.
        
        Args:
            contract: The OptionContract.
            strategy: The strategy type.
            score: Overall score.
            breakdown: Score breakdown dict.
            warnings: List of warning strings.
            max_loss_pct: Maximum loss percentage.
        
        Returns:
            Explanation string.
        """
        parts = []
        parts.append(f"Contract: {contract.contract_type.upper()} ${contract.strike} exp {contract.expiration}")
        parts.append(f"Strategy: {strategy}")
        parts.append(f"Score: {score:.1f}/100")
        parts.append(f"Max Loss: {max_loss_pct:.1f}% of position")

        # Highlight top factors
        top_factors = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)[:2]
        parts.append(f"Strengths: {', '.join([f'{k} ({v:.1f})' for k, v in top_factors])}")

        if warnings:
            parts.append(f"Warnings: {', '.join(warnings)}")

        return " | ".join(parts)
