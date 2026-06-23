"""Options analysis service for scoring and filtering option contracts.

Provides risk-level-aware scoring, filtering, ranking, and volatility analysis of options opportunities.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
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
    delta: Optional[float] = None  # Greek: directional exposure
    gamma: Optional[float] = None  # Greek: acceleration risk
    theta: Optional[float] = None  # Greek: time decay
    vega: Optional[float] = None  # Greek: volatility sensitivity


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
    delta: Optional[float] = None  # Greek: directional exposure
    gamma: Optional[float] = None  # Greek: acceleration risk
    theta: Optional[float] = None  # Greek: time decay
    vega: Optional[float] = None  # Greek: volatility sensitivity
    greeks_summary: Optional[Dict[str, float]] = field(default_factory=dict)  # Summary of Greeks analysis


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


class GreeksAnalyzer:
    """Analyzer for option Greeks (delta, gamma, theta, vega).
    
    Provides methods to analyze Greeks and assess risk based on Greek profiles.
    Greeks measure different dimensions of option risk:
    - Delta: directional exposure (0-1 for calls, -1-0 for puts)
    - Gamma: acceleration risk (how fast delta changes)
    - Theta: time decay (daily loss from time passage)
    - Vega: volatility sensitivity (change per 1% IV change)
    """

    # Greeks thresholds by risk level
    GREEKS_THRESHOLDS = {
        RiskLevel.LOW: {
            "max_delta": 0.30,  # Conservative directional exposure
            "max_gamma": 0.05,  # Low acceleration risk
            "min_theta": -0.02,  # Prefer time decay in our favor
            "max_vega": 0.10,  # Low volatility sensitivity
        },
        RiskLevel.MEDIUM: {
            "max_delta": 0.60,  # Moderate directional exposure
            "max_gamma": 0.10,  # Moderate acceleration risk
            "min_theta": -0.05,  # Accept some time decay
            "max_vega": 0.20,  # Moderate volatility sensitivity
        },
        RiskLevel.HIGH: {
            "max_delta": 0.90,  # Aggressive directional exposure
            "max_gamma": 0.20,  # Higher acceleration risk
            "min_theta": -0.10,  # Accept significant time decay
            "max_vega": 0.40,  # Higher volatility sensitivity
        },
    }

    @staticmethod
    def analyze_greeks(
        contract: OptionContract,
    ) -> Dict[str, float]:
        """Analyze Greeks for a contract.
        
        Args:
            contract: OptionContract to analyze
            
        Returns:
            Dictionary with Greeks analysis including absolute values and risk scores
        """
        analysis = {}
        
        if contract.delta is not None:
            analysis["delta"] = contract.delta
            analysis["delta_abs"] = abs(contract.delta)
        
        if contract.gamma is not None:
            analysis["gamma"] = contract.gamma
            analysis["gamma_abs"] = abs(contract.gamma)
        
        if contract.theta is not None:
            analysis["theta"] = contract.theta
            analysis["theta_abs"] = abs(contract.theta)
        
        if contract.vega is not None:
            analysis["vega"] = contract.vega
            analysis["vega_abs"] = abs(contract.vega)
        
        return analysis

    @staticmethod
    def assess_greek_profile(
        contract: OptionContract,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
    ) -> Tuple[bool, List[str], Dict[str, float]]:
        """Assess if contract's Greek profile is acceptable for risk level.
        
        Args:
            contract: OptionContract to assess
            risk_level: Risk level for threshold comparison
            
        Returns:
            Tuple of (acceptable: bool, warnings: List[str], scores: Dict[str, float])
        """
        thresholds = GreeksAnalyzer.GREEKS_THRESHOLDS.get(
            risk_level, GreeksAnalyzer.GREEKS_THRESHOLDS[RiskLevel.MEDIUM]
        )
        
        warnings = []
        scores = {}
        acceptable = True
        
        # Check delta (directional exposure)
        if contract.delta is not None:
            delta_abs = abs(contract.delta)
            scores["delta_score"] = min(delta_abs / thresholds["max_delta"], 1.0)
            if delta_abs > thresholds["max_delta"]:
                warnings.append(
                    f"Delta {contract.delta:.3f} exceeds {risk_level.value} risk level threshold "
                    f"({thresholds['max_delta']:.3f}). High directional exposure."
                )
                acceptable = False
        
        # Check gamma (acceleration risk)
        if contract.gamma is not None:
            gamma_abs = abs(contract.gamma)
            scores["gamma_score"] = min(gamma_abs / thresholds["max_gamma"], 1.0)
            if gamma_abs > thresholds["max_gamma"]:
                warnings.append(
                    f"Gamma {contract.gamma:.4f} exceeds {risk_level.value} risk level threshold "
                    f"({thresholds['max_gamma']:.4f}). High acceleration risk."
                )
                acceptable = False
        
        # Check theta (time decay)
        if contract.theta is not None:
            scores["theta_score"] = min(abs(contract.theta) / abs(thresholds["min_theta"]), 1.0)
            if contract.theta < thresholds["min_theta"]:
                warnings.append(
                    f"Theta {contract.theta:.4f} exceeds {risk_level.value} risk level threshold "
                    f"({thresholds['min_theta']:.4f}). High time decay risk."
                )
                acceptable = False
        
        # Check vega (volatility sensitivity)
        if contract.vega is not None:
            vega_abs = abs(contract.vega)
            scores["vega_score"] = min(vega_abs / thresholds["max_vega"], 1.0)
            if vega_abs > thresholds["max_vega"]:
                warnings.append(
                    f"Vega {contract.vega:.4f} exceeds {risk_level.value} risk level threshold "
                    f"({thresholds['max_vega']:.4f}). High volatility sensitivity."
                )
                acceptable = False
        
        return acceptable, warnings, scores

    @staticmethod
    def calculate_greeks_score(
        contract: OptionContract,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
    ) -> float:
        """Calculate overall Greeks score (0-1) for a contract.
        
        Args:
            contract: OptionContract to score
            risk_level: Risk level for threshold comparison
            
        Returns:
            Greeks score from 0 (worst) to 1 (best)
        """
        _, _, scores = GreeksAnalyzer.assess_greek_profile(contract, risk_level)
        
        if not scores:
            return 1.0  # No Greeks data, assume acceptable
        
        # Average of all Greek scores (lower is better)
        avg_score = sum(scores.values()) / len(scores)
        # Invert so higher score is better
        return 1.0 - min(avg_score, 1.0)


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
        self.greeks_analyzer = GreeksAnalyzer()

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

        # Check Greeks profile
        greeks_acceptable, greeks_warnings, _ = self.greeks_analyzer.assess_greek_profile(
            contract, self.risk_level
        )
        if not greeks_acceptable:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.UNACCEPTABLE_GREEKS,
                rejection_message=f"Contract Greeks profile unacceptable: {'; '.join(greeks_warnings)}",
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
            Dict with 'passed' bool and 'message' str
        """
        if contract.bid is None or contract.ask is None or contract.bid <= 0:
            return {"passed": False, "message": "Invalid bid/ask prices"}
        
        spread = contract.ask - contract.bid
        spread_pct = (spread / contract.bid) * 100 if contract.bid > 0 else 100
        
        max_spread_pct = self.config.max_bid_ask_spread_pct
        if spread_pct > max_spread_pct:
            return {
                "passed": False,
                "message": f"Bid-ask spread {spread_pct:.2f}% exceeds maximum {max_spread_pct:.2f}% for {self.risk_level.value} risk level.",
            }
        
        return {"passed": True, "message": "Bid-ask spread acceptable"}

    def _is_in_expiration_window(self, contract: OptionContract) -> bool:
        """Check if contract expiration is within acceptable window.
        
        Args:
            contract: The OptionContract to check.
        
        Returns:
            True if expiration is in window, False otherwise.
        """
        if contract.days_to_expiration is None:
            return False
        
        return (
            self.config.min_days_to_expiration <= contract.days_to_expiration <= self.config.max_days_to_expiration
        )
