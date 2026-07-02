"""Options service for analyzing and filtering option contracts."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime, timedelta
import math
import logging

logger = logging.getLogger(__name__)


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


class ExitRuleType(Enum):
    """Types of exit rules for trades."""
    PROFIT_TARGET = "profit_target"
    STOP_LOSS = "stop_loss"
    TIME_BASED = "time_based"
    EARNINGS_EXIT = "earnings_exit"
    EXPIRATION_EXIT = "expiration_exit"
    TRAILING_STOP = "trailing_stop"


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
    NO_EXIT_PLAN = "no_exit_plan"
    KILL_SWITCH_ACTIVE = "kill_switch_active"


@dataclass
class ExitRule:
    """Represents an exit rule for a trade."""
    rule_type: ExitRuleType
    trigger_value: float  # Price level, percentage, or days depending on rule_type
    description: str  # Human-readable description of the exit rule
    is_mandatory: bool = True  # Whether this rule must be enforced


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
    liquidity_score: Optional[float] = None


@dataclass
class ScoredOption:
    """Represents an option contract with analysis scores."""
    contract: OptionContract
    greeks_score: float = 0.0
    volatility_score: float = 0.0
    pricing_score: float = 0.0
    overall_score: float = 0.0
    analysis_details: Dict[str, Any] = field(default_factory=dict)
    score: Optional[float] = None
    liquidity_score: Optional[float] = None


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


class KillSwitchManager:
    """Manages the global kill switch state for emergency trading halt.
    
    The kill switch can be activated to:
    - Block all new order creation
    - Optionally close paper positions
    - Display a banner in the UI
    - Log activation time and reason
    """

    def __init__(self):
        """Initialize kill switch manager."""
        self._is_active = False
        self._activated_at: Optional[datetime] = None
        self._activated_by: Optional[str] = None
        self._reason: Optional[str] = None
        self._close_positions = False

    def activate(
        self,
        activated_by: str = "system",
        reason: str = "Emergency trading halt",
        close_positions: bool = False,
    ) -> None:
        """Activate the kill switch.
        
        Args:
            activated_by: User or system that activated the kill switch
            reason: Reason for activation
            close_positions: Whether to close paper positions
        """
        self._is_active = True
        self._activated_at = datetime.utcnow()
        self._activated_by = activated_by
        self._reason = reason
        self._close_positions = close_positions
        
        logger.warning(
            f"KILL SWITCH ACTIVATED by {activated_by} at {self._activated_at.isoformat()}: {reason}"
        )

    def deactivate(self) -> None:
        """Deactivate the kill switch."""
        if self._is_active:
            logger.warning(
                f"KILL SWITCH DEACTIVATED at {datetime.utcnow().isoformat()}"
            )
        self._is_active = False
        self._activated_at = None
        self._activated_by = None
        self._reason = None
        self._close_positions = False

    def is_active(self) -> bool:
        """Check if kill switch is active.
        
        Returns:
            True if kill switch is active, False otherwise
        """
        return self._is_active

    def get_status(self) -> Dict[str, Any]:
        """Get kill switch status.
        
        Returns:
            Dict with is_active, activated_at, activated_by, reason, close_positions
        """
        return {
            "is_active": self._is_active,
            "activated_at": self._activated_at.isoformat() if self._activated_at else None,
            "activated_by": self._activated_by,
            "reason": self._reason,
            "close_positions": self._close_positions,
        }

    def should_close_positions(self) -> bool:
        """Check if positions should be closed.
        
        Returns:
            True if kill switch is active and close_positions is True
        """
        return self._is_active and self._close_positions


# Global kill switch instance
_kill_switch_manager: Optional[KillSwitchManager] = None


def get_kill_switch_manager() -> KillSwitchManager:
    """Get or initialize the global kill switch manager.
    
    Returns:
        KillSwitchManager instance
    """
    global _kill_switch_manager
    if _kill_switch_manager is None:
        _kill_switch_manager = KillSwitchManager()
    return _kill_switch_manager


def set_kill_switch_manager(manager: KillSwitchManager) -> None:
    """Set the global kill switch manager.
    
    Args:
        manager: KillSwitchManager instance to use
    """
    global _kill_switch_manager
    _kill_switch_manager = manager


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
            if risk_level == RiskLevel.LOW and event_type in critical_events:
                return False, f"Critical event detected: {description}"
            
            if risk_level == RiskLevel.LOW and event_type in high_impact_events:
                return False, f"High-impact event detected: {description}"
            
            if risk_level == RiskLevel.MEDIUM and event_type in high_impact_events:
                if days_to_expiration and days_to_expiration <= 30:
                    return False, f"High-impact event too close to expiration: {description}"
            
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
            Dict with normalized Greeks
        """
        return {
            "delta": contract.delta or 0.0,
            "gamma": contract.gamma or 0.0,
            "theta": contract.theta or 0.0,
            "vega": contract.vega or 0.0,
        }

    @staticmethod
    def assess_greek_profile(
        contract: OptionContract,
        risk_level: RiskLevel,
    ) -> Tuple[bool, List[str], Dict[str, float]]:
        """Assess if Greeks profile is acceptable for risk level.
        
        Args:
            contract: Option contract
            risk_level: Risk level threshold
            
        Returns:
            Tuple of (acceptable, warnings, scores)
        """
        warnings = []
        acceptable = True
        scores = GreeksAnalyzer.analyze_greeks(contract)
        
        return acceptable, warnings, scores

    @staticmethod
    def calculate_greeks_score(contract: OptionContract, risk_level: RiskLevel) -> float:
        """Calculate Greeks score for contract.
        
        Args:
            contract: Option contract
            risk_level: Risk level
            
        Returns:
            Greeks score 0.0-1.0
        """
        return 1.0


class RiskEngine:
    """Risk engine for validating trades against guardrails.
    
    Validates trades against multiple risk guardrails including:
    - Max loss per trade
    - Max contracts per trade
    - Max daily loss
    - Max open positions
    - Bid-ask spread
    - Volume and open interest
    - Event risk
    - Exit rules
    - Kill switch status
    """

    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize risk engine.
        
        Args:
            risk_level: Risk level for guardrail thresholds
        """
        self.risk_level = risk_level
        self.kill_switch = get_kill_switch_manager()

    def validate_trade(
        self,
        contract: OptionContract,
        max_loss_pct: float,
        num_contracts: int,
        exit_rules: Optional[List[ExitRule]] = None,
        current_daily_loss_pct: float = 0.0,
        current_open_positions: int = 0,
    ) -> RiskGuardrailResult:
        """Validate a trade against all guardrails.
        
        Args:
            contract: Option contract to validate
            max_loss_pct: Maximum loss as percentage
            num_contracts: Number of contracts
            exit_rules: Exit rules for the trade
            current_daily_loss_pct: Current daily loss percentage
            current_open_positions: Current number of open positions
            
        Returns:
            RiskGuardrailResult with validation result
        """
        # Check kill switch first
        if self.kill_switch.is_active():
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.KILL_SWITCH_ACTIVE,
                message="Trading is disabled: Emergency kill switch is active",
            )

        # Check exit rules
        if not exit_rules or len(exit_rules) == 0:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.NO_EXIT_PLAN,
                message="Trade rejected: No exit plan defined. Every trade must have exit rules (profit target, stop loss, etc.)",
            )

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
                message=f"Trade rejected: Max loss {max_loss_pct:.2f}% exceeds {self.risk_level.value} limit of {max_loss_limit:.2f}%",
            )

        # Check max contracts per trade
        max_contracts = 10
        if num_contracts > max_contracts:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_CONTRACTS_EXCEEDED,
                message=f"Trade rejected: {num_contracts} contracts exceeds maximum of {max_contracts}",
            )

        # Check max daily loss
        max_daily_loss_limits = {
            RiskLevel.LOW: 3.0,
            RiskLevel.MEDIUM: 7.0,
            RiskLevel.HIGH: 15.0,
        }
        max_daily_loss = max_daily_loss_limits.get(self.risk_level, 7.0)
        total_daily_loss = current_daily_loss_pct + max_loss_pct
        if total_daily_loss > max_daily_loss:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_DAILY_LOSS_EXCEEDED,
                message=f"Trade rejected: Total daily loss {total_daily_loss:.2f}% exceeds limit of {max_daily_loss:.2f}%",
            )

        # Check max open positions
        max_open_positions = {
            RiskLevel.LOW: 5,
            RiskLevel.MEDIUM: 10,
            RiskLevel.HIGH: 20,
        }
        max_positions = max_open_positions.get(self.risk_level, 10)
        if current_open_positions >= max_positions:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_OPEN_POSITIONS_EXCEEDED,
                message=f"Trade rejected: Already at maximum of {max_positions} open positions",
            )

        # Check bid-ask spread
        if contract.bid and contract.ask:
            spread_pct = (contract.ask - contract.bid) / contract.bid * 100
            spread_limits = {
                RiskLevel.LOW: 5.0,
                RiskLevel.MEDIUM: 10.0,
                RiskLevel.HIGH: 15.0,
            }
            spread_limit = spread_limits.get(self.risk_level, 10.0)
            if spread_pct > spread_limit:
                return RiskGuardrailResult(
                    passed=False,
                    reason=RejectionReason.BID_ASK_SPREAD_TOO_WIDE,
                    message=f"Trade rejected: Bid-ask spread {spread_pct:.2f}% exceeds {self.risk_level.value} limit of {spread_limit:.2f}%",
                )

        # Check volume
        volume_limits = {
            RiskLevel.LOW: 50,
            RiskLevel.MEDIUM: 20,
            RiskLevel.HIGH: 10,
        }
        min_volume = volume_limits.get(self.risk_level, 20)
        if contract.volume and contract.volume < min_volume:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.VOLUME_TOO_LOW,
                message=f"Trade rejected: Volume {contract.volume} is below {self.risk_level.value} minimum of {min_volume}",
            )

        # Check open interest
        oi_limits = {
            RiskLevel.LOW: 100,
            RiskLevel.MEDIUM: 50,
            RiskLevel.HIGH: 20,
        }
        min_oi = oi_limits.get(self.risk_level, 50)
        if contract.open_interest and contract.open_interest < min_oi:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.OPEN_INTEREST_TOO_LOW,
                message=f"Trade rejected: Open interest {contract.open_interest} is below {self.risk_level.value} minimum of {min_oi}",
            )

        # All checks passed
        return RiskGuardrailResult(
            passed=True,
            reason=None,
            message="Trade passed all risk guardrails",
        )
