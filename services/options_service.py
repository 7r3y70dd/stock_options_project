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


class EventType(Enum):
    """Types of events that can increase options risk."""
    EARNINGS = "earnings"
    FDA_DECISION = "fda_decision"
    LAWSUIT = "lawsuit"
    M_AND_A = "m_and_a"
    SEC_INVESTIGATION = "sec_investigation"
    ANALYST_UPGRADE = "analyst_upgrade"
    ANALYST_DOWNGRADE = "analyst_downgrade"
    MACRO_EVENT = "macro_event"


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
    MAX_DAILY_LOSS_EXCEEDED = "max_daily_loss_exceeded"
    MAX_OPEN_POSITIONS_EXCEEDED = "max_open_positions_exceeded"
    BID_ASK_SPREAD_TOO_WIDE = "bid_ask_spread_too_wide"
    VOLUME_TOO_LOW = "volume_too_low"
    OPEN_INTEREST_TOO_LOW = "open_interest_too_low"
    EARNINGS_WINDOW_RESTRICTED = "earnings_window_restricted"
    LIVE_TRADING_NOT_APPROVED = "live_trading_not_approved"
    EVENT_RISK_TOO_HIGH = "event_risk_too_high"


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
    earnings_date: Optional[str] = None
    event_risks: Optional[List[Tuple[EventType, str]]] = None  # List of (event_type, description)


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


@dataclass
class RiskGuardrailResult:
    """Result of a risk guardrail validation."""
    passed: bool
    reason: Optional[RejectionReason] = None
    message: str = ""


class EventRiskAnalyzer:
    """Analyzes event-based risks for option contracts."""

    @staticmethod
    def detect_events(
        symbol: str,
        contract: OptionContract,
        news_articles: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Tuple[EventType, str]]:
        """Detect high-risk events for a symbol.
        
        Args:
            symbol: Stock symbol
            contract: Option contract
            news_articles: Optional list of news articles with metadata
            
        Returns:
            List of (event_type, description) tuples
        """
        events = []
        
        # Check for earnings
        if contract.earnings_date:
            events.append((EventType.EARNINGS, f"Earnings on {contract.earnings_date}"))
        
        # Analyze news articles for event keywords
        if news_articles:
            for article in news_articles:
                title = article.get("title", "").lower()
                description = article.get("description", "").lower()
                text = f"{title} {description}"
                
                # FDA decision detection
                if any(keyword in text for keyword in ["fda", "approval", "rejection", "clinical trial"]):
                    events.append((EventType.FDA_DECISION, f"FDA-related news: {article.get('title', 'N/A')}"))
                
                # Lawsuit detection
                if any(keyword in text for keyword in ["lawsuit", "sued", "litigation", "legal action", "court"]):
                    events.append((EventType.LAWSUIT, f"Lawsuit news: {article.get('title', 'N/A')}"))
                
                # M&A detection
                if any(keyword in text for keyword in ["merger", "acquisition", "m&a", "takeover", "buyout", "deal"]):
                    events.append((EventType.M_AND_A, f"M&A news: {article.get('title', 'N/A')}"))
                
                # SEC investigation detection
                if any(keyword in text for keyword in ["sec", "investigation", "subpoena", "regulatory"]):
                    events.append((EventType.SEC_INVESTIGATION, f"SEC news: {article.get('title', 'N/A')}"))
                
                # Analyst upgrade/downgrade detection
                if "upgrade" in text or "raised" in text or "outperform" in text:
                    events.append((EventType.ANALYST_UPGRADE, f"Analyst upgrade: {article.get('title', 'N/A')}"))
                elif "downgrade" in text or "lowered" in text or "underperform" in text:
                    events.append((EventType.ANALYST_DOWNGRADE, f"Analyst downgrade: {article.get('title', 'N/A')}"))
                
                # Macro event detection
                if any(keyword in text for keyword in ["fed", "interest rate", "inflation", "recession", "gdp", "jobs report"]):
                    events.append((EventType.MACRO_EVENT, f"Macro event: {article.get('title', 'N/A')}"))
        
        return events

    @staticmethod
    def assess_event_risk(
        events: List[Tuple[EventType, str]],
        risk_level: RiskLevel,
        days_to_expiration: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Assess if event risk is acceptable for risk level.
        
        Args:
            events: List of detected events
            risk_level: Risk level threshold
            days_to_expiration: Days until option expiration
            
        Returns:
            Tuple of (acceptable, reason) where reason is None if acceptable
        """
        if not events:
            return True, None
        
        # Define event risk thresholds by risk level
        # LOW: no high-impact events allowed, restrict earnings/FDA/SEC
        # MEDIUM: restrict high-impact events within 30 days
        # HIGH: allow most events but warn on critical ones
        
        high_impact_events = {
            EventType.EARNINGS,
            EventType.FDA_DECISION,
            EventType.SEC_INVESTIGATION,
            EventType.LAWSUIT,
        }
        
        critical_events = {
            EventType.FDA_DECISION,
            EventType.SEC_INVESTIGATION,
        }
        
        for event_type, description in events:
            # Critical events always rejected for LOW risk
            if risk_level == RiskLevel.LOW and event_type in critical_events:
                return False, f"Critical event detected: {description}"
            
            # High-impact events rejected for LOW risk
            if risk_level == RiskLevel.LOW and event_type in high_impact_events:
                return False, f"High-impact event detected: {description}"
            
            # For MEDIUM risk, restrict high-impact events within 30 days
            if risk_level == RiskLevel.MEDIUM and event_type in high_impact_events:
                if days_to_expiration and days_to_expiration <= 30:
                    return False, f"High-impact event too close to expiration: {description}"
            
            # For HIGH risk, only reject critical events within 7 days
            if risk_level == RiskLevel.HIGH and event_type in critical_events:
                if days_to_expiration and days_to_expiration <= 7:
                    return False, f"Critical event too close to expiration: {description}"
        
        return True, None


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
            
            from math import exp, sqrt, log
            from scipy.stats import norm
            
            d1 = (log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
            d2 = d1 - sigma * sqrt(T)
            
            if contract.contract_type.lower() == "call":
                price = S * exp(-q * T) * norm.cdf(d1) - K * exp(-r * T) * norm.cdf(d2)
            else:  # put
                price = K * exp(-r * T) * norm.cdf(-d2) - S * exp(-q * T) * norm.cdf(-d1)
            
            return price
        except Exception:
            return None

    def _calculate_price_quantlib(self, contract: OptionContract) -> Optional[float]:
        """Calculate price using QuantLib."""
        try:
            if self.ql is None:
                return None
            
            # Implementation would use QuantLib pricing engine
            # Placeholder for now
            return None
        except Exception:
            return None


class OptionsChainFilter:
    """Filters option contracts based on risk level and quality criteria."""

    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize filter with risk level.
        
        Args:
            risk_level: Risk level for filtering thresholds
        """
        self.risk_level = risk_level
        self.volatility_analyzer = VolatilityAnalyzer()
        self.greeks_analyzer = GreeksAnalyzer()
        self.event_risk_analyzer = EventRiskAnalyzer()

    def get_risk_config(self) -> Dict[str, Any]:
        """Get filtering configuration for risk level.
        
        Returns:
            Dict of configuration parameters
        """
        configs = {
            RiskLevel.LOW: {
                "min_volume": 50,
                "min_open_interest": 100,
                "max_spread_pct": 0.05,
                "min_dte": 7,
                "max_dte": 60,
            },
            RiskLevel.MEDIUM: {
                "min_volume": 20,
                "min_open_interest": 50,
                "max_spread_pct": 0.10,
                "min_dte": 7,
                "max_dte": 90,
            },
            RiskLevel.HIGH: {
                "min_volume": 5,
                "min_open_interest": 10,
                "max_spread_pct": 0.20,
                "min_dte": 1,
                "max_dte": 180,
            },
        }
        return configs.get(self.risk_level, configs[RiskLevel.MEDIUM])

    def filter_contracts(
        self,
        contracts: List[OptionContract],
        news_articles: Optional[List[Dict[str, Any]]] = None,
    ) -> List[FilteredContract]:
        """Filter option contracts based on quality and risk criteria.
        
        Args:
            contracts: List of option contracts to filter
            news_articles: Optional news articles for event detection
            
        Returns:
            List of FilteredContract objects with acceptance status
        """
        filtered = []
        config = self.get_risk_config()
        
        for contract in contracts:
            result = self._filter_single_contract(contract, config, news_articles)
            filtered.append(result)
        
        return filtered

    def _filter_single_contract(
        self,
        contract: OptionContract,
        config: Dict[str, Any],
        news_articles: Optional[List[Dict[str, Any]]] = None,
    ) -> FilteredContract:
        """Filter a single contract.
        
        Args:
            contract: Contract to filter
            config: Risk configuration
            news_articles: Optional news articles
            
        Returns:
            FilteredContract with acceptance status
        """
        # Check expiration
        if contract.days_to_expiration is not None:
            if contract.days_to_expiration <= 0:
                return FilteredContract(
                    contract=contract,
                    accepted=False,
                    rejection_reason=RejectionReason.EXPIRED,
                    rejection_message="Contract has expired",
                )
            
            if contract.days_to_expiration < config["min_dte"] or contract.days_to_expiration > config["max_dte"]:
                return FilteredContract(
                    contract=contract,
                    accepted=False,
                    rejection_reason=RejectionReason.OUTSIDE_EXPIRATION_WINDOW,
                    rejection_message=f"DTE {contract.days_to_expiration} outside window {config['min_dte']}-{config['max_dte']}",
                )
        
        # Check bid/ask
        if contract.bid is None or contract.ask is None:
            return FilteredContract(
                contract=contract,
                accepted=False,
                rejection_reason=RejectionReason.MISSING_BID_ASK,
                rejection_message="Missing bid or ask price",
            )
        
        # Check spread
        mid = (contract.bid + contract.ask) / 2
        spread_pct = (contract.ask - contract.bid) / mid if mid > 0 else 1.0
        if spread_pct > config["max_spread_pct"]:
            return FilteredContract(
                contract=contract,
                accepted=False,
                rejection_reason=RejectionReason.EXCESSIVE_SPREAD,
                rejection_message=f"Spread {spread_pct:.2%} exceeds {config['max_spread_pct']:.2%}",
            )
        
        # Check volume
        if contract.volume is not None and contract.volume < config["min_volume"]:
            return FilteredContract(
                contract=contract,
                accepted=False,
                rejection_reason=RejectionReason.VOLUME_TOO_LOW,
                rejection_message=f"Volume {contract.volume} below minimum {config['min_volume']}",
            )
        
        # Check open interest
        if contract.open_interest is not None and contract.open_interest < config["min_open_interest"]:
            return FilteredContract(
                contract=contract,
                accepted=False,
                rejection_reason=RejectionReason.OPEN_INTEREST_TOO_LOW,
                rejection_message=f"Open interest {contract.open_interest} below minimum {config['min_open_interest']}",
            )
        
        # Check event risk
        events = self.event_risk_analyzer.detect_events(
            contract.symbol,
            contract,
            news_articles,
        )
        contract.event_risks = events
        
        acceptable, reason = self.event_risk_analyzer.assess_event_risk(
            events,
            self.risk_level,
            contract.days_to_expiration,
        )
        if not acceptable:
            return FilteredContract(
                contract=contract,
                accepted=False,
                rejection_reason=RejectionReason.EVENT_RISK_TOO_HIGH,
                rejection_message=reason or "Event risk too high",
            )
        
        # All checks passed
        return FilteredContract(
            contract=contract,
            accepted=True,
            rejection_reason=None,
            rejection_message=None,
        )


class RiskEngine:
    """Risk engine for validating trades against guardrails."""

    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize risk engine.
        
        Args:
            risk_level: Risk level for guardrails
        """
        self.risk_level = risk_level
        self.event_risk_analyzer = EventRiskAnalyzer()

    def validate_trade(
        self,
        contract: OptionContract,
        max_loss_pct: float,
        num_contracts: int,
        current_daily_loss_pct: float = 0.0,
        current_open_positions: int = 0,
        is_live_trading: bool = False,
        user_approved_live_trading: bool = False,
    ) -> RiskGuardrailResult:
        """Validate a trade against all risk guardrails.
        
        Args:
            contract: Option contract
            max_loss_pct: Maximum loss as percentage
            num_contracts: Number of contracts
            current_daily_loss_pct: Current daily loss percentage
            current_open_positions: Current number of open positions
            is_live_trading: Whether this is a live trade
            user_approved_live_trading: Whether user approved live trading
            
        Returns:
            RiskGuardrailResult with pass/fail and reason
        """
        # Check max loss per trade
        max_loss_limits = {
            RiskLevel.LOW: 2.0,
            RiskLevel.MEDIUM: 5.0,
            RiskLevel.HIGH: 10.0,
        }
        max_loss_limit = max_loss_limits.get(self.risk_level, 5.0)
        
        if max_loss_pct > max_loss_limit:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_LOSS_EXCEEDED,
                message=f"Max loss {max_loss_pct:.2f}% exceeds {self.risk_level.value} limit of {max_loss_limit:.2f}%",
            )
        
        # Check max contracts per trade
        max_contracts_limits = {
            RiskLevel.LOW: 5,
            RiskLevel.MEDIUM: 10,
            RiskLevel.HIGH: 20,
        }
        max_contracts_limit = max_contracts_limits.get(self.risk_level, 10)
        
        if num_contracts > max_contracts_limit:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_CONTRACTS_EXCEEDED,
                message=f"Contracts {num_contracts} exceeds {self.risk_level.value} limit of {max_contracts_limit}",
            )
        
        # Check max daily loss
        max_daily_loss_limits = {
            RiskLevel.LOW: 3.0,
            RiskLevel.MEDIUM: 7.0,
            RiskLevel.HIGH: 15.0,
        }
        max_daily_loss_limit = max_daily_loss_limits.get(self.risk_level, 7.0)
        total_daily_loss = current_daily_loss_pct + max_loss_pct
        
        if total_daily_loss > max_daily_loss_limit:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_DAILY_LOSS_EXCEEDED,
                message=f"Total daily loss {total_daily_loss:.2f}% exceeds {self.risk_level.value} limit of {max_daily_loss_limit:.2f}%",
            )
        
        # Check max open positions
        max_open_positions_limits = {
            RiskLevel.LOW: 5,
            RiskLevel.MEDIUM: 10,
            RiskLevel.HIGH: 20,
        }
        max_open_positions_limit = max_open_positions_limits.get(self.risk_level, 10)
        
        if current_open_positions >= max_open_positions_limit:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_OPEN_POSITIONS_EXCEEDED,
                message=f"Open positions {current_open_positions} at or exceeds {self.risk_level.value} limit of {max_open_positions_limit}",
            )
        
        # Check bid-ask spread
        if contract.bid is not None and contract.ask is not None:
            mid = (contract.bid + contract.ask) / 2
            spread_pct = (contract.ask - contract.bid) / mid if mid > 0 else 1.0
            
            spread_limits = {
                RiskLevel.LOW: 0.05,
                RiskLevel.MEDIUM: 0.10,
                RiskLevel.HIGH: 0.20,
            }
            spread_limit = spread_limits.get(self.risk_level, 0.10)
            
            if spread_pct > spread_limit:
                return RiskGuardrailResult(
                    passed=False,
                    reason=RejectionReason.BID_ASK_SPREAD_TOO_WIDE,
                    message=f"Bid-ask spread {spread_pct:.2%} exceeds {self.risk_level.value} limit of {spread_limit:.2%}",
                )
        
        # Check volume
        if contract.volume is not None:
            volume_limits = {
                RiskLevel.LOW: 50,
                RiskLevel.MEDIUM: 20,
                RiskLevel.HIGH: 5,
            }
            volume_limit = volume_limits.get(self.risk_level, 20)
            
            if contract.volume < volume_limit:
                return RiskGuardrailResult(
                    passed=False,
                    reason=RejectionReason.VOLUME_TOO_LOW,
                    message=f"Volume {contract.volume} below {self.risk_level.value} minimum of {volume_limit}",
                )
        
        # Check open interest
        if contract.open_interest is not None:
            oi_limits = {
                RiskLevel.LOW: 100,
                RiskLevel.MEDIUM: 50,
                RiskLevel.HIGH: 10,
            }
            oi_limit = oi_limits.get(self.risk_level, 50)
            
            if contract.open_interest < oi_limit:
                return RiskGuardrailResult(
                    passed=False,
                    reason=RejectionReason.OPEN_INTEREST_TOO_LOW,
                    message=f"Open interest {contract.open_interest} below {self.risk_level.value} minimum of {oi_limit}",
                )
        
        # Check earnings window
        if contract.earnings_date:
            try:
                earnings_dt = datetime.strptime(contract.earnings_date, "%Y-%m-%d")
                now = datetime.now()
                days_to_earnings = (earnings_dt - now).days
                
                earnings_buffers = {
                    RiskLevel.LOW: 5,
                    RiskLevel.MEDIUM: 3,
                    RiskLevel.HIGH: 1,
                }
                buffer = earnings_buffers.get(self.risk_level, 3)
                
                if -buffer <= days_to_earnings <= buffer:
                    return RiskGuardrailResult(
                        passed=False,
                        reason=RejectionReason.EARNINGS_WINDOW_RESTRICTED,
                        message=f"Earnings on {contract.earnings_date} within {buffer}-day buffer",
                    )
            except (ValueError, TypeError):
                pass
        
        # Check live trading approval
        if is_live_trading and not user_approved_live_trading:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.LIVE_TRADING_NOT_APPROVED,
                message="Live trading is disabled by default. User approval required.",
            )
        
        # Check event risk
        events = contract.event_risks or []
        acceptable, reason = self.event_risk_analyzer.assess_event_risk(
            events,
            self.risk_level,
            contract.days_to_expiration,
        )
        if not acceptable:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.EVENT_RISK_TOO_HIGH,
                message=reason or "Event risk too high",
            )
        
        # All checks passed
        return RiskGuardrailResult(
            passed=True,
            reason=None,
            message="Trade passed all risk guardrails",
        )
