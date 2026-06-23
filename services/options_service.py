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
    liquidity_score: float = 0.0  # Liquidity score 0-100


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

    def calculate_liquidity_score(self, contract: OptionContract) -> float:
        """Calculate liquidity score for a contract (0-100).
        
        Liquidity score is based on:
        - Bid/ask spread percentage (lower is better)
        - Volume (higher is better)
        - Open interest (higher is better)
        - Days to expiration (moderate is better)
        
        Args:
            contract: The OptionContract to score.
        
        Returns:
            Liquidity score from 0 to 100.
        """
        if not self._has_bid_ask(contract):
            return 0.0

        scores = []

        # Spread score (0-25 points): lower spread is better
        mid = (contract.bid + contract.ask) / 2.0
        if mid > 0:
            spread_pct = (contract.ask - contract.bid) / mid
            # 0% spread = 25 points, 5% spread = 0 points
            spread_score = max(0, 25 * (1 - spread_pct / 0.05))
            scores.append(spread_score)
        else:
            scores.append(0.0)

        # Volume score (0-25 points): higher volume is better
        if contract.volume is not None:
            # 1000+ volume = 25 points, 0 volume = 0 points
            volume_score = min(25, (contract.volume / 1000.0) * 25)
            scores.append(volume_score)
        else:
            scores.append(0.0)

        # Open interest score (0-25 points): higher OI is better
        if contract.open_interest is not None:
            # 2000+ OI = 25 points, 0 OI = 0 points
            oi_score = min(25, (contract.open_interest / 2000.0) * 25)
            scores.append(oi_score)
        else:
            scores.append(0.0)

        # Days to expiration score (0-25 points): 15-45 days is optimal
        if contract.days_to_expiration is not None:
            dte = contract.days_to_expiration
            if 15 <= dte <= 45:
                # Optimal range: 25 points
                dte_score = 25.0
            elif dte < 15:
                # Too close to expiration: penalize
                dte_score = max(0, 25 * (dte / 15.0))
            else:
                # Too far out: penalize
                dte_score = max(0, 25 * (1 - (dte - 45) / 100.0))
            scores.append(dte_score)
        else:
            scores.append(0.0)

        # Return average of all scores
        return sum(scores) / len(scores) if scores else 0.0


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
        spread_check = self._check_bid_ask_spread(contract)
        if not spread_check["passed"]:
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.BID_ASK_SPREAD_TOO_WIDE,
                message=spread_check["message"],
            )

        # Check volume
        if not self._has_sufficient_volume(contract):
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.VOLUME_TOO_LOW,
                message=f"Contract volume ({contract.volume}) is below minimum ({self.config.min_volume}) for {self.risk_level.value} risk level.",
            )

        # Check open interest
        if not self._has_sufficient_open_interest(contract):
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.OPEN_INTEREST_TOO_LOW,
                message=f"Contract open interest ({contract.open_interest}) is below minimum ({self.config.min_open_interest}) for {self.risk_level.value} risk level.",
            )

        # Check earnings window
        if contract.earnings_date is not None:
            earnings_check = self._check_earnings_window(contract)
            if not earnings_check["passed"]:
                return RiskGuardrail(
                    passed=False,
                    reason=RejectionReason.EARNINGS_WINDOW_RESTRICTED,
                    message=earnings_check["message"],
                )

        # Check live trading approval
        if is_live_trading and not user_approved_live_trading:
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.LIVE_TRADING_NOT_APPROVED,
                message="Live trading is disabled by default. User must explicitly approve live trading.",
            )

        # All guardrails passed
        return RiskGuardrail(
            passed=True,
            reason=RejectionReason.PASSED,
            message="Trade passed all guardrails.",
        )

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

    def _check_earnings_window(self, contract: OptionContract) -> Dict[str, any]:
        """Check if contract is outside earnings window.
        
        Args:
            contract: The OptionContract to check.
        
        Returns:
            Dict with 'passed' bool and 'message' str.
        """
        if contract.earnings_date is None:
            return {"passed": True, "message": "No earnings date."}

        try:
            earnings_dt = datetime.fromisoformat(contract.earnings_date)
            now = datetime.now()
            days_until_earnings = (earnings_dt - now).days
            buffer = self.config.earnings_buffer_days

            if -buffer <= days_until_earnings <= buffer:
                return {
                    "passed": False,
                    "message": f"Contract is within {buffer}-day earnings buffer (earnings in {days_until_earnings} days).",
                }
        except (ValueError, TypeError):
            pass

        return {"passed": True, "message": "Outside earnings window."}
