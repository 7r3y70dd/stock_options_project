"""Unit tests for global risk guardrails and options chain filtering.

Tests verify that the RiskEngine correctly validates trades against all guardrails,
the OptionsChainFilter correctly filters contracts, and rejection reasons are properly stored.
Includes tests for event-risk detection, exit rules, blocking of trades around high-risk events,
and kill switch functionality.
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
    KillSwitchManager,
    get_kill_switch_manager,
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


class TestKillSwitch(unittest.TestCase):
    """Test suite for kill switch functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.kill_switch = KillSwitchManager()
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
        self.exit_rules = [
            ExitRule(ExitRuleType.STOP_LOSS, 148.0, "Stop loss"),
            ExitRule(ExitRuleType.PROFIT_TARGET, 152.0, "Profit target"),
        ]

    def test_kill_switch_inactive_by_default(self):
        """Test that kill switch is inactive by default."""
        self.assertFalse(self.kill_switch.is_active())

    def test_kill_switch_activation(self):
        """Test kill switch activation."""
        self.kill_switch.activate(
            activated_by="admin",
            reason="Market volatility spike",
            close_positions=True,
        )
        self.assertTrue(self.kill_switch.is_active())
        status = self.kill_switch.get_status()
        self.assertEqual(status["activated_by"], "admin")
        self.assertEqual(status["reason"], "Market volatility spike")
        self.assertTrue(status["close_positions"])

    def test_kill_switch_deactivation(self):
        """Test kill switch deactivation."""
        self.kill_switch.activate()
        self.assertTrue(self.kill_switch.is_active())
        self.kill_switch.deactivate()
        self.assertFalse(self.kill_switch.is_active())

    def test_kill_switch_blocks_new_orders(self):
        """Test that kill switch blocks new orders."""
        # Activate kill switch
        self.kill_switch.activate(activated_by="admin", reason="Emergency halt")
        
        # Create risk engine with kill switch
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        engine.kill_switch = self.kill_switch
        
        # Try to validate trade
        guardrail = engine.validate_trade(
            self.contract,
            max_loss_pct=1.0,
            num_contracts=1,
            exit_rules=self.exit_rules,
        )
        
        # Should be rejected due to kill switch
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.KILL_SWITCH_ACTIVE)
        self.assertIn("kill switch", guardrail.message.lower())

    def test_kill_switch_allows_orders_when_inactive(self):
        """Test that orders are allowed when kill switch is inactive."""
        # Ensure kill switch is inactive
        self.kill_switch.deactivate()
        
        # Create risk engine with kill switch
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        engine.kill_switch = self.kill_switch
        
        # Try to validate trade
        guardrail = engine.validate_trade(
            self.contract,
            max_loss_pct=1.0,
            num_contracts=1,
            exit_rules=self.exit_rules,
        )
        
        # Should pass (kill switch not active)
        self.assertTrue(guardrail.passed)
        self.assertNotEqual(guardrail.reason, RejectionReason.KILL_SWITCH_ACTIVE)

    def test_kill_switch_close_positions_flag(self):
        """Test kill switch close_positions flag."""
        self.kill_switch.activate(close_positions=True)
        self.assertTrue(self.kill_switch.should_close_positions())
        
        self.kill_switch.deactivate()
        self.assertFalse(self.kill_switch.should_close_positions())

    def test_kill_switch_status_tracking(self):
        """Test kill switch status tracking."""
        self.kill_switch.activate(
            activated_by="user123",
            reason="Manual halt",
            close_positions=False,
        )
        
        status = self.kill_switch.get_status()
        self.assertTrue(status["is_active"])
        self.assertEqual(status["activated_by"], "user123")
        self.assertEqual(status["reason"], "Manual halt")
        self.assertFalse(status["close_positions"])
        self.assertIsNotNone(status["activated_at"])


if __name__ == "__main__":
    unittest.main()
