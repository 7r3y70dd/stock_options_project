"""Options analysis service for scoring and filtering option contracts.

Provides risk-level-aware scoring, filtering, ranking, and volatility analysis of options opportunities.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import math
import statistics

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
    historical_volatility: Optional[float] = None  # Historical volatility from price data
    volatility_context: Optional[str] = None  # "expensive", "cheap", "fair"


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
    implied_volatility: Optional[float] = None  # IV for context
    historical_volatility: Optional[float] = None  # HV for context
    iv_hv_ratio: Optional[float] = None  # IV/HV ratio
    volatility_context: Optional[str] = None  # "expensive", "cheap", "fair"


@dataclass
class FilteredContract:
    """Result of filtering a contract."""
    contract: Optional[OptionContract]
    passed: bool
    rejection_reason: RejectionReason
    rejection_message: str


class VolatilityAnalyzer:
    """Analyzer for implied and historical volatility."""

    # Thresholds for flagging expensive/cheap contracts
    EXPENSIVE_IV_HV_RATIO = 1.5  # IV is 50% higher than HV
    CHEAP_IV_HV_RATIO = 0.67  # IV is 33% lower than HV

    @staticmethod
    def calculate_historical_volatility(
        price_bars: List[Dict[str, float]],
        periods: int = 20,
    ) -> Optional[float]:
        """Calculate historical volatility from price bars.
        
        Uses standard deviation of log returns over specified periods.
        
        Args:
            price_bars: List of price bar dicts with 'close' key
            periods: Number of periods to use for calculation (default: 20)
            
        Returns:
            Historical volatility as decimal (e.g., 0.25 for 25%), or None if insufficient data
        """
        if not price_bars or len(price_bars) < 2:
            return None
        
        # Extract closing prices
        closes = [bar.get('close') for bar in price_bars if bar.get('close')]
        
        if len(closes) < 2:
            return None
        
        # Calculate log returns
        log_returns = []
        for i in range(1, len(closes)):
            if closes[i-1] > 0:
                log_return = math.log(closes[i] / closes[i-1])
                log_returns.append(log_return)
        
        if len(log_returns) < 2:
            return None
        
        # Use only the most recent periods
        if len(log_returns) > periods:
            log_returns = log_returns[-periods:]
        
        # Calculate standard deviation (volatility)
        try:
            std_dev = statistics.stdev(log_returns)
            # Annualize: multiply by sqrt(252) for daily data
            annual_volatility = std_dev * math.sqrt(252)
            return annual_volatility
        except (ValueError, statistics.StatisticsError):
            return None

    @staticmethod
    def compare_volatilities(
        implied_vol: Optional[float],
        historical_vol: Optional[float],
    ) -> Tuple[Optional[float], Optional[str]]:
        """Compare implied volatility with historical volatility.
        
        Args:
            implied_vol: Implied volatility as decimal
            historical_vol: Historical volatility as decimal
            
        Returns:
            Tuple of (IV/HV ratio, context) where context is "expensive", "cheap", "fair", or None
        """
        if implied_vol is None or historical_vol is None or historical_vol == 0:
            return None, None
        
        ratio = implied_vol / historical_vol
        
        if ratio >= VolatilityAnalyzer.EXPENSIVE_IV_HV_RATIO:
            context = "expensive"
        elif ratio <= VolatilityAnalyzer.CHEAP_IV_HV_RATIO:
            context = "cheap"
        else:
            context = "fair"
        
        return ratio, context

    @staticmethod
    def flag_contract_volatility(
        contract: OptionContract,
        price_bars: Optional[List[Dict[str, float]]] = None,
    ) -> Tuple[Optional[float], Optional[str]]:
        """Flag a contract as expensive or cheap based on volatility.
        
        Args:
            contract: OptionContract to analyze
            price_bars: Optional price bars for calculating historical volatility
            
        Returns:
            Tuple of (IV/HV ratio, volatility_context)
        """
        # Calculate historical volatility if price bars provided
        hv = None
        if price_bars:
            hv = VolatilityAnalyzer.calculate_historical_volatility(price_bars)
        elif contract.historical_volatility:
            hv = contract.historical_volatility
        
        # Compare with implied volatility
        iv = contract.implied_volatility
        ratio, context = VolatilityAnalyzer.compare_volatilities(iv, hv)
        
        return ratio, context


class OptionsChainFilter:
    """Filter for option contracts based on quality and risk criteria."""

    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize the filter with a risk level.
        
        Args:
            risk_level: The RiskLevel to use for filtering.
        """
        self.risk_level = risk_level
        self.config = get_risk_config(risk_level)
        self.volatility_analyzer = VolatilityAnalyzer()

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
        is_paper_trading: bool = True,
    ) -> Tuple[bool, str]:
        """Validate a trade against risk guardrails.
        
        Args:
            contract: The OptionContract to validate
            max_loss_pct: Maximum loss as percentage of portfolio
            num_contracts: Number of contracts to trade
            current_daily_loss_pct: Current daily loss percentage
            current_open_positions: Current number of open positions
            is_paper_trading: Whether this is paper trading
            
        Returns:
            Tuple of (is_valid, message)
        """
        # Check max loss per trade
        if max_loss_pct > self.config.max_loss_pct_per_trade:
            return False, f"Max loss {max_loss_pct:.2%} exceeds limit {self.config.max_loss_pct_per_trade:.2%}"
        
        # Check daily loss limit
        if current_daily_loss_pct + max_loss_pct > self.config.max_daily_loss_pct:
            return False, f"Daily loss would exceed limit"
        
        # Check max open positions
        if current_open_positions >= self.config.max_open_positions:
            return False, f"Max open positions {self.config.max_open_positions} reached"
        
        return True, "Trade passed all risk checks"
