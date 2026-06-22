"""Options analysis service for scoring and filtering option contracts.

Provides risk-level-aware scoring, filtering, and ranking of options opportunities.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import math

from services import RiskLevel, get_risk_config, RejectionReason, RiskGuardrail


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
    earnings_date: Optional[str] = None  # ISO format date string


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


class RiskEngine:
    """Engine for validating trades against global risk guardrails."""

    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize the risk engine with a risk level.
        
        Args:
            risk_level: The RiskLevel to use for guardrail validation.
        """
        self.risk_level = risk_level
        self.config = get_risk_config(risk_level)

    def validate_trade(
        self,
        contract: OptionContract,
        max_loss_pct: float,
        num_contracts: int = 1,
        current_daily_loss_pct: float = 0.0,
        current_open_positions: int = 0,
        is_live_trading: bool = False,
        user_approved_live_trading: bool = False,
    ) -> RiskGuardrail:
        """Validate a trade against all guardrails.
        
        Args:
            contract: The OptionContract to validate.
            max_loss_pct: Maximum loss for this trade as % of portfolio.
            num_contracts: Number of contracts to trade.
            current_daily_loss_pct: Current daily loss as % of portfolio.
            current_open_positions: Current number of open positions.
            is_live_trading: Whether this is a live trade (vs paper trade).
            user_approved_live_trading: Whether user has approved live trading.
        
        Returns:
            RiskGuardrail with passed status and human-readable message.
        """
        # Check max loss per trade
        if max_loss_pct > self.config.max_loss_per_trade_pct:
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.MAX_LOSS_EXCEEDED,
                message=f"Max loss per trade ({max_loss_pct:.2f}%) exceeds limit ({self.config.max_loss_per_trade_pct:.2f}%) for {self.risk_level.value} risk level.",
            )

        # Check max contracts per trade
        if num_contracts > 10:  # Hard limit
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.MAX_CONTRACTS_EXCEEDED,
                message=f"Number of contracts ({num_contracts}) exceeds maximum (10).",
            )

        # Check max daily loss
        projected_daily_loss = current_daily_loss_pct + max_loss_pct
        if projected_daily_loss > self.config.max_daily_loss_pct:
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.MAX_DAILY_LOSS_EXCEEDED,
                message=f"Projected daily loss ({projected_daily_loss:.2f}%) would exceed limit ({self.config.max_daily_loss_pct:.2f}%) for {self.risk_level.value} risk level.",
            )

        # Check max open positions
        if current_open_positions >= self.config.max_open_positions:
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.MAX_OPEN_POSITIONS_EXCEEDED,
                message=f"Current open positions ({current_open_positions}) meets or exceeds maximum ({self.config.max_open_positions}) for {self.risk_level.value} risk level.",
            )

        # Check bid-ask spread
        if contract.bid is not None and contract.ask is not None and contract.bid > 0:
            mid = (contract.bid + contract.ask) / 2.0
            spread_pct = (contract.ask - contract.bid) / mid if mid > 0 else 1.0
            if spread_pct > self.config.max_bid_ask_spread_pct:
                return RiskGuardrail(
                    passed=False,
                    reason=RejectionReason.BID_ASK_SPREAD_TOO_WIDE,
                    message=f"Bid-ask spread ({spread_pct:.2%}) exceeds maximum ({self.config.max_bid_ask_spread_pct:.2%}) for {self.risk_level.value} risk level.",
                )

        # Check volume
        if contract.volume is not None and contract.volume < self.config.min_volume:
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.VOLUME_TOO_LOW,
                message=f"Contract volume ({contract.volume}) is below minimum ({self.config.min_volume}) for {self.risk_level.value} risk level.",
            )

        # Check open interest
        if contract.open_interest is not None and contract.open_interest < self.config.min_open_interest:
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.OPEN_INTEREST_TOO_LOW,
                message=f"Contract open interest ({contract.open_interest}) is below minimum ({self.config.min_open_interest}) for {self.risk_level.value} risk level.",
            )

        # Check earnings window
        if contract.earnings_date is not None:
            if not self._is_outside_earnings_window(contract.expiration, contract.earnings_date):
                return RiskGuardrail(
                    passed=False,
                    reason=RejectionReason.EARNINGS_WINDOW_RESTRICTED,
                    message=f"Trade is within {self.config.earnings_buffer_days} days of earnings date ({contract.earnings_date}). Restricted for {self.risk_level.value} risk level.",
                )

        # Check live trading approval
        if is_live_trading and not user_approved_live_trading:
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.LIVE_TRADING_NOT_APPROVED,
                message="Live trading is disabled by default. User must explicitly approve live trading before any real-money trades can be executed.",
            )

        # All guardrails passed
        return RiskGuardrail(
            passed=True,
            reason=RejectionReason.PASSED,
            message="Trade passed all guardrails.",
        )

    def _is_outside_earnings_window(
        self, expiration_date: str, earnings_date: str
    ) -> bool:
        """Check if expiration is outside the earnings buffer window.
        
        Args:
            expiration_date: ISO format expiration date string.
            earnings_date: ISO format earnings date string.
        
        Returns:
            True if expiration is outside the buffer window, False otherwise.
        """
        try:
            exp = datetime.fromisoformat(expiration_date).date()
            earn = datetime.fromisoformat(earnings_date).date()
            days_diff = abs((exp - earn).days)
            return days_diff > self.config.earnings_buffer_days
        except (ValueError, AttributeError):
            # If date parsing fails, assume it's outside the window (safe default)
            return True


class OptionsService:
    """Service for analyzing and scoring options contracts."""

    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize the options service with a risk level.
        
        Args:
            risk_level: The RiskLevel to use for filtering and scoring.
        """
        self.risk_level = risk_level
        self.config = get_risk_config(risk_level)
        self.risk_engine = RiskEngine(risk_level)

    def score_contract(
        self,
        contract: OptionContract,
        underlying_price: Optional[float] = None,
        current_daily_loss_pct: float = 0.0,
        current_open_positions: int = 0,
    ) -> Optional[ScoredOption]:
        """Score a single option contract based on risk level.
        
        Args:
            contract: The OptionContract to score.
            underlying_price: Current underlying stock price (overrides contract.underlying_price).
            current_daily_loss_pct: Current daily loss as % of portfolio.
            current_open_positions: Current number of open positions.
        
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

        # Validate against guardrails
        guardrail = self.risk_engine.validate_trade(
            contract,
            max_loss_pct=max_loss_pct,
            num_contracts=1,
            current_daily_loss_pct=current_daily_loss_pct,
            current_open_positions=current_open_positions,
            is_live_trading=False,
        )

        # If guardrails fail, return None (contract is rejected)
        if not guardrail.passed:
            return None

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
        current_daily_loss_pct: float = 0.0,
        current_open_positions: int = 0,
    ) -> List[ScoredOption]:
        """Score and rank a list of option contracts.
        
        Args:
            contracts: List of OptionContract objects to score.
            underlying_price: Current underlying stock price.
            current_daily_loss_pct: Current daily loss as % of portfolio.
            current_open_positions: Current number of open positions.
        
        Returns:
            List of ScoredOption objects sorted by score (highest first).
        """
        scored = []
        for contract in contracts:
            scored_option = self.score_contract(
                contract,
                underlying_price,
                current_daily_loss_pct,
                current_open_positions,
            )
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
        # Position size = max_position_size_pct / (max_loss_pct / max_loss_per_trade_pct)
        if max_loss_pct <= 0:
            return self.config.max_position_size_pct
        ratio = self.config.max_loss_per_trade_pct / max_loss_pct
        return min(self.config.max_position_size_pct, self.config.max_position_size_pct * ratio)

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
        parts = [
            f"Strategy: {strategy}",
            f"Overall Score: {score:.1f}/100",
            f"Max Loss: {max_loss_pct:.2f}%",
            f"Liquidity: {breakdown.get('liquidity', 0):.1f}/25",
            f"Spread: {breakdown.get('spread', 0):.1f}/25",
            f"Moneyness: {breakdown.get('moneyness', 0):.1f}/20",
            f"Volatility: {breakdown.get('volatility', 0):.1f}/30",
            f"Time Decay: {breakdown.get('time_decay', 0):.1f}/30",
        ]
        if warnings:
            parts.append(f"Warnings: {', '.join(warnings)}")
        return " | ".join(parts)
