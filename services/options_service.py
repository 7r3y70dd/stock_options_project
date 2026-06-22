"""Options analysis service for scoring and filtering option contracts.

Provides risk-level-aware scoring, filtering, and ranking of options opportunities.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import math

from app.data_sources import DataProvider, MockDataProvider
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


@dataclass
class FilteredContract:
    """Result of filtering a contract."""
    contract: Optional[OptionContract]
    passed: bool
    rejection_reason: RejectionReason
    rejection_message: str


class OptionsChainFilter:
    """Filter for option contracts based on quality and risk criteria."""

    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize the filter with a risk level.
        
        Args:
            risk_level: The RiskLevel to use for filtering.
        """
        self.risk_level = risk_level
        self.config = get_risk_config(risk_level)

    def filter_contracts(
        self, contracts: List[OptionContract]
    ) -> List[FilteredContract]:
        """Filter a list of option contracts and return results with rejection reasons.
        
        Args:
            contracts: List of OptionContract objects to filter.
        
        Returns:
            List of FilteredContract objects with pass/fail status and rejection reasons.
        """
        results = []
        for contract in contracts:
            result = self._filter_single_contract(contract)
            results.append(result)
        return results

    def _filter_single_contract(self, contract: OptionContract) -> FilteredContract:
        """Filter a single contract and return result with rejection reason.
        
        Args:
            contract: The OptionContract to filter.
        
        Returns:
            FilteredContract with pass/fail status and rejection reason.
        """
        # Check if contract is expired
        if self._is_expired(contract):
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.EXPIRED,
                rejection_message="Contract has expired.",
            )

        # Check for missing bid/ask
        if not self._has_bid_ask(contract):
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.MISSING_BID_ASK,
                rejection_message="Contract is missing bid or ask price.",
            )

        # Check volume (liquidity)
        if not self._has_sufficient_volume(contract):
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.VOLUME_TOO_LOW,
                rejection_message=f"Contract volume ({contract.volume}) is below minimum ({self.config.min_volume}) for {self.risk_level.value} risk level.",
            )

        # Check open interest (liquidity)
        if not self._has_sufficient_open_interest(contract):
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.OPEN_INTEREST_TOO_LOW,
                rejection_message=f"Contract open interest ({contract.open_interest}) is below minimum ({self.config.min_open_interest}) for {self.risk_level.value} risk level.",
            )

        # Check bid-ask spread
        spread_check = self._check_bid_ask_spread(contract)
        if not spread_check["passed"]:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.BID_ASK_SPREAD_TOO_WIDE,
                rejection_message=spread_check["message"],
            )

        # Check expiration window
        if not self._is_in_expiration_window(contract):
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.OUTSIDE_EXPIRATION_WINDOW,
                rejection_message=f"Contract expiration ({contract.days_to_expiration} days) is outside window ({self.config.min_days_to_expiration}-{self.config.max_days_to_expiration} days) for {self.risk_level.value} risk level.",
            )

        # All filters passed
        return FilteredContract(
            contract=contract,
            passed=True,
            rejection_reason=RejectionReason.PASSED,
            rejection_message="Contract passed all filters.",
        )

    def _is_expired(self, contract: OptionContract) -> bool:
        """Check if contract has expired.
        
        Args:
            contract: The OptionContract to check.
        
        Returns:
            True if contract is expired, False otherwise.
        """
        if contract.days_to_expiration is None:
            return True
        return contract.days_to_expiration <= 0

    def _has_bid_ask(self, contract: OptionContract) -> bool:
        """Check if contract has both bid and ask prices.
        
        Args:
            contract: The OptionContract to check.
        
        Returns:
            True if both bid and ask are present, False otherwise.
        """
        return contract.bid is not None and contract.ask is not None

    def _has_sufficient_volume(self, contract: OptionContract) -> bool:
        """Check if contract has sufficient volume.
        
        Args:
            contract: The OptionContract to check.
        
        Returns:
            True if volume meets minimum, False otherwise.
        """
        if contract.volume is None:
            return False
        return contract.volume >= self.config.min_volume

    def _has_sufficient_open_interest(self, contract: OptionContract) -> bool:
        """Check if contract has sufficient open interest.
        
        Args:
            contract: The OptionContract to check.
        
        Returns:
            True if open interest meets minimum, False otherwise.
        """
        if contract.open_interest is None:
            return False
        return contract.open_interest >= self.config.min_open_interest

    def _check_bid_ask_spread(self, contract: OptionContract) -> Dict[str, any]:
        """Check if bid-ask spread is acceptable.
        
        Args:
            contract: The OptionContract to check.
        
        Returns:
            Dict with 'passed' bool and 'message' str.
        """
        if contract.bid is None or contract.ask is None or contract.bid <= 0:
            return {"passed": False, "message": "Cannot calculate spread: missing or invalid bid/ask."}

        mid = (contract.bid + contract.ask) / 2.0
        if mid <= 0:
            return {"passed": False, "message": "Cannot calculate spread: invalid midpoint."}

        spread_pct = (contract.ask - contract.bid) / mid
        if spread_pct > self.config.max_bid_ask_spread_pct:
            return {
                "passed": False,
                "message": f"Bid-ask spread ({spread_pct:.2%}) exceeds maximum ({self.config.max_bid_ask_spread_pct:.2%}) for {self.risk_level.value} risk level.",
            }

        return {"passed": True, "message": "Bid-ask spread is acceptable."}

    def _is_in_expiration_window(self, contract: OptionContract) -> bool:
        """Check if contract expiration is within acceptable window.
        
        Args:
            contract: The OptionContract to check.
        
        Returns:
            True if expiration is within window, False otherwise.
        """
        if contract.days_to_expiration is None:
            return False
        return (
            self.config.min_days_to_expiration
            <= contract.days_to_expiration
            <= self.config.max_days_to_expiration
        )


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

    def __init__(
        self,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        data_provider: Optional[DataProvider] = None,
    ):
        """Initialize the options service with a risk level and optional data provider.
        
        Args:
            risk_level: The RiskLevel to use for filtering and scoring.
            data_provider: Optional DataProvider for fetching market data.
                          If None, uses MockDataProvider.
        """
        self.risk_level = risk_level
        self.config = get_risk_config(risk_level)
        self.risk_engine = RiskEngine(risk_level)
        self.filter = OptionsChainFilter(risk_level)
        self.data_provider = data_provider or MockDataProvider()

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
        explanation = self._generate_explanation(contract, strategy, score, breakdown)

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

    def _determine_strategy(self, contract: OptionContract, price: float) -> str:
        """Determine strategy based on contract characteristics."""
        moneyness = contract.strike / price
        if contract.contract_type == "call":
            if 0.98 <= moneyness <= 1.02:
                return "covered_call"
            elif moneyness > 1.02:
                return "bull_call_spread"
        else:  # put
            if 0.98 <= moneyness <= 1.02:
                return "cash_secured_put"
            elif moneyness < 0.98:
                return "bear_put_spread"
        return "covered_call"

    def _score_liquidity(self, contract: OptionContract) -> float:
        """Score liquidity based on volume and open interest."""
        volume_score = min(100.0, (contract.volume or 0) / self.config.min_volume * 50)
        oi_score = min(100.0, (contract.open_interest or 0) / self.config.min_open_interest * 50)
        return (volume_score + oi_score) / 2

    def _score_spread(self, contract: OptionContract) -> float:
        """Score bid-ask spread (lower spread = higher score)."""
        if contract.bid is None or contract.ask is None or contract.bid <= 0:
            return 0.0
        mid = (contract.bid + contract.ask) / 2.0
        if mid <= 0:
            return 0.0
        spread_pct = (contract.ask - contract.bid) / mid
        return max(0.0, 100.0 - (spread_pct * 1000))

    def _score_moneyness(self, moneyness: float) -> float:
        """Score moneyness (ATM = highest score)."""
        distance_from_atm = abs(moneyness - 1.0)
        return max(0.0, 100.0 - (distance_from_atm * 100))

    def _score_volatility(self, contract: OptionContract) -> float:
        """Score implied volatility."""
        if contract.implied_volatility is None:
            return 50.0
        # Higher IV = higher score (more premium)
        return min(100.0, contract.implied_volatility * 100)

    def _score_time_decay(self, contract: OptionContract) -> float:
        """Score time decay (theta)."""
        if contract.days_to_expiration is None:
            return 50.0
        # Optimal time decay window: 14-45 days
        if 14 <= contract.days_to_expiration <= 45:
            return 100.0
        elif contract.days_to_expiration < 14:
            return 50.0 + (contract.days_to_expiration / 14 * 50)
        else:
            return max(0.0, 100.0 - ((contract.days_to_expiration - 45) / 45 * 50))

    def _generate_warnings(self, contract: OptionContract, breakdown: Dict[str, float]) -> List[str]:
        """Generate warnings for contract."""
        warnings = []
        if breakdown["liquidity"] < 50:
            warnings.append("Low liquidity")
        if breakdown["spread"] < 50:
            warnings.append("Wide bid-ask spread")
        if breakdown["volatility"] < 30:
            warnings.append("Low implied volatility")
        return warnings

    def _calculate_max_loss(self, contract: OptionContract, strategy: str, price: float) -> float:
        """Calculate maximum loss as percentage of portfolio."""
        # Simplified: use bid-ask midpoint as premium
        if contract.bid is None or contract.ask is None:
            return 5.0
        premium = (contract.bid + contract.ask) / 2.0
        max_loss_pct = (premium / price) * 100
        return min(max_loss_pct, self.config.max_loss_per_trade_pct)

    def _calculate_position_size(self, max_loss_pct: float) -> float:
        """Calculate position size based on max loss."""
        # Risk 1% of portfolio per trade
        return (1.0 / max_loss_pct) * 100 if max_loss_pct > 0 else 1.0

    def _generate_explanation(self, contract: OptionContract, strategy: str, score: float, breakdown: Dict[str, float]) -> str:
        """Generate human-readable explanation of the signal."""
        return f"Strategy: {strategy}. Score: {score:.1f}/100. Liquidity: {breakdown['liquidity']:.0f}, Spread: {breakdown['spread']:.0f}, Moneyness: {breakdown['moneyness']:.0f}, Volatility: {breakdown['volatility']:.0f}, Time Decay: {breakdown['time_decay']:.0f}."
