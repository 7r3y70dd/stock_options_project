"""Options service for Greeks analysis, risk guardrails, and pricing."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Tuple, Any
import math


class RiskLevel(Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EventType(Enum):
    """Event type classification."""
    EARNINGS = "earnings"
    DIVIDEND = "dividend"
    SPLIT = "split"
    OTHER = "other"


class RejectionReason(Enum):
    """Reason for rejecting an option contract."""
    INSUFFICIENT_LIQUIDITY = "insufficient_liquidity"
    EXCESSIVE_SPREAD = "excessive_spread"
    POOR_GREEKS = "poor_greeks"
    HIGH_RISK = "high_risk"
    UNFAVORABLE_PRICING = "unfavorable_pricing"
    NEAR_EXPIRATION = "near_expiration"
    LOW_VOLUME = "low_volume"
    OTHER = "other"


@dataclass
class OptionContract:
    """Represents an option contract with market and Greeks data."""
    symbol: str
    expiration: str
    strike: float
    contract_type: str  # 'call' or 'put'
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    implied_volatility: Optional[float] = None
    underlying_price: Optional[float] = None
    days_to_expiration: Optional[int] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None


@dataclass
class ScoredOption:
    """Option contract with associated score."""
    contract: OptionContract
    score: float
    components: Dict[str, float] = field(default_factory=dict)


@dataclass
class FilteredContract:
    """Filtered option contract with rejection reason if applicable."""
    contract: OptionContract
    accepted: bool
    rejection_reason: Optional[RejectionReason] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class RiskGuardrailResult:
    """Result of risk guardrail validation."""
    passed: bool
    violations: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)


class VolatilityAnalyzer:
    """Analyzes volatility metrics for options."""

    @staticmethod
    def calculate_historical_volatility(price_bars: List[Dict[str, float]]) -> Optional[float]:
        """Calculate historical volatility from price bars.
        
        Args:
            price_bars: List of dicts with 'close' price
            
        Returns:
            Historical volatility or None if insufficient data
        """
        if len(price_bars) < 2:
            return None
        
        closes = [bar["close"] for bar in price_bars]
        returns = []
        
        for i in range(1, len(closes)):
            ret = math.log(closes[i] / closes[i-1])
            returns.append(ret)
        
        if len(returns) < 1:
            return None
        
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        # Annualize (assuming daily data)
        hv = std_dev * math.sqrt(252)
        return hv

    @staticmethod
    def compare_volatilities(iv: float, hv: float) -> Tuple[float, str]:
        """Compare implied volatility to historical volatility.
        
        Args:
            iv: Implied volatility
            hv: Historical volatility
            
        Returns:
            Tuple of (ratio, context) where context is 'expensive', 'cheap', or 'fair'
        """
        if hv == 0:
            return 1.0, "fair"
        
        ratio = iv / hv
        
        if ratio > 1.15:
            context = "expensive"
        elif ratio < 0.85:
            context = "cheap"
        else:
            context = "fair"
        
        return ratio, context


class GreeksAnalyzer:
    """Analyzes Greeks for options."""

    @staticmethod
    def analyze_greeks(contract: OptionContract) -> Dict[str, float]:
        """Extract and normalize Greeks from contract.
        
        Args:
            contract: Option contract with Greeks data
            
        Returns:
            Dict with Greek values and absolute values
        """
        greeks = {}
        
        if contract.delta is not None:
            greeks["delta"] = contract.delta
            greeks["delta_abs"] = abs(contract.delta)
        
        if contract.gamma is not None:
            greeks["gamma"] = contract.gamma
            greeks["gamma_abs"] = abs(contract.gamma)
        
        if contract.theta is not None:
            greeks["theta"] = contract.theta
            greeks["theta_abs"] = abs(contract.theta)
        
        if contract.vega is not None:
            greeks["vega"] = contract.vega
            greeks["vega_abs"] = abs(contract.vega)
        
        if contract.rho is not None:
            greeks["rho"] = contract.rho
            greeks["rho_abs"] = abs(contract.rho)
        
        return greeks

    @staticmethod
    def assess_greek_profile(
        contract: OptionContract, risk_level: RiskLevel
    ) -> Tuple[bool, List[str], Dict[str, float]]:
        """Assess whether Greeks profile is acceptable for risk level.
        
        Args:
            contract: Option contract
            risk_level: Target risk level
            
        Returns:
            Tuple of (acceptable, warnings, scores)
        """
        warnings = []
        scores = {}
        
        # Define thresholds by risk level
        thresholds = {
            RiskLevel.LOW: {
                "delta": 0.30,
                "gamma": 0.05,
                "theta": -0.02,
                "vega": 0.10,
            },
            RiskLevel.MEDIUM: {
                "delta": 0.50,
                "gamma": 0.10,
                "theta": -0.05,
                "vega": 0.20,
            },
            RiskLevel.HIGH: {
                "delta": 0.70,
                "gamma": 0.15,
                "theta": -0.10,
                "vega": 0.30,
            },
        }
        
        threshold = thresholds.get(risk_level, thresholds[RiskLevel.MEDIUM])
        acceptable = True
        
        # Check delta
        if contract.delta is not None:
            delta_abs = abs(contract.delta)
            scores["delta_score"] = min(1.0, 1.0 - (delta_abs / threshold["delta"]))
            if delta_abs > threshold["delta"]:
                acceptable = False
                warnings.append(
                    f"Delta {contract.delta} exceeds {risk_level.value} risk threshold. "
                    f"High directional exposure."
                )
        else:
            scores["delta_score"] = 1.0
        
        # Check gamma
        if contract.gamma is not None:
            gamma_abs = abs(contract.gamma)
            scores["gamma_score"] = min(1.0, 1.0 - (gamma_abs / threshold["gamma"]))
            if gamma_abs > threshold["gamma"]:
                acceptable = False
                warnings.append(
                    f"Gamma {contract.gamma} exceeds {risk_level.value} risk threshold. "
                    f"High delta acceleration risk."
                )
        else:
            scores["gamma_score"] = 1.0
        
        # Check theta
        if contract.theta is not None:
            theta_abs = abs(contract.theta)
            scores["theta_score"] = min(1.0, 1.0 - (theta_abs / abs(threshold["theta"])))
            if theta_abs > abs(threshold["theta"]):
                acceptable = False
                warnings.append(
                    f"Theta {contract.theta} exceeds {risk_level.value} risk threshold. "
                    f"High time decay risk."
                )
        else:
            scores["theta_score"] = 1.0
        
        # Check vega
        if contract.vega is not None:
            vega_abs = abs(contract.vega)
            scores["vega_score"] = min(1.0, 1.0 - (vega_abs / threshold["vega"]))
            if vega_abs > threshold["vega"]:
                acceptable = False
                warnings.append(
                    f"Vega {contract.vega} exceeds {risk_level.value} risk threshold. "
                    f"High volatility risk."
                )
        else:
            scores["vega_score"] = 1.0
        
        return acceptable, warnings, scores

    @staticmethod
    def calculate_greeks_score(contract: OptionContract, risk_level: RiskLevel) -> float:
        """Calculate overall Greeks score for contract.
        
        Args:
            contract: Option contract
            risk_level: Target risk level
            
        Returns:
            Score between 0.0 and 1.0
        """
        acceptable, _, scores = GreeksAnalyzer.assess_greek_profile(contract, risk_level)
        
        if not scores:
            # No Greeks data available
            return 1.0
        
        # Average the component scores
        avg_score = sum(scores.values()) / len(scores)
        return max(0.0, min(1.0, avg_score))


class PricingAnalyzer:
    """Analyzes option pricing."""

    def __init__(self, risk_free_rate: float = 0.05, dividend_yield: float = 0.0):
        """Initialize pricing analyzer.
        
        Args:
            risk_free_rate: Risk-free rate for pricing
            dividend_yield: Dividend yield for underlying
        """
        self.risk_free_rate = risk_free_rate
        self.dividend_yield = dividend_yield
        self.pricing_engine = None
        
        # Try to import QuantLib for pricing
        try:
            import QuantLib as ql
            self.ql = ql
            self.pricing_engine = True
        except ImportError:
            self.ql = None
            self.pricing_engine = None

    def calculate_theoretical_price(self, contract: OptionContract) -> Optional[float]:
        """Calculate theoretical option price using Black-Scholes.
        
        Args:
            contract: Option contract
            
        Returns:
            Theoretical price or None if calculation not possible
        """
        # Check required data
        if (
            contract.underlying_price is None
            or contract.implied_volatility is None
            or contract.days_to_expiration is None
        ):
            return None
        
        # If QuantLib available, use it
        if self.pricing_engine and self.ql:
            try:
                return self._calculate_with_quantlib(contract)
            except Exception:
                return None
        
        # Fallback to Black-Scholes
        return self._calculate_black_scholes(contract)

    def _calculate_black_scholes(self, contract: OptionContract) -> Optional[float]:
        """Calculate price using Black-Scholes formula."""
        S = contract.underlying_price
        K = contract.strike
        T = contract.days_to_expiration / 365.0
        r = self.risk_free_rate
        sigma = contract.implied_volatility
        q = self.dividend_yield
        
        if T <= 0 or sigma <= 0:
            return None
        
        try:
            d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            
            from math import exp, sqrt
            from scipy.stats import norm
            
            if contract.contract_type.lower() == "call":
                price = S * exp(-q * T) * norm.cdf(d1) - K * exp(-r * T) * norm.cdf(d2)
            else:
                price = K * exp(-r * T) * norm.cdf(-d2) - S * exp(-q * T) * norm.cdf(-d1)
            
            return max(0.0, price)
        except Exception:
            return None

    def _calculate_with_quantlib(self, contract: OptionContract) -> Optional[float]:
        """Calculate price using QuantLib."""
        try:
            ql = self.ql
            
            # Set up dates
            today = ql.Date.todaysDate()
            expiry_date = ql.Date(1, 1, 2025)  # Placeholder
            
            # Create option
            option_type = ql.Option.Call if contract.contract_type.lower() == "call" else ql.Option.Put
            payoff = ql.PlainVanillaPayoff(option_type, contract.strike)
            exercise = ql.EuropeanExercise(expiry_date)
            option = ql.VanillaOption(payoff, exercise)
            
            # Set up market data
            spot = ql.SimpleQuote(contract.underlying_price)
            flat_ts = ql.FlatForward(today, self.risk_free_rate, ql.Actual365Fixed())
            dividend_ts = ql.FlatForward(today, self.dividend_yield, ql.Actual365Fixed())
            flat_vol = ql.BlackConstantVol(today, ql.TARGET(), contract.implied_volatility, ql.Actual365Fixed())
            
            # Create process and engine
            process = ql.BlackScholesMertonProcess(spot, dividend_ts, flat_ts, flat_vol)
            engine = ql.AnalyticEuropeanEngine(process)
            option.setPricingEngine(engine)
            
            return option.NPV()
        except Exception:
            return None

    def compare_prices(self, contract: OptionContract) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Compare market price to theoretical price.
        
        Args:
            contract: Option contract
            
        Returns:
            Tuple of (theoretical_price, difference, assessment)
        """
        if contract.bid is None or contract.ask is None:
            return None, None, None
        
        market_price = (contract.bid + contract.ask) / 2.0
        theoretical_price = self.calculate_theoretical_price(contract)
        
        if theoretical_price is None:
            return None, None, None
        
        difference = market_price - theoretical_price
        
        if difference > theoretical_price * 0.05:
            assessment = "overpriced"
        elif difference < -theoretical_price * 0.05:
            assessment = "underpriced"
        else:
            assessment = "fair"
        
        return theoretical_price, difference, assessment


class OptionsChainFilter:
    """Filters option chains based on criteria."""

    @staticmethod
    def filter_by_liquidity(
        contracts: List[OptionContract],
        min_volume: int = 10,
        min_open_interest: int = 50,
    ) -> List[FilteredContract]:
        """Filter contracts by liquidity metrics.
        
        Args:
            contracts: List of option contracts
            min_volume: Minimum volume threshold
            min_open_interest: Minimum open interest threshold
            
        Returns:
            List of filtered contracts
        """
        filtered = []
        for contract in contracts:
            volume = contract.volume or 0
            oi = contract.open_interest or 0
            
            if volume >= min_volume and oi >= min_open_interest:
                filtered.append(FilteredContract(contract=contract, accepted=True))
            else:
                reason = RejectionReason.LOW_VOLUME if volume < min_volume else RejectionReason.INSUFFICIENT_LIQUIDITY
                filtered.append(
                    FilteredContract(
                        contract=contract,
                        accepted=False,
                        rejection_reason=reason,
                        warnings=[f"Insufficient liquidity: volume={volume}, OI={oi}"],
                    )
                )
        
        return filtered

    @staticmethod
    def filter_by_spread(
        contracts: List[OptionContract],
        max_spread_percent: float = 5.0,
    ) -> List[FilteredContract]:
        """Filter contracts by bid-ask spread.
        
        Args:
            contracts: List of option contracts
            max_spread_percent: Maximum spread as percentage of mid-price
            
        Returns:
            List of filtered contracts
        """
        filtered = []
        for contract in contracts:
            if contract.bid is None or contract.ask is None:
                filtered.append(
                    FilteredContract(
                        contract=contract,
                        accepted=False,
                        rejection_reason=RejectionReason.EXCESSIVE_SPREAD,
                        warnings=["Missing bid/ask data"],
                    )
                )
                continue
            
            mid = (contract.bid + contract.ask) / 2.0
            spread = contract.ask - contract.bid
            spread_pct = (spread / mid * 100) if mid > 0 else 100
            
            if spread_pct <= max_spread_percent:
                filtered.append(FilteredContract(contract=contract, accepted=True))
            else:
                filtered.append(
                    FilteredContract(
                        contract=contract,
                        accepted=False,
                        rejection_reason=RejectionReason.EXCESSIVE_SPREAD,
                        warnings=[f"Spread {spread_pct:.2f}% exceeds {max_spread_percent}%"],
                    )
                )
        
        return filtered

    @staticmethod
    def filter_by_expiration(
        contracts: List[OptionContract],
        min_days: int = 7,
        max_days: int = 60,
    ) -> List[FilteredContract]:
        """Filter contracts by days to expiration.
        
        Args:
            contracts: List of option contracts
            min_days: Minimum days to expiration
            max_days: Maximum days to expiration
            
        Returns:
            List of filtered contracts
        """
        filtered = []
        for contract in contracts:
            dte = contract.days_to_expiration or 0
            
            if min_days <= dte <= max_days:
                filtered.append(FilteredContract(contract=contract, accepted=True))
            else:
                reason = RejectionReason.NEAR_EXPIRATION if dte < min_days else RejectionReason.OTHER
                filtered.append(
                    FilteredContract(
                        contract=contract,
                        accepted=False,
                        rejection_reason=reason,
                        warnings=[f"Days to expiration {dte} outside range [{min_days}, {max_days}]"],
                    )
                )
        
        return filtered


class EventRiskAnalyzer:
    """Analyzes event-related risks for options."""

    @staticmethod
    def assess_event_risk(
        contract: OptionContract,
        event_type: EventType,
        days_to_event: int,
    ) -> Tuple[bool, List[str]]:
        """Assess risk from upcoming events.
        
        Args:
            contract: Option contract
            event_type: Type of event
            days_to_event: Days until event
            
        Returns:
            Tuple of (acceptable, warnings)
        """
        warnings = []
        acceptable = True
        
        # Events within 7 days are risky
        if days_to_event <= 7:
            acceptable = False
            warnings.append(
                f"{event_type.value.capitalize()} event in {days_to_event} days. "
                f"High volatility risk."
            )
        elif days_to_event <= 14:
            warnings.append(
                f"{event_type.value.capitalize()} event in {days_to_event} days. "
                f"Moderate volatility risk."
            )
        
        return acceptable, warnings


class RiskEngine:
    """Engine for comprehensive risk analysis."""

    def __init__(self):
        """Initialize risk engine."""
        self.volatility_analyzer = VolatilityAnalyzer()
        self.greeks_analyzer = GreeksAnalyzer()
        self.pricing_analyzer = PricingAnalyzer()
        self.event_analyzer = EventRiskAnalyzer()

    def validate_contract(
        self,
        contract: OptionContract,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
    ) -> RiskGuardrailResult:
        """Validate contract against risk guardrails.
        
        Args:
            contract: Option contract to validate
            risk_level: Target risk level
            
        Returns:
            Risk guardrail result
        """
        violations = []
        scores = {}
        
        # Check Greeks
        greeks_ok, greeks_warnings, greeks_scores = self.greeks_analyzer.assess_greek_profile(
            contract, risk_level
        )
        violations.extend(greeks_warnings)
        scores.update(greeks_scores)
        
        # Check liquidity
        if contract.volume is not None and contract.volume < 10:
            violations.append("Insufficient volume")
        
        if contract.open_interest is not None and contract.open_interest < 50:
            violations.append("Insufficient open interest")
        
        # Check spread
        if contract.bid is not None and contract.ask is not None:
            mid = (contract.bid + contract.ask) / 2.0
            spread_pct = ((contract.ask - contract.bid) / mid * 100) if mid > 0 else 100
            if spread_pct > 5.0:
                violations.append(f"Bid-ask spread {spread_pct:.2f}% too wide")
        
        # Check expiration
        if contract.days_to_expiration is not None:
            if contract.days_to_expiration < 7:
                violations.append("Too close to expiration")
            elif contract.days_to_expiration > 90:
                violations.append("Too far from expiration")
        
        passed = len(violations) == 0
        return RiskGuardrailResult(passed=passed, violations=violations, scores=scores)
