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

try:
    from app.options.pricing import QuantLibPricingEngine
    QUANTLIB_AVAILABLE = True
except ImportError:
    QUANTLIB_AVAILABLE = False


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
    theoretical_price: Optional[float] = None  # Black-Scholes theoretical price
    pricing_difference: Optional[float] = None  # Market mid-price minus theoretical price
    pricing_assessment: Optional[str] = None  # "overpriced", "underpriced", "fair"


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
    theoretical_price: Optional[float] = None  # Black-Scholes theoretical price
    market_mid_price: Optional[float] = None  # Market mid-price (bid + ask) / 2
    pricing_difference: Optional[float] = None  # Market mid-price minus theoretical price
    pricing_assessment: Optional[str] = None  # "overpriced", "underpriced", "fair"


@dataclass
class FilteredContract:
    """Result of filtering a contract."""
    contract: Optional[OptionContract]
    passed: bool
    rejection_reason: RejectionReason
    rejection_message: str


@dataclass
class RiskGuardrailResult:
    """Result of a risk guardrail validation."""
    passed: bool
    reason: RejectionReason
    message: str


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
        """Calculate overall Greeks score for a contract.
        
        Args:
            contract: OptionContract to score
            risk_level: Risk level for threshold comparison
            
        Returns:
            Score from 0.0 to 1.0, where 1.0 is best
        """
        acceptable, warnings, scores = GreeksAnalyzer.assess_greek_profile(contract, risk_level)
        
        # If no Greeks data, return perfect score
        if not scores:
            return 1.0
        
        # Average the individual scores
        if scores:
            avg_score = sum(scores.values()) / len(scores)
            # Invert so lower scores are better (closer to 0 is better)
            # Then convert to 0-1 scale where 1.0 is best
            return 1.0 - min(avg_score, 1.0)
        
        return 1.0


class PricingAnalyzer:
    """Analyzer for option pricing using Black-Scholes or other models."""

    def __init__(
        self,
        risk_free_rate: float = 0.05,
        dividend_yield: float = 0.0,
    ):
        """Initialize PricingAnalyzer.
        
        Args:
            risk_free_rate: Risk-free rate for pricing (default: 5%)
            dividend_yield: Dividend yield for pricing (default: 0%)
        """
        self.risk_free_rate = risk_free_rate
        self.dividend_yield = dividend_yield
        self.pricing_engine = None
        
        # Initialize QuantLib pricing engine if available
        if QUANTLIB_AVAILABLE:
            try:
                self.pricing_engine = QuantLibPricingEngine(
                    risk_free_rate=risk_free_rate,
                    dividend_yield=dividend_yield,
                )
            except Exception:
                # If QuantLib initialization fails, continue without it
                self.pricing_engine = None

    def calculate_theoretical_price(
        self,
        contract: OptionContract,
    ) -> Optional[float]:
        """Calculate theoretical price for a contract using Black-Scholes.
        
        Args:
            contract: OptionContract to price
            
        Returns:
            Theoretical price, or None if pricing engine unavailable or data missing
        """
        # Check required data
        if (
            contract.underlying_price is None
            or contract.strike is None
            or contract.implied_volatility is None
            or contract.days_to_expiration is None
        ):
            return None
        
        # Use QuantLib if available
        if self.pricing_engine:
            try:
                price = self.pricing_engine.price(
                    spot=contract.underlying_price,
                    strike=contract.strike,
                    volatility=contract.implied_volatility,
                    time_to_expiration=contract.days_to_expiration / 365.0,
                    option_type=contract.contract_type,
                )
                return price
            except Exception:
                return None
        
        return None

    def compare_prices(
        self,
        contract: OptionContract,
    ) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Compare market price with theoretical price.
        
        Args:
            contract: OptionContract to compare
            
        Returns:
            Tuple of (theoretical_price, difference, assessment)
            where assessment is "overpriced", "underpriced", or "fair"
        """
        # Check required data
        if contract.bid is None or contract.ask is None:
            return None, None, None
        
        # Calculate market mid-price
        market_mid = (contract.bid + contract.ask) / 2.0
        
        # Calculate theoretical price
        theoretical = self.calculate_theoretical_price(contract)
        if theoretical is None:
            return None, None, None
        
        # Calculate difference
        difference = market_mid - theoretical
        
        # Assess pricing
        # Consider 5% threshold for fair pricing
        threshold = theoretical * 0.05
        if difference > threshold:
            assessment = "overpriced"
        elif difference < -threshold:
            assessment = "underpriced"
        else:
            assessment = "fair"
        
        return theoretical, difference, assessment


class OptionsChainFilter:
    """Filter option contracts based on quality and risk criteria."""

    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize OptionsChainFilter.
        
        Args:
            risk_level: Risk level for filtering thresholds
        """
        self.risk_level = risk_level
        self.risk_config = get_risk_config(risk_level)

    def filter_expired(
        self,
        contract: OptionContract,
    ) -> FilteredContract:
        """Filter out expired contracts.
        
        Args:
            contract: OptionContract to filter
            
        Returns:
            FilteredContract with passed=False if expired
        """
        if contract.days_to_expiration is not None and contract.days_to_expiration <= 0:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.EXPIRED,
                rejection_message="Contract has expired",
            )
        
        return FilteredContract(
            contract=contract,
            passed=True,
            rejection_reason=RejectionReason.PASSED,
            rejection_message="",
        )

    def filter_missing_bid_ask(
        self,
        contract: OptionContract,
    ) -> FilteredContract:
        """Filter out contracts with missing bid/ask.
        
        Args:
            contract: OptionContract to filter
            
        Returns:
            FilteredContract with passed=False if bid/ask missing
        """
        if contract.bid is None or contract.ask is None:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.MISSING_BID_ASK,
                rejection_message="Missing bid or ask price",
            )
        
        return FilteredContract(
            contract=contract,
            passed=True,
            rejection_reason=RejectionReason.PASSED,
            rejection_message="",
        )

    def filter_illiquid(
        self,
        contract: OptionContract,
    ) -> FilteredContract:
        """Filter out illiquid contracts (low volume/open interest).
        
        Args:
            contract: OptionContract to filter
            
        Returns:
            FilteredContract with passed=False if illiquid
        """
        volume = contract.volume or 0
        open_interest = contract.open_interest or 0
        
        if volume < self.risk_config.min_volume:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.VOLUME_TOO_LOW,
                rejection_message=f"Volume {volume} below minimum {self.risk_config.min_volume}",
            )
        
        if open_interest < self.risk_config.min_open_interest:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.OPEN_INTEREST_TOO_LOW,
                rejection_message=f"Open interest {open_interest} below minimum {self.risk_config.min_open_interest}",
            )
        
        return FilteredContract(
            contract=contract,
            passed=True,
            rejection_reason=RejectionReason.PASSED,
            rejection_message="",
        )

    def filter_spread(
        self,
        contract: OptionContract,
    ) -> FilteredContract:
        """Filter out contracts with excessive bid-ask spread.
        
        Args:
            contract: OptionContract to filter
            
        Returns:
            FilteredContract with passed=False if spread too wide
        """
        if contract.bid is None or contract.ask is None:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.MISSING_BID_ASK,
                rejection_message="Missing bid or ask price",
            )
        
        mid_price = (contract.bid + contract.ask) / 2.0
        if mid_price == 0:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.BID_ASK_SPREAD_TOO_WIDE,
                rejection_message="Invalid bid/ask prices",
            )
        
        spread_pct = ((contract.ask - contract.bid) / mid_price) * 100.0
        
        if spread_pct > self.risk_config.max_bid_ask_spread_pct:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.BID_ASK_SPREAD_TOO_WIDE,
                rejection_message=f"Spread {spread_pct:.2f}% exceeds maximum {self.risk_config.max_bid_ask_spread_pct}%",
            )
        
        return FilteredContract(
            contract=contract,
            passed=True,
            rejection_reason=RejectionReason.PASSED,
            rejection_message="",
        )

    def filter_expiration_window(
        self,
        contract: OptionContract,
    ) -> FilteredContract:
        """Filter out contracts outside expiration window.
        
        Args:
            contract: OptionContract to filter
            
        Returns:
            FilteredContract with passed=False if outside window
        """
        if contract.days_to_expiration is None:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.OUTSIDE_EXPIRATION_WINDOW,
                rejection_message="Days to expiration unknown",
            )
        
        if contract.days_to_expiration < self.risk_config.min_days_to_expiration:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.OUTSIDE_EXPIRATION_WINDOW,
                rejection_message=f"DTE {contract.days_to_expiration} below minimum {self.risk_config.min_days_to_expiration}",
            )
        
        if contract.days_to_expiration > self.risk_config.max_days_to_expiration:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.OUTSIDE_EXPIRATION_WINDOW,
                rejection_message=f"DTE {contract.days_to_expiration} exceeds maximum {self.risk_config.max_days_to_expiration}",
            )
        
        return FilteredContract(
            contract=contract,
            passed=True,
            rejection_reason=RejectionReason.PASSED,
            rejection_message="",
        )

    def filter_all(
        self,
        contract: OptionContract,
    ) -> FilteredContract:
        """Apply all filters to a contract.
        
        Args:
            contract: OptionContract to filter
            
        Returns:
            FilteredContract with first rejection reason encountered
        """
        # Apply filters in order
        result = self.filter_expired(contract)
        if not result.passed:
            return result
        
        result = self.filter_missing_bid_ask(contract)
        if not result.passed:
            return result
        
        result = self.filter_illiquid(contract)
        if not result.passed:
            return result
        
        result = self.filter_spread(contract)
        if not result.passed:
            return result
        
        result = self.filter_expiration_window(contract)
        if not result.passed:
            return result
        
        return FilteredContract(
            contract=contract,
            passed=True,
            rejection_reason=RejectionReason.PASSED,
            rejection_message="",
        )


class OptionsService:
    """Main service for options analysis and scoring."""

    def __init__(
        self,
        data_provider: Optional[DataProvider] = None,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
    ):
        """Initialize OptionsService.
        
        Args:
            data_provider: Optional data provider (defaults to MockDataProvider)
            risk_level: Risk level for filtering and scoring
        """
        self.data_provider = data_provider or MockDataProvider()
        self.risk_level = risk_level
        self.filter = OptionsChainFilter(risk_level=risk_level)
        self.volatility_analyzer = VolatilityAnalyzer()
        self.greeks_analyzer = GreeksAnalyzer()
        self.pricing_analyzer = PricingAnalyzer()

    def filter_chain(
        self,
        contracts: List[OptionContract],
    ) -> List[FilteredContract]:
        """Filter a chain of option contracts.
        
        Args:
            contracts: List of OptionContract to filter
            
        Returns:
            List of FilteredContract with pass/fail status
        """
        return [self.filter.filter_all(contract) for contract in contracts]
