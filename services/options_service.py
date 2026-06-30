"""Options service for analyzing and filtering option contracts."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime, timedelta
import math


class RiskLevel(Enum):
    """Risk level for options filtering and analysis."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RejectionReason(Enum):
    """Reasons for rejecting an option contract."""
    EXPIRED = "expired"
    MISSING_BID_ASK = "missing_bid_ask"
    ILLIQUID = "illiquid"
    EXCESSIVE_SPREAD = "excessive_spread"
    OUTSIDE_EXPIRATION_WINDOW = "outside_expiration_window"
    MAX_LOSS_EXCEEDED = "max_loss_exceeded"
    MAX_CONTRACTS_EXCEEDED = "max_contracts_exceeded"
    DELTA_OUT_OF_RANGE = "delta_out_of_range"
    VOLATILITY_OUT_OF_RANGE = "volatility_out_of_range"


@dataclass
class OptionContract:
    """Represents a single option contract."""
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
    last_price: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None


@dataclass
class ScoredOption:
    """Represents an option contract with analysis scores."""
    contract: OptionContract
    greeks_score: float
    volatility_score: float
    pricing_score: float
    overall_score: float
    analysis_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FilteredContract:
    """Represents a filtered option contract with rejection reason if applicable."""
    contract: Optional[OptionContract] = None
    accepted: bool = False
    rejection_reason: Optional[RejectionReason] = None
    rejection_message: Optional[str] = None


class VolatilityAnalyzer:
    """Analyzes volatility metrics for option contracts."""

    @staticmethod
    def calculate_historical_volatility(price_bars: List[Dict[str, float]]) -> Optional[float]:
        """Calculate historical volatility from price bars.
        
        Args:
            price_bars: List of dicts with 'close' price
            
        Returns:
            Historical volatility as a decimal (e.g., 0.25 for 25%)
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
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        # Annualize (assuming daily returns)
        hv = std_dev * math.sqrt(252)
        return hv

    @staticmethod
    def compare_volatilities(iv: float, hv: Optional[float]) -> Tuple[Optional[float], Optional[str]]:
        """Compare implied volatility to historical volatility.
        
        Args:
            iv: Implied volatility
            hv: Historical volatility
            
        Returns:
            Tuple of (ratio, context) where context is 'expensive', 'fair', or 'cheap'
        """
        if hv is None or hv == 0:
            return None, None
        
        ratio = iv / hv
        
        if ratio > 1.15:
            context = "expensive"
        elif ratio < 0.85:
            context = "cheap"
        else:
            context = "fair"
        
        return ratio, context

    @staticmethod
    def assess_volatility_level(contract: OptionContract, risk_level: RiskLevel) -> Tuple[bool, List[str]]:
        """Assess if contract volatility is acceptable for risk level.
        
        Args:
            contract: Option contract to assess
            risk_level: Risk level threshold
            
        Returns:
            Tuple of (acceptable, warnings)
        """
        warnings = []
        acceptable = True
        
        if contract.implied_volatility is None:
            return acceptable, warnings
        
        # Define IV thresholds by risk level
        iv_thresholds = {
            RiskLevel.LOW: 0.30,
            RiskLevel.MEDIUM: 0.50,
            RiskLevel.HIGH: 1.0,
        }
        
        threshold = iv_thresholds.get(risk_level, 0.50)
        
        if contract.implied_volatility > threshold:
            acceptable = False
            warnings.append(f"IV {contract.implied_volatility:.2%} exceeds {risk_level.value} threshold of {threshold:.2%}")
        
        return acceptable, warnings


class GreeksAnalyzer:
    """Analyzes Greeks for option contracts."""

    @staticmethod
    def analyze_greeks(contract: OptionContract) -> Dict[str, float]:
        """Extract and normalize Greeks from contract.
        
        Args:
            contract: Option contract
            
        Returns:
            Dict of Greek values with absolute values
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
        
        return greeks

    @staticmethod
    def assess_greek_profile(contract: OptionContract, risk_level: RiskLevel) -> Tuple[bool, List[str], Dict[str, float]]:
        """Assess if Greek profile is acceptable for risk level.
        
        Args:
            contract: Option contract to assess
            risk_level: Risk level threshold
            
        Returns:
            Tuple of (acceptable, warnings, scores)
        """
        warnings = []
        scores = {}
        acceptable = True
        
        # Define Greek thresholds by risk level
        thresholds = {
            RiskLevel.LOW: {
                "delta": 0.30,
                "gamma": 0.05,
                "theta": -0.02,
                "vega": 0.10,
            },
            RiskLevel.MEDIUM: {
                "delta": 0.60,
                "gamma": 0.10,
                "theta": -0.05,
                "vega": 0.20,
            },
            RiskLevel.HIGH: {
                "delta": 1.0,
                "gamma": 1.0,
                "theta": -1.0,
                "vega": 1.0,
            },
        }
        
        threshold_set = thresholds.get(risk_level, thresholds[RiskLevel.MEDIUM])
        
        # Check delta
        if contract.delta is not None:
            delta_abs = abs(contract.delta)
            scores["delta_score"] = 1.0 - min(delta_abs / threshold_set["delta"], 1.0)
            if delta_abs > threshold_set["delta"]:
                acceptable = False
                warnings.append(f"Delta {contract.delta:.2f} exceeds {risk_level.value} threshold - high directional exposure")
        else:
            scores["delta_score"] = 1.0
        
        # Check gamma
        if contract.gamma is not None:
            gamma_abs = abs(contract.gamma)
            scores["gamma_score"] = 1.0 - min(gamma_abs / threshold_set["gamma"], 1.0)
            if gamma_abs > threshold_set["gamma"]:
                acceptable = False
                warnings.append(f"Gamma {contract.gamma:.4f} exceeds {risk_level.value} threshold")
        else:
            scores["gamma_score"] = 1.0
        
        # Check theta
        if contract.theta is not None:
            theta_abs = abs(contract.theta)
            scores["theta_score"] = 1.0 - min(theta_abs / abs(threshold_set["theta"]), 1.0)
            if theta_abs > abs(threshold_set["theta"]):
                acceptable = False
                warnings.append(f"Theta {contract.theta:.4f} exceeds {risk_level.value} threshold")
        else:
            scores["theta_score"] = 1.0
        
        # Check vega
        if contract.vega is not None:
            vega_abs = abs(contract.vega)
            scores["vega_score"] = 1.0 - min(vega_abs / threshold_set["vega"], 1.0)
            if vega_abs > threshold_set["vega"]:
                acceptable = False
                warnings.append(f"Vega {contract.vega:.4f} exceeds {risk_level.value} threshold")
        else:
            scores["vega_score"] = 1.0
        
        return acceptable, warnings, scores

    @staticmethod
    def calculate_greeks_score(contract: OptionContract, risk_level: RiskLevel) -> float:
        """Calculate overall Greeks score for a contract.
        
        Args:
            contract: Option contract
            risk_level: Risk level for assessment
            
        Returns:
            Score between 0.0 and 1.0
        """
        acceptable, warnings, scores = GreeksAnalyzer.assess_greek_profile(contract, risk_level)
        
        if not scores:
            # No Greeks data available
            return 1.0
        
        # Average the individual Greek scores
        avg_score = sum(scores.values()) / len(scores)
        
        # Penalize if not acceptable
        if not acceptable:
            avg_score *= 0.7
        
        return max(0.0, min(1.0, avg_score))


class PricingAnalyzer:
    """Analyzes pricing for option contracts."""

    def __init__(self, risk_free_rate: float = 0.05, dividend_yield: float = 0.0):
        """Initialize PricingAnalyzer.
        
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
            self.pricing_engine = "quantlib"
        except ImportError:
            self.ql = None
            self.pricing_engine = None

    def calculate_theoretical_price(self, contract: OptionContract) -> Optional[float]:
        """Calculate theoretical option price using Black-Scholes or QuantLib.
        
        Args:
            contract: Option contract
            
        Returns:
            Theoretical price or None if calculation not possible
        """
        # Check required data
        if (contract.underlying_price is None or 
            contract.implied_volatility is None or
            contract.days_to_expiration is None):
            return None
        
        if self.pricing_engine == "quantlib" and self.ql is not None:
            return self._calculate_price_quantlib(contract)
        else:
            return self._calculate_price_black_scholes(contract)

    def _calculate_price_black_scholes(self, contract: OptionContract) -> Optional[float]:
        """Calculate price using Black-Scholes formula."""
        try:
            S = contract.underlying_price
            K = contract.strike
            T = contract.days_to_expiration / 365.0
            r = self.risk_free_rate
            sigma = contract.implied_volatility
            q = self.dividend_yield
            
            if T <= 0 or sigma <= 0:
                return None
            
            d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            
            from math import exp, sqrt
            from scipy.stats import norm
            
            N_d1 = norm.cdf(d1)
            N_d2 = norm.cdf(d2)
            
            if contract.contract_type.lower() == "call":
                price = S * exp(-q * T) * N_d1 - K * exp(-r * T) * N_d2
            else:  # put
                N_minus_d1 = norm.cdf(-d1)
                N_minus_d2 = norm.cdf(-d2)
                price = K * exp(-r * T) * N_minus_d2 - S * exp(-q * T) * N_minus_d1
            
            return price
        except Exception:
            return None

    def _calculate_price_quantlib(self, contract: OptionContract) -> Optional[float]:
        """Calculate price using QuantLib."""
        try:
            ql = self.ql
            
            # Set up dates
            today = ql.Date.todaysDate()
            expiration_date = today + int(contract.days_to_expiration)
            
            # Create option
            option_type = ql.Option.Call if contract.contract_type.lower() == "call" else ql.Option.Put
            payoff = ql.PlainVanillaPayoff(option_type, contract.strike)
            exercise = ql.EuropeanExercise(expiration_date)
            option = ql.VanillaOption(payoff, exercise)
            
            # Set up market data
            spot_handle = ql.QuoteHandle(ql.SimpleQuote(contract.underlying_price))
            flat_ts = ql.YieldTermStructureHandle(ql.FlatForward(today, self.risk_free_rate, ql.Actual365Fixed()))
            dividend_ts = ql.YieldTermStructureHandle(ql.FlatForward(today, self.dividend_yield, ql.Actual365Fixed()))
            flat_vol = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, ql.NullCalendar(), contract.implied_volatility, ql.Actual365Fixed()))
            
            # Create process and engine
            process = ql.BlackScholesMertonProcess(spot_handle, dividend_ts, flat_ts, flat_vol)
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
            where assessment is 'overpriced', 'underpriced', or 'fair'
        """
        if contract.bid is None or contract.ask is None:
            return None, None, None
        
        theoretical_price = self.calculate_theoretical_price(contract)
        if theoretical_price is None:
            return None, None, None
        
        market_price = (contract.bid + contract.ask) / 2.0
        difference = market_price - theoretical_price
        
        # Assess if overpriced or underpriced (with 5% tolerance)
        tolerance = theoretical_price * 0.05
        
        if difference > tolerance:
            assessment = "overpriced"
        elif difference < -tolerance:
            assessment = "underpriced"
        else:
            assessment = "fair"
        
        return theoretical_price, difference, assessment


class OptionsChainFilter:
    """Filters option contracts based on quality and risk criteria."""

    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize OptionsChainFilter.
        
        Args:
            risk_level: Risk level for filtering
        """
        self.risk_level = risk_level

    def get_risk_config(self) -> Dict[str, Any]:
        """Get filtering configuration for risk level.
        
        Returns:
            Dict with filtering thresholds
        """
        configs = {
            RiskLevel.LOW: {
                "min_volume": 100,
                "min_open_interest": 500,
                "max_spread_percent": 0.05,
                "min_days_to_expiration": 7,
                "max_days_to_expiration": 60,
            },
            RiskLevel.MEDIUM: {
                "min_volume": 50,
                "min_open_interest": 200,
                "max_spread_percent": 0.10,
                "min_days_to_expiration": 3,
                "max_days_to_expiration": 90,
            },
            RiskLevel.HIGH: {
                "min_volume": 10,
                "min_open_interest": 50,
                "max_spread_percent": 0.20,
                "min_days_to_expiration": 1,
                "max_days_to_expiration": 180,
            },
        }
        return configs.get(self.risk_level, configs[RiskLevel.MEDIUM])

    def filter_expired(self, contract: OptionContract) -> FilteredContract:
        """Filter out expired contracts.
        
        Args:
            contract: Option contract
            
        Returns:
            FilteredContract with acceptance status
        """
        if contract.days_to_expiration is not None and contract.days_to_expiration <= 0:
            return FilteredContract(
                contract=contract,
                accepted=False,
                rejection_reason=RejectionReason.EXPIRED,
                rejection_message="Contract has expired"
            )
        return FilteredContract(contract=contract, accepted=True)

    def filter_missing_bid_ask(self, contract: OptionContract) -> FilteredContract:
        """Filter out contracts with missing bid/ask.
        
        Args:
            contract: Option contract
            
        Returns:
            FilteredContract with acceptance status
        """
        if contract.bid is None or contract.ask is None:
            return FilteredContract(
                contract=contract,
                accepted=False,
                rejection_reason=RejectionReason.MISSING_BID_ASK,
                rejection_message="Missing bid or ask price"
            )
        return FilteredContract(contract=contract, accepted=True)

    def filter_illiquid(self, contract: OptionContract) -> FilteredContract:
        """Filter out illiquid contracts.
        
        Args:
            contract: Option contract
            
        Returns:
            FilteredContract with acceptance status
        """
        config = self.get_risk_config()
        
        volume = contract.volume or 0
        open_interest = contract.open_interest or 0
        
        if volume < config["min_volume"] or open_interest < config["min_open_interest"]:
            return FilteredContract(
                contract=contract,
                accepted=False,
                rejection_reason=RejectionReason.ILLIQUID,
                rejection_message=f"Insufficient liquidity: volume={volume}, OI={open_interest}"
            )
        return FilteredContract(contract=contract, accepted=True)

    def filter_excessive_spread(self, contract: OptionContract) -> FilteredContract:
        """Filter out contracts with excessive bid-ask spread.
        
        Args:
            contract: Option contract
            
        Returns:
            FilteredContract with acceptance status
        """
        if contract.bid is None or contract.ask is None:
            return FilteredContract(contract=contract, accepted=True)
        
        config = self.get_risk_config()
        mid_price = (contract.bid + contract.ask) / 2.0
        
        if mid_price > 0:
            spread_percent = (contract.ask - contract.bid) / mid_price
            if spread_percent > config["max_spread_percent"]:
                return FilteredContract(
                    contract=contract,
                    accepted=False,
                    rejection_reason=RejectionReason.EXCESSIVE_SPREAD,
                    rejection_message=f"Spread {spread_percent:.2%} exceeds threshold"
                )
        
        return FilteredContract(contract=contract, accepted=True)

    def filter_expiration_window(self, contract: OptionContract) -> FilteredContract:
        """Filter by expiration window.
        
        Args:
            contract: Option contract
            
        Returns:
            FilteredContract with acceptance status
        """
        config = self.get_risk_config()
        dte = contract.days_to_expiration or 0
        
        if dte < config["min_days_to_expiration"] or dte > config["max_days_to_expiration"]:
            return FilteredContract(
                contract=contract,
                accepted=False,
                rejection_reason=RejectionReason.OUTSIDE_EXPIRATION_WINDOW,
                rejection_message=f"DTE {dte} outside window [{config['min_days_to_expiration']}, {config['max_days_to_expiration']}]"
            )
        return FilteredContract(contract=contract, accepted=True)

    def filter_chain(self, contracts: List[OptionContract]) -> List[FilteredContract]:
        """Filter a chain of contracts.
        
        Args:
            contracts: List of option contracts
            
        Returns:
            List of FilteredContract objects
        """
        filtered = []
        
        for contract in contracts:
            # Apply all filters
            result = self.filter_expired(contract)
            if not result.accepted:
                filtered.append(result)
                continue
            
            result = self.filter_missing_bid_ask(contract)
            if not result.accepted:
                filtered.append(result)
                continue
            
            result = self.filter_illiquid(contract)
            if not result.accepted:
                filtered.append(result)
                continue
            
            result = self.filter_excessive_spread(contract)
            if not result.accepted:
                filtered.append(result)
                continue
            
            result = self.filter_expiration_window(contract)
            if not result.accepted:
                filtered.append(result)
                continue
            
            # All filters passed
            filtered.append(FilteredContract(contract=contract, accepted=True))
        
        return filtered


class OptionsService:
    """Main service for options analysis and filtering."""

    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize OptionsService.
        
        Args:
            risk_level: Risk level for analysis
        """
        self.risk_level = risk_level
        self.filter = OptionsChainFilter(risk_level)
        self.volatility_analyzer = VolatilityAnalyzer()
        self.greeks_analyzer = GreeksAnalyzer()
        self.pricing_analyzer = PricingAnalyzer()

    def analyze_contract(self, contract: OptionContract) -> ScoredOption:
        """Analyze a single contract and return scores.
        
        Args:
            contract: Option contract to analyze
            
        Returns:
            ScoredOption with analysis results
        """
        greeks_score = self.greeks_analyzer.calculate_greeks_score(contract, self.risk_level)
        
        # Volatility score (placeholder)
        volatility_score = 0.5
        if contract.implied_volatility is not None:
            acceptable, _ = VolatilityAnalyzer.assess_volatility_level(contract, self.risk_level)
            volatility_score = 1.0 if acceptable else 0.5
        
        # Pricing score (placeholder)
        pricing_score = 0.5
        theoretical_price, difference, assessment = self.pricing_analyzer.compare_prices(contract)
        if assessment == "fair":
            pricing_score = 1.0
        elif assessment == "underpriced":
            pricing_score = 0.8
        elif assessment == "overpriced":
            pricing_score = 0.3
        
        overall_score = (greeks_score + volatility_score + pricing_score) / 3.0
        
        return ScoredOption(
            contract=contract,
            greeks_score=greeks_score,
            volatility_score=volatility_score,
            pricing_score=pricing_score,
            overall_score=overall_score,
            analysis_details={
                "theoretical_price": theoretical_price,
                "price_difference": difference,
                "price_assessment": assessment,
            }
        )
