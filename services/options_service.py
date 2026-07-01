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
    SCORE_TOO_LOW = "score_too_low"
    LIQUIDITY_SCORE_TOO_LOW = "liquidity_score_too_low"
    NO_SAFE_OPPORTUNITY = "no_safe_opportunity"


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
        
        if contract.theta is not None:
            greeks["theta"] = contract.theta
        
        if contract.vega is not None:
            greeks["vega"] = contract.vega
        
        return greeks


class RiskConfig:
    """Risk configuration for a specific risk level."""
    
    def __init__(self, risk_level: RiskLevel):
        """Initialize risk config for a risk level.
        
        Args:
            risk_level: Risk level (LOW, MEDIUM, HIGH)
        """
        self.risk_level = risk_level
        
        # Define thresholds by risk level
        if risk_level == RiskLevel.LOW:
            self.max_loss_per_trade_pct = 1.0
            self.max_daily_loss_pct = 3.0
            self.max_open_positions = 5
            self.max_contracts_per_trade = 2
            self.min_liquidity_score = 60.0
            self.min_signal_score = 60.0
        elif risk_level == RiskLevel.HIGH:
            self.max_loss_per_trade_pct = 5.0
            self.max_daily_loss_pct = 15.0
            self.max_open_positions = 20
            self.max_contracts_per_trade = 10
            self.min_liquidity_score = 30.0
            self.min_signal_score = 40.0
        else:  # MEDIUM
            self.max_loss_per_trade_pct = 2.5
            self.max_daily_loss_pct = 7.5
            self.max_open_positions = 10
            self.max_contracts_per_trade = 5
            self.min_liquidity_score = 40.0
            self.min_signal_score = 50.0


def get_risk_config(risk_level: RiskLevel) -> RiskConfig:
    """Get risk configuration for a risk level.
    
    Args:
        risk_level: Risk level
        
    Returns:
        RiskConfig instance
    """
    return RiskConfig(risk_level)


class RiskEngine:
    """Validates trades against risk guardrails."""
    
    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize risk engine.
        
        Args:
            risk_level: User's risk level
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
        is_live_trading: bool = False,
        user_approved_live_trading: bool = False,
    ) -> RiskGuardrailResult:
        """Validate a trade against all guardrails.
        
        Args:
            contract: The OptionContract to validate.
            max_loss_pct: Maximum loss for this trade as % of portfolio.
            num_contracts: Number of contracts to trade.
            current_daily_loss_pct: Current daily loss as % of portfolio.
            current_open_positions: Current number of open positions.
            is_live_trading: Whether this is a live trade (vs paper trade).
            user_approved_live_trading: Whether user has approved live trading.
        
        Returns:
            RiskGuardrailResult with passed status and human-readable message.
        """
        # Check max loss per trade
        if max_loss_pct > self.config.max_loss_per_trade_pct:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_LOSS_EXCEEDED,
                message=f"Max loss {max_loss_pct:.2f}% exceeds limit of {self.config.max_loss_per_trade_pct:.2f}%",
            )
        
        # Check max daily loss
        if current_daily_loss_pct + max_loss_pct > self.config.max_daily_loss_pct:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_DAILY_LOSS_EXCEEDED,
                message=f"Daily loss would be {current_daily_loss_pct + max_loss_pct:.2f}%, exceeds limit of {self.config.max_daily_loss_pct:.2f}%",
            )
        
        # Check max contracts per trade
        if num_contracts > self.config.max_contracts_per_trade:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_CONTRACTS_EXCEEDED,
                message=f"Number of contracts {num_contracts} exceeds limit of {self.config.max_contracts_per_trade}",
            )
        
        # Check max open positions
        if current_open_positions + 1 > self.config.max_open_positions:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_OPEN_POSITIONS_EXCEEDED,
                message=f"Open positions would be {current_open_positions + 1}, exceeds limit of {self.config.max_open_positions}",
            )
        
        # Check live trading approval
        if is_live_trading and not user_approved_live_trading:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.LIVE_TRADING_NOT_APPROVED,
                message="Live trading not approved by user",
            )
        
        # Check event risk
        if contract.event_risks:
            acceptable, reason = EventRiskAnalyzer.assess_event_risk(
                contract.event_risks,
                self.risk_level,
                contract.days_to_expiration,
            )
            if not acceptable:
                return RiskGuardrailResult(
                    passed=False,
                    reason=RejectionReason.EVENT_RISK_TOO_HIGH,
                    message=reason or "Event risk too high",
                )
        
        return RiskGuardrailResult(passed=True, message="Trade passed all guardrails")

    def validate_signal_score(
        self,
        signal_score: float,
        liquidity_score: Optional[float] = None,
    ) -> RiskGuardrailResult:
        """Validate signal score and liquidity against thresholds.
        
        Args:
            signal_score: Overall signal score (0-100)
            liquidity_score: Liquidity score (0-100), optional
            
        Returns:
            RiskGuardrailResult with passed status
        """
        # Check minimum signal score
        if signal_score < self.config.min_signal_score:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.SCORE_TOO_LOW,
                message=f"Signal score {signal_score:.1f} below minimum of {self.config.min_signal_score:.1f}",
            )
        
        # Check minimum liquidity score
        if liquidity_score is not None and liquidity_score < self.config.min_liquidity_score:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.LIQUIDITY_SCORE_TOO_LOW,
                message=f"Liquidity score {liquidity_score:.1f} below minimum of {self.config.min_liquidity_score:.1f}",
            )
        
        return RiskGuardrailResult(passed=True, message="Signal passed score validation")
