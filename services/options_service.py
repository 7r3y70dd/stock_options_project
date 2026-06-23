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
                    f"({thresholds['min_theta']:.4f}). High time decay."
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


class RiskEngine:
    """Engine for validating trades against risk guardrails.
    
    Validates option trades against a comprehensive set of risk guardrails
    based on the configured risk level (LOW, MEDIUM, HIGH).
    """

    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize RiskEngine with a risk level.
        
        Args:
            risk_level: Risk level for guardrail thresholds
        """
        self.risk_level = risk_level
        self.config = get_risk_config(risk_level)

    def validate_trade(
        self,
        contract: OptionContract,
        max_loss_pct: float,
        num_contracts: int,
        current_daily_loss_pct: float = 0.0,
        current_open_positions: int = 0,
        is_live_trading: bool = False,
        user_approved_live_trading: bool = False,
    ) -> RiskGuardrail:
        """Validate a trade against all risk guardrails.
        
        Args:
            contract: OptionContract to validate
            max_loss_pct: Maximum loss percentage for this trade
            num_contracts: Number of contracts to trade
            current_daily_loss_pct: Current daily loss percentage
            current_open_positions: Current number of open positions
            is_live_trading: Whether this is a live trading request
            user_approved_live_trading: Whether user has approved live trading
            
        Returns:
            RiskGuardrail object with validation result
        """
        # Check max loss per trade
        if max_loss_pct > self.config.max_loss_per_trade_pct:
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.MAX_LOSS_EXCEEDED,
                message=f"Max loss per trade {max_loss_pct:.2f}% exceeds limit {self.config.max_loss_per_trade_pct:.2f}%",
            )
        
        # Check max contracts per trade
        if num_contracts > self.config.max_contracts_per_trade:
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.MAX_CONTRACTS_EXCEEDED,
                message=f"Number of contracts {num_contracts} exceeds limit {self.config.max_contracts_per_trade}",
            )
        
        # Check max daily loss
        total_daily_loss = current_daily_loss_pct + max_loss_pct
        if total_daily_loss > self.config.max_daily_loss_pct:
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.MAX_DAILY_LOSS_EXCEEDED,
                message=f"Total daily loss {total_daily_loss:.2f}% exceeds limit {self.config.max_daily_loss_pct:.2f}%",
            )
        
        # Check max open positions
        if current_open_positions >= self.config.max_open_positions:
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.MAX_OPEN_POSITIONS_EXCEEDED,
                message=f"Open positions {current_open_positions} at or exceeds limit {self.config.max_open_positions}",
            )
        
        # Check bid-ask spread
        if contract.bid is not None and contract.ask is not None and contract.bid > 0:
            spread_pct = (contract.ask - contract.bid) / contract.bid
            if spread_pct > self.config.max_bid_ask_spread_pct:
                return RiskGuardrail(
                    passed=False,
                    reason=RejectionReason.BID_ASK_SPREAD_TOO_WIDE,
                    message=f"Bid-ask spread {spread_pct:.2%} exceeds limit {self.config.max_bid_ask_spread_pct:.2%}",
                )
        
        # Check volume
        if contract.volume is not None and contract.volume < self.config.min_volume:
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.VOLUME_TOO_LOW,
                message=f"Volume {contract.volume} below minimum {self.config.min_volume}",
            )
        
        # Check open interest
        if contract.open_interest is not None and contract.open_interest < self.config.min_open_interest:
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.OPEN_INTEREST_TOO_LOW,
                message=f"Open interest {contract.open_interest} below minimum {self.config.min_open_interest}",
            )
        
        # Check earnings window
        if contract.earnings_date:
            try:
                earnings_dt = datetime.fromisoformat(contract.earnings_date)
                now = datetime.now()
                days_to_earnings = (earnings_dt - now).days
                if abs(days_to_earnings) < self.config.earnings_window_days:
                    return RiskGuardrail(
                        passed=False,
                        reason=RejectionReason.EARNINGS_WINDOW_RESTRICTED,
                        message=f"Trade within {self.config.earnings_window_days} day earnings window",
                    )
            except (ValueError, TypeError):
                pass  # Invalid earnings date format, skip check
        
        # Check live trading approval
        if is_live_trading and not user_approved_live_trading:
            return RiskGuardrail(
                passed=False,
                reason=RejectionReason.LIVE_TRADING_NOT_APPROVED,
                message="Live trading is disabled by default. User approval required.",
            )
        
        # All checks passed
        return RiskGuardrail(
            passed=True,
            reason=None,
            message="Trade passed all risk guardrails",
        )


class OptionsChainFilter:
    """Filter for options chains based on risk guardrails."""

    def __init__(self, risk_engine: RiskEngine):
        """Initialize filter with a risk engine.
        
        Args:
            risk_engine: RiskEngine instance for validation
        """
        self.risk_engine = risk_engine

    def filter_contracts(
        self,
        contracts: List[OptionContract],
        max_loss_pct: float,
        num_contracts: int = 1,
    ) -> List[FilteredContract]:
        """Filter a list of contracts.
        
        Args:
            contracts: List of OptionContract objects to filter
            max_loss_pct: Maximum loss percentage for validation
            num_contracts: Number of contracts per trade
            
        Returns:
            List of FilteredContract objects with pass/fail status
        """
        results = []
        for contract in contracts:
            guardrail = self.risk_engine.validate_trade(
                contract,
                max_loss_pct=max_loss_pct,
                num_contracts=num_contracts,
            )
            results.append(
                FilteredContract(
                    contract=contract if guardrail.passed else None,
                    passed=guardrail.passed,
                    rejection_reason=guardrail.reason,
                    rejection_message=guardrail.message,
                )
            )
        return results
