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
            Greeks score from 0.0 to 1.0
        """
        acceptable, warnings, scores = GreeksAnalyzer.assess_greek_profile(contract, risk_level)
        
        if not scores:
            # No Greeks data available
            return 1.0
        
        # Average the individual scores
        avg_score = sum(scores.values()) / len(scores)
        
        # Penalize for warnings
        penalty = len(warnings) * 0.1
        final_score = max(avg_score - penalty, 0.0)
        
        return min(final_score, 1.0)


class PricingAnalyzer:
    """Analyzer for option pricing using Black-Scholes model."""

    def __init__(self, risk_free_rate: float = 0.05, dividend_yield: float = 0.0):
        """Initialize pricing analyzer.
        
        Args:
            risk_free_rate: Risk-free interest rate (default: 5%)
            dividend_yield: Dividend yield (default: 0%)
        """
        self.risk_free_rate = risk_free_rate
        self.dividend_yield = dividend_yield
        self.pricing_engine = None
        
        if QUANTLIB_AVAILABLE:
            try:
                self.pricing_engine = QuantLibPricingEngine(
                    risk_free_rate=risk_free_rate,
                    dividend_yield=dividend_yield,
                )
            except Exception:
                pass

    def calculate_theoretical_price(self, contract: OptionContract) -> Optional[float]:
        """Calculate theoretical price for a contract.
        
        Args:
            contract: OptionContract to price
            
        Returns:
            Theoretical price or None if pricing engine unavailable or data missing
        """
        if self.pricing_engine is None:
            return None
        
        if contract.implied_volatility is None or contract.underlying_price is None:
            return None
        
        try:
            price = self.pricing_engine.price(
                underlying_price=contract.underlying_price,
                strike=contract.strike,
                time_to_expiration=contract.days_to_expiration / 365.0 if contract.days_to_expiration else 0.1,
                volatility=contract.implied_volatility,
                option_type="call" if contract.contract_type.lower() == "call" else "put",
            )
            return price
        except Exception:
            return None

    def compare_prices(self, contract: OptionContract) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Compare market price with theoretical price.
        
        Args:
            contract: OptionContract to compare
            
        Returns:
            Tuple of (theoretical_price, difference, assessment)
            where assessment is "overpriced", "underpriced", or "fair"
        """
        if contract.bid is None or contract.ask is None:
            return None, None, None
        
        theoretical_price = self.calculate_theoretical_price(contract)
        if theoretical_price is None:
            return None, None, None
        
        market_mid_price = (contract.bid + contract.ask) / 2
        difference = market_mid_price - theoretical_price
        
        # Determine if overpriced or underpriced
        threshold = theoretical_price * 0.05  # 5% threshold
        if difference > threshold:
            assessment = "overpriced"
        elif difference < -threshold:
            assessment = "underpriced"
        else:
            assessment = "fair"
        
        return theoretical_price, difference, assessment


class OptionsChainFilter:
    """Filter option contracts based on quality and risk criteria.
    
    Filters contracts by:
    - Expiration (removes expired contracts)
    - Bid/ask availability
    - Liquidity (volume and open interest)
    - Bid-ask spread
    - Risk level
    - Expiration window
    """

    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize options chain filter.
        
        Args:
            risk_level: Risk level for filtering thresholds
        """
        self.risk_level = risk_level
        self.risk_config = get_risk_config(risk_level)

    def filter_chain(
        self,
        contracts: List[OptionContract],
    ) -> List[FilteredContract]:
        """Filter a chain of option contracts.
        
        Args:
            contracts: List of OptionContract to filter
            
        Returns:
            List of FilteredContract with pass/fail status and rejection reasons
        """
        results = []
        
        for contract in contracts:
            result = self._filter_contract(contract)
            results.append(result)
        
        return results

    def _filter_contract(self, contract: OptionContract) -> FilteredContract:
        """Filter a single contract through all checks.
        
        Args:
            contract: OptionContract to filter
            
        Returns:
            FilteredContract with pass/fail status
        """
        # Check expiration
        if contract.expiration:
            try:
                exp_date = datetime.strptime(contract.expiration, "%Y-%m-%d").date()
                if exp_date < datetime.now().date():
                    return FilteredContract(
                        contract=contract,
                        passed=False,
                        rejection_reason=RejectionReason.EXPIRED,
                        rejection_message="Contract has expired",
                    )
            except (ValueError, TypeError):
                pass
        
        # Check bid/ask
        if contract.bid is None or contract.ask is None:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.MISSING_BID_ASK,
                rejection_message="Missing bid or ask price",
            )
        
        # Check liquidity (volume)
        min_volume = self.risk_config.get("min_volume", 10)
        if (contract.volume or 0) < min_volume:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.VOLUME_TOO_LOW,
                rejection_message=f"Volume {contract.volume or 0} below minimum {min_volume}",
            )
        
        # Check liquidity (open interest)
        min_open_interest = self.risk_config.get("min_open_interest", 20)
        if (contract.open_interest or 0) < min_open_interest:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.OPEN_INTEREST_TOO_LOW,
                rejection_message=f"Open interest {contract.open_interest or 0} below minimum {min_open_interest}",
            )
        
        # Check bid-ask spread
        max_spread_pct = self.risk_config.get("max_bid_ask_spread_pct", 0.05)
        mid_price = (contract.bid + contract.ask) / 2
        if mid_price > 0:
            spread_pct = (contract.ask - contract.bid) / mid_price
            if spread_pct > max_spread_pct:
                return FilteredContract(
                    contract=contract,
                    passed=False,
                    rejection_reason=RejectionReason.BID_ASK_SPREAD_TOO_WIDE,
                    rejection_message=f"Bid-ask spread {spread_pct:.1%} exceeds maximum {max_spread_pct:.1%}",
                )
        
        # Check expiration window
        min_dte = self.risk_config.get("min_days_to_expiration", 7)
        max_dte = self.risk_config.get("max_days_to_expiration", 60)
        dte = contract.days_to_expiration or 30
        if dte < min_dte or dte > max_dte:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.EXPIRATION_WINDOW_INVALID,
                rejection_message=f"Days to expiration {dte} outside window [{min_dte}, {max_dte}]",
            )
        
        # All checks passed
        return FilteredContract(
            contract=contract,
            passed=True,
            rejection_reason=RejectionReason.NONE,
            rejection_message="",
        )


class RiskEngine:
    """Engine for validating trades against risk guardrails.
    
    Validates trades against global risk limits including:
    - Max loss per trade
    - Max contracts per trade
    - Max daily loss
    - Max open positions
    - Bid-ask spread limits
    - Volume and open interest minimums
    - Earnings window restrictions
    - Live trading approval
    """

    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize risk engine.
        
        Args:
            risk_level: Risk level for guardrail thresholds
        """
        self.risk_level = risk_level
        self.risk_config = get_risk_config(risk_level)

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
            contract: OptionContract to validate
            max_loss_pct: Maximum loss as percentage
            num_contracts: Number of contracts
            current_daily_loss_pct: Current daily loss percentage
            current_open_positions: Current number of open positions
            is_live_trading: Whether this is a live trade
            user_approved_live_trading: Whether user approved live trading
            
        Returns:
            RiskGuardrailResult with pass/fail status and reason
        """
        # Check max loss per trade
        max_loss_limit = self.risk_config.get("max_loss_per_trade_pct", 5.0)
        if max_loss_pct > max_loss_limit:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_LOSS_EXCEEDED,
                message=f"Max loss {max_loss_pct:.2f}% exceeds limit {max_loss_limit:.2f}%",
            )
        
        # Check max contracts per trade
        max_contracts = self.risk_config.get("max_contracts_per_trade", 10)
        if num_contracts > max_contracts:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_CONTRACTS_EXCEEDED,
                message=f"Number of contracts {num_contracts} exceeds limit {max_contracts}",
            )
        
        # Check max daily loss
        max_daily_loss = self.risk_config.get("max_daily_loss_pct", 3.0)
        total_daily_loss = current_daily_loss_pct + max_loss_pct
        if total_daily_loss > max_daily_loss:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_DAILY_LOSS_EXCEEDED,
                message=f"Total daily loss {total_daily_loss:.2f}% exceeds limit {max_daily_loss:.2f}%",
            )
        
        # Check max open positions
        max_open_positions = self.risk_config.get("max_open_positions", 5)
        if current_open_positions >= max_open_positions:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_OPEN_POSITIONS_EXCEEDED,
                message=f"Open positions {current_open_positions} at or exceeds limit {max_open_positions}",
            )
        
        # Check bid-ask spread
        if contract.bid and contract.ask:
            max_spread_pct = self.risk_config.get("max_bid_ask_spread_pct", 0.05)
            mid_price = (contract.bid + contract.ask) / 2
            if mid_price > 0:
                spread_pct = (contract.ask - contract.bid) / mid_price
                if spread_pct > max_spread_pct:
                    return RiskGuardrailResult(
                        passed=False,
                        reason=RejectionReason.BID_ASK_SPREAD_TOO_WIDE,
                        message=f"Bid-ask spread {spread_pct:.1%} exceeds limit {max_spread_pct:.1%}",
                    )
        
        # Check volume
        min_volume = self.risk_config.get("min_volume", 10)
        if (contract.volume or 0) < min_volume:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.VOLUME_TOO_LOW,
                message=f"Volume {contract.volume or 0} below minimum {min_volume}",
            )
        
        # Check open interest
        min_open_interest = self.risk_config.get("min_open_interest", 20)
        if (contract.open_interest or 0) < min_open_interest:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.OPEN_INTEREST_TOO_LOW,
                message=f"Open interest {contract.open_interest or 0} below minimum {min_open_interest}",
            )
        
        # Check earnings window
        if contract.earnings_date:
            try:
                earnings_date = datetime.strptime(contract.earnings_date, "%Y-%m-%d").date()
                earnings_buffer = self.risk_config.get("earnings_buffer_days", 5)
                days_until_earnings = (earnings_date - datetime.now().date()).days
                if -earnings_buffer <= days_until_earnings <= earnings_buffer:
                    return RiskGuardrailResult(
                        passed=False,
                        reason=RejectionReason.EARNINGS_WINDOW_RESTRICTED,
                        message=f"Trade within {earnings_buffer} days of earnings",
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
        
        # All checks passed
        return RiskGuardrailResult(
            passed=True,
            reason=RejectionReason.NONE,
            message="Trade passed all risk guardrails",
        )
