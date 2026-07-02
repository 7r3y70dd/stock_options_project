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
            Dict of Greek values with absolute values
        """
        greeks = {}
        
        if contract.delta is not None:
            greeks["delta"] = abs(contract.delta)
        if contract.gamma is not None:
            greeks["gamma"] = abs(contract.gamma)
        if contract.theta is not None:
            greeks["theta"] = abs(contract.theta)
        if contract.vega is not None:
            greeks["vega"] = abs(contract.vega)
        
        return greeks


class ExitRuleValidator:
    """Validates exit rules for trades."""

    @staticmethod
    def validate_exit_rules(exit_rules: Optional[List[ExitRule]]) -> Tuple[bool, Optional[str]]:
        """Validate that exit rules are defined and valid.
        
        Args:
            exit_rules: List of exit rules to validate
            
        Returns:
            Tuple of (valid, error_message)
        """
        if not exit_rules:
            return False, "No exit plan defined. Every trade needs exit logic before entry."
        
        mandatory_rules = [r for r in exit_rules if r.is_mandatory]
        if not mandatory_rules:
            return False, "No mandatory exit rules defined."
        
        # Validate that at least one of each critical rule type exists
        rule_types = {r.rule_type for r in mandatory_rules}
        
        # At minimum, need either profit target or stop loss
        has_profit_or_loss = (
            ExitRuleType.PROFIT_TARGET in rule_types or
            ExitRuleType.STOP_LOSS in rule_types
        )
        
        if not has_profit_or_loss:
            return False, "Exit plan must include either profit target or stop loss."
        
        # Validate trigger values are positive
        for rule in mandatory_rules:
            if rule.trigger_value <= 0:
                return False, f"Exit rule {rule.rule_type.value} has invalid trigger value: {rule.trigger_value}"
        
        return True, None

    @staticmethod
    def generate_default_exit_rules(
        entry_price: float,
        max_loss: float,
        expected_profit: float,
        days_to_expiration: int,
        risk_level: RiskLevel,
    ) -> List[ExitRule]:
        """Generate default exit rules based on trade parameters.
        
        Args:
            entry_price: Entry price of the trade
            max_loss: Maximum loss in dollars
            expected_profit: Expected profit in dollars
            days_to_expiration: Days until option expiration
            risk_level: User's risk level
            
        Returns:
            List of default exit rules
        """
        rules = []
        
        # Stop loss: at max_loss level
        stop_loss_price = entry_price - max_loss
        rules.append(ExitRule(
            rule_type=ExitRuleType.STOP_LOSS,
            trigger_value=stop_loss_price,
            description=f"Stop loss at ${stop_loss_price:.2f} (max loss: ${max_loss:.2f})",
            is_mandatory=True,
        ))
        
        # Profit target: at expected_profit level
        profit_target_price = entry_price + expected_profit
        rules.append(ExitRule(
            rule_type=ExitRuleType.PROFIT_TARGET,
            trigger_value=profit_target_price,
            description=f"Profit target at ${profit_target_price:.2f} (expected profit: ${expected_profit:.2f})",
            is_mandatory=True,
        ))
        
        # Time-based exit: exit at 50% of DTE
        exit_dte = max(1, days_to_expiration // 2)
        rules.append(ExitRule(
            rule_type=ExitRuleType.TIME_BASED,
            trigger_value=float(exit_dte),
            description=f"Exit if {exit_dte} days remain to expiration",
            is_mandatory=False,
        ))
        
        # Expiration exit: always exit at expiration
        rules.append(ExitRule(
            rule_type=ExitRuleType.EXPIRATION_EXIT,
            trigger_value=float(days_to_expiration),
            description=f"Exit at expiration ({days_to_expiration} days)",
            is_mandatory=True,
        ))
        
        # Trailing stop for high-risk profiles
        if risk_level == RiskLevel.HIGH:
            trailing_stop_pct = 0.10  # 10% trailing stop
            rules.append(ExitRule(
                rule_type=ExitRuleType.TRAILING_STOP,
                trigger_value=trailing_stop_pct,
                description=f"Trailing stop at {trailing_stop_pct:.1%} of peak profit",
                is_mandatory=False,
            ))
        
        return rules


class RiskEngine:
    """Risk management engine for validating trades against guardrails."""

    def __init__(self, risk_level: RiskLevel = RiskLevel.MEDIUM):
        """Initialize risk engine.
        
        Args:
            risk_level: Risk level for this engine
        """
        self.risk_level = risk_level
        self.risk_config = self._get_risk_config(risk_level)

    def _get_risk_config(self, risk_level: RiskLevel) -> Dict[str, Any]:
        """Get risk configuration for risk level.
        
        Args:
            risk_level: Risk level
            
        Returns:
            Dict of risk parameters
        """
        configs = {
            RiskLevel.LOW: {
                "max_loss_pct": 2.0,
                "max_contracts": 5,
                "max_daily_loss_pct": 3.0,
                "max_open_positions": 5,
                "max_bid_ask_spread_pct": 0.05,
                "min_volume": 50,
                "min_open_interest": 100,
                "earnings_buffer_days": 5,
            },
            RiskLevel.MEDIUM: {
                "max_loss_pct": 5.0,
                "max_contracts": 10,
                "max_daily_loss_pct": 5.0,
                "max_open_positions": 10,
                "max_bid_ask_spread_pct": 0.10,
                "min_volume": 20,
                "min_open_interest": 50,
                "earnings_buffer_days": 3,
            },
            RiskLevel.HIGH: {
                "max_loss_pct": 10.0,
                "max_contracts": 20,
                "max_daily_loss_pct": 10.0,
                "max_open_positions": 20,
                "max_bid_ask_spread_pct": 0.15,
                "min_volume": 10,
                "min_open_interest": 20,
                "earnings_buffer_days": 1,
            },
        }
        return configs.get(risk_level, configs[RiskLevel.MEDIUM])

    def validate_trade(
        self,
        contract: OptionContract,
        max_loss_pct: float,
        num_contracts: int,
        current_daily_loss_pct: float = 0.0,
        current_open_positions: int = 0,
        is_live_trading: bool = False,
        user_approved_live_trading: bool = False,
        exit_rules: Optional[List[ExitRule]] = None,
    ) -> RiskGuardrailResult:
        """Validate a trade against all risk guardrails.
        
        Args:
            contract: Option contract to validate
            max_loss_pct: Maximum loss as percentage
            num_contracts: Number of contracts
            current_daily_loss_pct: Current daily loss percentage
            current_open_positions: Current number of open positions
            is_live_trading: Whether this is a live trade
            user_approved_live_trading: Whether user approved live trading
            exit_rules: Exit rules for the trade
            
        Returns:
            RiskGuardrailResult with pass/fail and reason
        """
        # Check exit rules first
        if exit_rules is None or len(exit_rules) == 0:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.NO_EXIT_PLAN,
                message="No exit plan defined. Every trade needs exit logic before entry.",
            )
        
        exit_valid, exit_msg = ExitRuleValidator.validate_exit_rules(exit_rules)
        if not exit_valid:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.NO_EXIT_PLAN,
                message=exit_msg or "Invalid exit plan.",
            )
        
        # Check max loss per trade
        if max_loss_pct > self.risk_config["max_loss_pct"]:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_LOSS_EXCEEDED,
                message=f"Max loss {max_loss_pct:.2f}% exceeds {self.risk_level.value} limit of {self.risk_config['max_loss_pct']:.2f}%",
            )
        
        # Check max contracts per trade
        if num_contracts > self.risk_config["max_contracts"]:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_CONTRACTS_EXCEEDED,
                message=f"Contracts {num_contracts} exceeds {self.risk_level.value} limit of {self.risk_config['max_contracts']}",
            )
        
        # Check max daily loss
        total_daily_loss = current_daily_loss_pct + max_loss_pct
        if total_daily_loss > self.risk_config["max_daily_loss_pct"]:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_DAILY_LOSS_EXCEEDED,
                message=f"Total daily loss {total_daily_loss:.2f}% exceeds {self.risk_level.value} limit of {self.risk_config['max_daily_loss_pct']:.2f}%",
            )
        
        # Check max open positions
        if current_open_positions >= self.risk_config["max_open_positions"]:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.MAX_OPEN_POSITIONS_EXCEEDED,
                message=f"Open positions {current_open_positions} at {self.risk_level.value} limit of {self.risk_config['max_open_positions']}",
            )
        
        # Check bid-ask spread
        if contract.bid and contract.ask:
            mid_price = (contract.bid + contract.ask) / 2
            spread_pct = (contract.ask - contract.bid) / mid_price if mid_price > 0 else 1.0
            if spread_pct > self.risk_config["max_bid_ask_spread_pct"]:
                return RiskGuardrailResult(
                    passed=False,
                    reason=RejectionReason.BID_ASK_SPREAD_TOO_WIDE,
                    message=f"Bid-ask spread {spread_pct:.2%} exceeds {self.risk_level.value} limit of {self.risk_config['max_bid_ask_spread_pct']:.2%}",
                )
        
        # Check volume
        if (contract.volume or 0) < self.risk_config["min_volume"]:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.VOLUME_TOO_LOW,
                message=f"Volume {contract.volume or 0} below {self.risk_level.value} minimum of {self.risk_config['min_volume']}",
            )
        
        # Check open interest
        if (contract.open_interest or 0) < self.risk_config["min_open_interest"]:
            return RiskGuardrailResult(
                passed=False,
                reason=RejectionReason.OPEN_INTEREST_TOO_LOW,
                message=f"Open interest {contract.open_interest or 0} below {self.risk_level.value} minimum of {self.risk_config['min_open_interest']}",
            )
        
        # Check earnings window
        if contract.earnings_date:
            try:
                earnings_dt = datetime.strptime(contract.earnings_date, "%Y-%m-%d")
                days_to_earnings = (earnings_dt - datetime.now()).days
                buffer = self.risk_config["earnings_buffer_days"]
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
        if contract.event_risks:
            acceptable, reason_msg = EventRiskAnalyzer.assess_event_risk(
                contract.event_risks,
                self.risk_level,
                contract.days_to_expiration,
            )
            if not acceptable:
                return RiskGuardrailResult(
                    passed=False,
                    reason=RejectionReason.EVENT_RISK_TOO_HIGH,
                    message=reason_msg or "Event risk too high",
                )
        
        return RiskGuardrailResult(passed=True)
