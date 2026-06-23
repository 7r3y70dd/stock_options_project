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
    liquidity_score: float = 0.0  # Liquidity score 0-100, default 0.0


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
            Greeks score from 0.0 to 1.0 (higher is better)
        """
        acceptable, warnings, scores = GreeksAnalyzer.assess_greek_profile(contract, risk_level)
        
        if not scores:
            return 0.5  # Default score if no Greeks available
        
        # Average the individual scores
        avg_score = sum(scores.values()) / len(scores)
        
        # Penalize if not acceptable
        if not acceptable:
            avg_score *= 0.7  # 30% penalty for exceeding thresholds
        
        return min(avg_score, 1.0)


class PricingAnalyzer:
    """Analyzer for option pricing and theoretical value."""

    @staticmethod
    def calculate_theoretical_price(
        contract: OptionContract,
        risk_free_rate: float = 0.05,
    ) -> Optional[float]:
        """Calculate theoretical price using Black-Scholes model.
        
        Args:
            contract: OptionContract to price
            risk_free_rate: Risk-free interest rate (default: 5%)
            
        Returns:
            Theoretical price, or None if insufficient data
        """
        if not QUANTLIB_AVAILABLE:
            return None
        
        if contract.underlying_price is None or contract.implied_volatility is None:
            return None
        
        try:
            engine = QuantLibPricingEngine()
            price = engine.price_option(
                spot_price=contract.underlying_price,
                strike_price=contract.strike,
                time_to_expiration=contract.days_to_expiration / 365.0 if contract.days_to_expiration else 0.1,
                volatility=contract.implied_volatility,
                risk_free_rate=risk_free_rate,
                option_type="call" if contract.contract_type.lower() == "call" else "put",
            )
            return price
        except Exception:
            return None

    @staticmethod
    def compare_prices(
        contract: OptionContract,
        theoretical_price: Optional[float] = None,
    ) -> Tuple[Optional[float], Optional[str]]:
        """Compare market price with theoretical price.
        
        Args:
            contract: OptionContract to analyze
            theoretical_price: Optional pre-calculated theoretical price
            
        Returns:
            Tuple of (pricing_difference, assessment) where assessment is "overpriced", "underpriced", or "fair"
        """
        if contract.bid is None or contract.ask is None:
            return None, None
        
        market_mid = (contract.bid + contract.ask) / 2
        
        if theoretical_price is None:
            theoretical_price = PricingAnalyzer.calculate_theoretical_price(contract)
        
        if theoretical_price is None:
            return None, None
        
        difference = market_mid - theoretical_price
        
        # Determine if overpriced or underpriced (threshold: 5% of theoretical price)
        threshold = theoretical_price * 0.05
        
        if difference > threshold:
            assessment = "overpriced"
        elif difference < -threshold:
            assessment = "underpriced"
        else:
            assessment = "fair"
        
        return difference, assessment
