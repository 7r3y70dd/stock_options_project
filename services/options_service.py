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


class OptionsChainFilter:
    """Filter option contracts based on quality and risk criteria."""

    @staticmethod
    def filter_expired(contract: OptionContract) -> FilteredContract:
        """Filter out expired contracts."""
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

    @staticmethod
    def filter_missing_bid_ask(contract: OptionContract) -> FilteredContract:
        """Filter out contracts with missing bid/ask."""
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

    @staticmethod
    def filter_illiquid(contract: OptionContract, risk_config) -> FilteredContract:
        """Filter out illiquid contracts (low volume/open_interest)."""
        volume = contract.volume or 0
        if volume < risk_config.min_volume:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.VOLUME_TOO_LOW,
                rejection_message=f"Volume {volume} below minimum {risk_config.min_volume}",
            )
        
        open_interest = contract.open_interest or 0
        if open_interest < risk_config.min_open_interest:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.OPEN_INTEREST_TOO_LOW,
                rejection_message=f"Open interest {open_interest} below minimum {risk_config.min_open_interest}",
            )
        
        return FilteredContract(
            contract=contract,
            passed=True,
            rejection_reason=RejectionReason.PASSED,
            rejection_message="",
        )

    @staticmethod
    def filter_spread(contract: OptionContract, risk_config) -> FilteredContract:
        """Filter out contracts with excessive bid/ask spread."""
        if contract.bid is None or contract.ask is None or contract.bid == 0:
            return FilteredContract(
                contract=contract,
                passed=True,
                rejection_reason=RejectionReason.PASSED,
                rejection_message="",
            )
        
        spread_pct = ((contract.ask - contract.bid) / contract.bid) * 100
        if spread_pct > risk_config.max_bid_ask_spread_pct:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.BID_ASK_SPREAD_TOO_WIDE,
                rejection_message=f"Spread {spread_pct:.2f}% exceeds maximum {risk_config.max_bid_ask_spread_pct}%",
            )
        
        return FilteredContract(
            contract=contract,
            passed=True,
            rejection_reason=RejectionReason.PASSED,
            rejection_message="",
        )

    @staticmethod
    def filter_expiration_window(contract: OptionContract, risk_config) -> FilteredContract:
        """Filter out contracts outside expiration window."""
        dte = contract.days_to_expiration
        if dte is None:
            return FilteredContract(
                contract=contract,
                passed=True,
                rejection_reason=RejectionReason.PASSED,
                rejection_message="",
            )
        
        if dte < risk_config.min_days_to_expiration or dte > risk_config.max_days_to_expiration:
            return FilteredContract(
                contract=contract,
                passed=False,
                rejection_reason=RejectionReason.OUTSIDE_EXPIRATION_WINDOW,
                rejection_message=f"DTE {dte} outside window [{risk_config.min_days_to_expiration}, {risk_config.max_days_to_expiration}]",
            )
        
        return FilteredContract(
            contract=contract,
            passed=True,
            rejection_reason=RejectionReason.PASSED,
            rejection_message="",
        )

    @staticmethod
    def filter_chain(
        contracts: List[OptionContract],
        risk_level: RiskLevel = RiskLevel.MEDIUM,
    ) -> List[FilteredContract]:
        """Filter an entire options chain."""
        risk_config = get_risk_config(risk_level)
        filtered = []
        
        for contract in contracts:
            # Apply all filters in sequence
            result = OptionsChainFilter.filter_expired(contract)
            if not result.passed:
                filtered.append(result)
                continue
            
            result = OptionsChainFilter.filter_missing_bid_ask(contract)
            if not result.passed:
                filtered.append(result)
                continue
            
            result = OptionsChainFilter.filter_illiquid(contract, risk_config)
            if not result.passed:
                filtered.append(result)
                continue
            
            result = OptionsChainFilter.filter_spread(contract, risk_config)
            if not result.passed:
                filtered.append(result)
                continue
            
            result = OptionsChainFilter.filter_expiration_window(contract, risk_config)
            if not result.passed:
                filtered.append(result)
                continue
            
            # Contract passed all filters
            filtered.append(FilteredContract(
                contract=contract,
                passed=True,
                rejection_reason=RejectionReason.PASSED,
                rejection_message="",
            ))
        
        return filtered


class RiskEngine:
    """Engine for validating trades against risk guardrails."""

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
        num_contracts: int = 1,
        current_daily_loss_pct: float = 0.0,
        current_open_positions: int = 0,
        is_live_trading: bool = False,
        user_approved_live_trading: bool = False,
    ) -> RiskGuardrailResult:
        """Validate a trade against all risk guardrails.
        
        Args:
            contract: OptionContract to validate
            max_loss_pct: Maximum loss percentage for this trade
            num_contracts: Number of contracts to trade
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
                message=f"Max loss {max_loss_pct:.2f}% exceeds limit {max_loss_limit:.2f}%",
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
                message=f"Number of contracts {num_contracts} exceeds limit {max_contracts_limit}",
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
                message=f"Total daily loss {total_daily_loss:.2f}% exceeds limit {max_daily_loss_limit:.2f}%",
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
                message=f"Open positions {current_open_positions} at or exceeds limit {max_open_positions_limit}",
            )

        # Check bid-ask spread
        if contract.bid is not None and contract.ask is not None and contract.bid > 0:
            spread_pct = ((contract.ask - contract.bid) / contract.bid) * 100
            max_spread_limits = {
                RiskLevel.LOW: 5.0,
                RiskLevel.MEDIUM: 10.0,
                RiskLevel.HIGH: 20.0,
            }
            max_spread_limit = max_spread_limits.get(self.risk_level, 10.0)
            if spread_pct > max_spread_limit:
                return RiskGuardrailResult(
                    passed=False,
                    reason=RejectionReason.BID_ASK_SPREAD_TOO_WIDE,
                    message=f"Bid-ask spread {spread_pct:.2f}% exceeds limit {max_spread_limit:.2f}%",
                )

        # Check volume
        volume = contract.volume or 0
        min_volume_limits = {
            RiskLevel.LOW: 50,
            RiskLevel.MEDIUM: 20,
            RiskLevel.HIGH: 5,
        }
        min_volume_limit = min_volume_limits.get(self.risk_level, 20)
        if volume < min_volume_limit:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.VOLUME_TOO_LOW,
                message=f"Volume {volume} below minimum {min_volume_limit}",
            )

        # Check open interest
        open_interest = contract.open_interest or 0
        min_oi_limits = {
            RiskLevel.LOW: 100,
            RiskLevel.MEDIUM: 50,
            RiskLevel.HIGH: 10,
        }
        min_oi_limit = min_oi_limits.get(self.risk_level, 50)
        if open_interest < min_oi_limit:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.OPEN_INTEREST_TOO_LOW,
                message=f"Open interest {open_interest} below minimum {min_oi_limit}",
            )

        # Check earnings window
        if contract.earnings_date:
            try:
                earnings_dt = datetime.fromisoformat(contract.earnings_date)
                now = datetime.now()
                days_to_earnings = (earnings_dt - now).days
                
                earnings_buffer_limits = {
                    RiskLevel.LOW: 5,
                    RiskLevel.MEDIUM: 3,
                    RiskLevel.HIGH: 1,
                }
                earnings_buffer = earnings_buffer_limits.get(self.risk_level, 3)
                
                if -earnings_buffer <= days_to_earnings <= earnings_buffer:
                    return RiskGuardrailResult(
                        passed=False,
                        reason=RejectionReason.EARNINGS_WINDOW_RESTRICTED,
                        message=f"Trade within {earnings_buffer} days of earnings",
                    )
            except (ValueError, TypeError):
                pass  # Invalid earnings date format, skip check

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
            reason=RejectionReason.PASSED,
            message="Trade passed all risk guardrails",
        )


class OptionsService:
    """Service for analyzing and scoring option contracts."""

    def __init__(
        self,
        data_provider: Optional[DataProvider] = None,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
    ):
        """Initialize options service.
        
        Args:
            data_provider: Optional data provider (defaults to MockDataProvider)
            risk_level: Risk level for filtering and scoring
        """
        self.data_provider = data_provider or MockDataProvider()
        self.risk_level = risk_level
        self.risk_engine = RiskEngine(risk_level=risk_level)
        self.filter = OptionsChainFilter()
