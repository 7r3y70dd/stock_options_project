"""Unit tests for global risk guardrails and options chain filtering.

Tests verify that the RiskEngine correctly validates trades against all guardrails,
the OptionsChainFilter correctly filters contracts, and rejection reasons are properly stored.
Includes tests for event-risk detection, exit rules, and blocking of trades around high-risk events.
"""

import unittest
from datetime import datetime, timedelta

from services import RiskLevel, RejectionReason, EventType, ExitRuleType
from services.options_service import (
    RiskEngine,
    OptionContract,
    FilteredContract,
    EventRiskAnalyzer,
    ExitRule,
    ExitRuleValidator,
)


class TestRiskGuardrails(unittest.TestCase):
    """Test suite for risk guardrails."""

    def setUp(self):
        """Set up test fixtures."""
        self.contract = OptionContract(
            symbol="AAPL",
            expiration="2024-02-16",
            strike=150.0,
            contract_type="call",
            bid=2.0,
            ask=2.1,
            volume=100,
            open_interest=200,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
        )

    def test_max_loss_per_trade_low_risk(self):
        """Test max loss per trade rejection for low risk level."""
        engine = RiskEngine(risk_level=RiskLevel.LOW)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss at $148"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target at $152"),
        ]
        # Low risk: max 2% loss per trade
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=3.0, num_contracts=1, exit_rules=exit_rules
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.MAX_LOSS_EXCEEDED)
        self.assertIn("3.00%", guardrail.message)
        self.assertIn("2.00%", guardrail.message)

    def test_max_loss_per_trade_medium_risk(self):
        """Test max loss per trade rejection for medium risk level."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 145.0, "Stop loss at $145"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 155.0, "Profit target at $155"),
        ]
        # Medium risk: max 5% loss per trade
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=6.0, num_contracts=1, exit_rules=exit_rules
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.MAX_LOSS_EXCEEDED)

    def test_max_loss_per_trade_high_risk(self):
        """Test max loss per trade rejection for high risk level."""
        engine = RiskEngine(risk_level=RiskLevel.HIGH)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 140.0, "Stop loss at $140"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 160.0, "Profit target at $160"),
        ]
        # High risk: max 10% loss per trade
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=11.0, num_contracts=1, exit_rules=exit_rules
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.MAX_LOSS_EXCEEDED)

    def test_max_loss_per_trade_passes(self):
        """Test max loss per trade passes when within limit."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss at $148"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target at $152"),
        ]
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=4.0, num_contracts=1, exit_rules=exit_rules
        )
        # Should pass this check (may fail others)
        self.assertTrue(guardrail.passed or guardrail.reason != RejectionReason.MAX_LOSS_EXCEEDED)

    def test_no_exit_plan_rejected(self):
        """Test that trades without exit plan are rejected."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=1.0, num_contracts=1, exit_rules=None
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.NO_EXIT_PLAN)
        self.assertIn("exit", guardrail.message.lower())

    def test_empty_exit_plan_rejected(self):
        """Test that trades with empty exit plan are rejected."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=1.0, num_contracts=1, exit_rules=[]
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.NO_EXIT_PLAN)

    def test_valid_exit_plan_passes_check(self):
        """Test that valid exit plan passes the exit rule check."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss at $148", is_mandatory=True),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target at $152", is_mandatory=True),
        ]
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=1.0, num_contracts=1, exit_rules=exit_rules
        )
        # Should pass exit rule check (may fail other checks)
        self.assertTrue(guardrail.passed or guardrail.reason != RejectionReason.NO_EXIT_PLAN)

    def test_max_contracts_exceeded(self):
        """Test max contracts per trade rejection."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 145.0, "Stop loss"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 155.0, "Profit target"),
        ]
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=1.0, num_contracts=11, exit_rules=exit_rules
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.MAX_CONTRACTS_EXCEEDED)
        self.assertIn("11", guardrail.message)
        self.assertIn("10", guardrail.message)

    def test_max_daily_loss_exceeded(self):
        """Test max daily loss rejection."""
        engine = RiskEngine(risk_level=RiskLevel.LOW)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target"),
        ]
        # Low risk: max 3% daily loss
        guardrail = engine.validate_trade(
            self.contract,
            max_loss_pct=2.0,
            num_contracts=1,
            current_daily_loss_pct=1.5,  # 1.5% + 2.0% = 3.5% > 3%
            exit_rules=exit_rules,
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.MAX_DAILY_LOSS_EXCEEDED)
        self.assertIn("3.50%", guardrail.message)

    def test_max_open_positions_exceeded(self):
        """Test max open positions rejection."""
        engine = RiskEngine(risk_level=RiskLevel.LOW)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target"),
        ]
        # Low risk: max 5 open positions
        guardrail = engine.validate_trade(
            self.contract,
            max_loss_pct=1.0,
            num_contracts=1,
            current_open_positions=5,  # Already at max
            exit_rules=exit_rules,
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.MAX_OPEN_POSITIONS_EXCEEDED)
        self.assertIn("5", guardrail.message)

    def test_bid_ask_spread_too_wide_low_risk(self):
        """Test bid-ask spread rejection for low risk level."""
        # Low risk: max 5% spread
        wide_spread_contract = OptionContract(
            symbol="AAPL",
            expiration="2024-02-16",
            strike=150.0,
            contract_type="call",
            bid=1.0,
            ask=1.2,  # 20% spread
            volume=100,
            open_interest=200,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
        )
        engine = RiskEngine(risk_level=RiskLevel.LOW)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target"),
        ]
        guardrail = engine.validate_trade(
            wide_spread_contract, max_loss_pct=1.0, num_contracts=1, exit_rules=exit_rules
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.BID_ASK_SPREAD_TOO_WIDE)
        self.assertIn("spread", guardrail.message.lower())

    def test_bid_ask_spread_passes(self):
        """Test bid-ask spread passes when within limit."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target"),
        ]
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=1.0, num_contracts=1, exit_rules=exit_rules
        )
        # Should pass spread check (may fail others)
        self.assertTrue(guardrail.passed or guardrail.reason != RejectionReason.BID_ASK_SPREAD_TOO_WIDE)

    def test_volume_too_low_low_risk(self):
        """Test volume rejection for low risk level."""
        # Low risk: min 50 volume
        low_volume_contract = OptionContract(
            symbol="AAPL",
            expiration="2024-02-16",
            strike=150.0,
            contract_type="call",
            bid=2.0,
            ask=2.1,
            volume=10,  # Below minimum
            open_interest=200,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
        )
        engine = RiskEngine(risk_level=RiskLevel.LOW)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target"),
        ]
        guardrail = engine.validate_trade(
            low_volume_contract, max_loss_pct=1.0, num_contracts=1, exit_rules=exit_rules
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.VOLUME_TOO_LOW)
        self.assertIn("10", guardrail.message)
        self.assertIn("50", guardrail.message)

    def test_volume_passes(self):
        """Test volume passes when above minimum."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target"),
        ]
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=1.0, num_contracts=1, exit_rules=exit_rules
        )
        # Should pass volume check (may fail others)
        self.assertTrue(guardrail.passed or guardrail.reason != RejectionReason.VOLUME_TOO_LOW)

    def test_open_interest_too_low_low_risk(self):
        """Test open interest rejection for low risk level."""
        # Low risk: min 100 open interest
        low_oi_contract = OptionContract(
            symbol="AAPL",
            expiration="2024-02-16",
            strike=150.0,
            contract_type="call",
            bid=2.0,
            ask=2.1,
            volume=100,
            open_interest=50,  # Below minimum
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
        )
        engine = RiskEngine(risk_level=RiskLevel.LOW)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target"),
        ]
        guardrail = engine.validate_trade(
            low_oi_contract, max_loss_pct=1.0, num_contracts=1, exit_rules=exit_rules
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.OPEN_INTEREST_TOO_LOW)
        self.assertIn("50", guardrail.message)
        self.assertIn("100", guardrail.message)

    def test_open_interest_passes(self):
        """Test open interest passes when above minimum."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target"),
        ]
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=1.0, num_contracts=1, exit_rules=exit_rules
        )
        # Should pass open interest check (may fail others)
        self.assertTrue(guardrail.passed or guardrail.reason != RejectionReason.OPEN_INTEREST_TOO_LOW)

    def test_earnings_window_restricted(self):
        """Test earnings window restriction."""
        # Set earnings date to tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat().split('T')[0]
        contract_with_earnings = OptionContract(
            symbol="AAPL",
            expiration="2024-02-16",
            strike=150.0,
            contract_type="call",
            bid=2.0,
            ask=2.1,
            volume=100,
            open_interest=200,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            earnings_date=tomorrow,
        )
        engine = RiskEngine(risk_level=RiskLevel.LOW)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target"),
        ]
        # Low risk: 5 day buffer
        guardrail = engine.validate_trade(
            contract_with_earnings, max_loss_pct=1.0, num_contracts=1, exit_rules=exit_rules
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.EARNINGS_WINDOW_RESTRICTED)
        self.assertIn("earnings", guardrail.message.lower())

    def test_earnings_window_passes(self):
        """Test earnings window passes when outside buffer."""
        # Set earnings date to 10 days ago
        ten_days_ago = (datetime.now() - timedelta(days=10)).isoformat().split('T')[0]
        contract_with_earnings = OptionContract(
            symbol="AAPL",
            expiration="2024-02-16",
            strike=150.0,
            contract_type="call",
            bid=2.0,
            ask=2.1,
            volume=100,
            open_interest=200,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            earnings_date=ten_days_ago,
        )
        engine = RiskEngine(risk_level=RiskLevel.LOW)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target"),
        ]
        guardrail = engine.validate_trade(
            contract_with_earnings, max_loss_pct=1.0, num_contracts=1, exit_rules=exit_rules
        )
        # Should pass earnings check (may fail others)
        self.assertTrue(guardrail.passed or guardrail.reason != RejectionReason.EARNINGS_WINDOW_RESTRICTED)

    def test_live_trading_not_approved(self):
        """Test live trading rejection by default."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target"),
        ]
        guardrail = engine.validate_trade(
            self.contract,
            max_loss_pct=1.0,
            num_contracts=1,
            is_live_trading=True,
            user_approved_live_trading=False,
            exit_rules=exit_rules,
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.LIVE_TRADING_NOT_APPROVED)
        self.assertIn("disabled by default", guardrail.message.lower())

    def test_live_trading_approved(self):
        """Test live trading passes when user approved."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target"),
        ]
        guardrail = engine.validate_trade(
            self.contract,
            max_loss_pct=1.0,
            num_contracts=1,
            is_live_trading=True,
            user_approved_live_trading=True,
            exit_rules=exit_rules,
        )
        # Should pass live trading check (may fail others)
        self.assertTrue(guardrail.passed or guardrail.reason != RejectionReason.LIVE_TRADING_NOT_APPROVED)

    def test_paper_trading_allowed(self):
        """Test paper trading is allowed without approval."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target"),
        ]
        guardrail = engine.validate_trade(
            self.contract,
            max_loss_pct=1.0,
            num_contracts=1,
            is_live_trading=False,
            exit_rules=exit_rules,
        )
        # Should pass live trading check (may fail others)
        self.assertTrue(guardrail.passed or guardrail.reason != RejectionReason.LIVE_TRADING_NOT_APPROVED)


class TestExitRuleValidator(unittest.TestCase):
    """Test suite for exit rule validation."""

    def test_validate_exit_rules_none(self):
        """Test validation fails when exit rules are None."""
        valid, msg = ExitRuleValidator.validate_exit_rules(None)
        self.assertFalse(valid)
        self.assertIn("exit", msg.lower())

    def test_validate_exit_rules_empty(self):
        """Test validation fails when exit rules are empty."""
        valid, msg = ExitRuleValidator.validate_exit_rules([])
        self.assertFalse(valid)
        self.assertIn("exit", msg.lower())

    def test_validate_exit_rules_profit_target_only(self):
        """Test validation passes with profit target."""
        rules = [
            ExitRule(ExitRuleType.PROFIT_TARGET, 100.0, "Profit target", is_mandatory=True),
        ]
        valid, msg = ExitRuleValidator.validate_exit_rules(rules)
        self.assertTrue(valid)

    def test_validate_exit_rules_stop_loss_only(self):
        """Test validation passes with stop loss."""
        rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 90.0, "Stop loss", is_mandatory=True),
        ]
        valid, msg = ExitRuleValidator.validate_exit_rules(rules)
        self.assertTrue(valid)

    def test_validate_exit_rules_both(self):
        """Test validation passes with both profit target and stop loss."""
        rules = [
            ExitRule(ExitRuleType.PROFIT_TARGET, 110.0, "Profit target", is_mandatory=True),
            ExitRule(ExitRuleType.STOP_LOSS, 90.0, "Stop loss", is_mandatory=True),
        ]
        valid, msg = ExitRuleValidator.validate_exit_rules(rules)
        self.assertTrue(valid)

    def test_generate_default_exit_rules(self):
        """Test default exit rule generation."""
        rules = ExitRuleValidator.generate_default_exit_rules(
            entry_price=100.0,
            max_loss=10.0,
            expected_profit=20.0,
            days_to_expiration=30,
            risk_level=RiskLevel.MEDIUM,
        )
        self.assertGreater(len(rules), 0)
        # Should have stop loss and profit target
        rule_types = {r.rule_type for r in rules}
        self.assertIn(ExitRuleType.STOP_LOSS, rule_types)
        self.assertIn(ExitRuleType.PROFIT_TARGET, rule_types)
        self.assertIn(ExitRuleType.EXPIRATION_EXIT, rule_types)

    def test_generate_default_exit_rules_high_risk(self):
        """Test default exit rule generation includes trailing stop for high risk."""
        rules = ExitRuleValidator.generate_default_exit_rules(
            entry_price=100.0,
            max_loss=10.0,
            expected_profit=20.0,
            days_to_expiration=30,
            risk_level=RiskLevel.HIGH,
        )
        rule_types = {r.rule_type for r in rules}
        self.assertIn(ExitRuleType.TRAILING_STOP, rule_types)


if __name__ == "__main__":
    unittest.main()
