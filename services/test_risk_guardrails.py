"""Unit tests for global risk guardrails and options chain filtering.

Tests verify that the RiskEngine correctly validates trades against all guardrails,
the OptionsChainFilter correctly filters contracts, and rejection reasons are properly stored.
"""

import unittest
from datetime import datetime, timedelta

from services import RiskLevel, RejectionReason
from services.options_service import RiskEngine, OptionContract, OptionsChainFilter, FilteredContract


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
        # Low risk: max 2% loss per trade
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=3.0, num_contracts=1
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.MAX_LOSS_EXCEEDED)
        self.assertIn("3.00%", guardrail.message)
        self.assertIn("2.00%", guardrail.message)

    def test_max_loss_per_trade_medium_risk(self):
        """Test max loss per trade rejection for medium risk level."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        # Medium risk: max 5% loss per trade
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=6.0, num_contracts=1
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.MAX_LOSS_EXCEEDED)

    def test_max_loss_per_trade_high_risk(self):
        """Test max loss per trade rejection for high risk level."""
        engine = RiskEngine(risk_level=RiskLevel.HIGH)
        # High risk: max 10% loss per trade
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=11.0, num_contracts=1
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.MAX_LOSS_EXCEEDED)

    def test_max_loss_per_trade_passes(self):
        """Test max loss per trade passes when within limit."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=4.0, num_contracts=1
        )
        # Should pass this check (may fail others)
        self.assertTrue(guardrail.passed or guardrail.reason != RejectionReason.MAX_LOSS_EXCEEDED)

    def test_max_contracts_exceeded(self):
        """Test max contracts per trade rejection."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=1.0, num_contracts=11
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.MAX_CONTRACTS_EXCEEDED)
        self.assertIn("11", guardrail.message)
        self.assertIn("10", guardrail.message)

    def test_max_daily_loss_exceeded(self):
        """Test max daily loss rejection."""
        engine = RiskEngine(risk_level=RiskLevel.LOW)
        # Low risk: max 3% daily loss
        guardrail = engine.validate_trade(
            self.contract,
            max_loss_pct=2.0,
            num_contracts=1,
            current_daily_loss_pct=1.5,  # 1.5% + 2.0% = 3.5% > 3%
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.MAX_DAILY_LOSS_EXCEEDED)
        self.assertIn("3.50%", guardrail.message)

    def test_max_open_positions_exceeded(self):
        """Test max open positions rejection."""
        engine = RiskEngine(risk_level=RiskLevel.LOW)
        # Low risk: max 5 open positions
        guardrail = engine.validate_trade(
            self.contract,
            max_loss_pct=1.0,
            num_contracts=1,
            current_open_positions=5,  # Already at max
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
        guardrail = engine.validate_trade(
            wide_spread_contract, max_loss_pct=1.0, num_contracts=1
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.BID_ASK_SPREAD_TOO_WIDE)
        self.assertIn("spread", guardrail.message.lower())

    def test_bid_ask_spread_passes(self):
        """Test bid-ask spread passes when within limit."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=1.0, num_contracts=1
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
        guardrail = engine.validate_trade(
            low_volume_contract, max_loss_pct=1.0, num_contracts=1
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.VOLUME_TOO_LOW)
        self.assertIn("10", guardrail.message)
        self.assertIn("50", guardrail.message)

    def test_volume_passes(self):
        """Test volume passes when above minimum."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=1.0, num_contracts=1
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
        guardrail = engine.validate_trade(
            low_oi_contract, max_loss_pct=1.0, num_contracts=1
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.OPEN_INTEREST_TOO_LOW)
        self.assertIn("50", guardrail.message)
        self.assertIn("100", guardrail.message)

    def test_open_interest_passes(self):
        """Test open interest passes when above minimum."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        guardrail = engine.validate_trade(
            self.contract, max_loss_pct=1.0, num_contracts=1
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
        # Low risk: 5 day buffer
        guardrail = engine.validate_trade(
            contract_with_earnings, max_loss_pct=1.0, num_contracts=1
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
        guardrail = engine.validate_trade(
            contract_with_earnings, max_loss_pct=1.0, num_contracts=1
        )
        # Should pass earnings check (may fail others)
        self.assertTrue(guardrail.passed or guardrail.reason != RejectionReason.EARNINGS_WINDOW_RESTRICTED)

    def test_live_trading_not_approved(self):
        """Test live trading rejection by default."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        guardrail = engine.validate_trade(
            self.contract,
            max_loss_pct=1.0,
            num_contracts=1,
            is_live_trading=True,
            user_approved_live_trading=False,
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.LIVE_TRADING_NOT_APPROVED)
        self.assertIn("disabled by default", guardrail.message.lower())

    def test_live_trading_approved(self):
        """Test live trading passes when user approved."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        guardrail = engine.validate_trade(
            self.contract,
            max_loss_pct=1.0,
            num_contracts=1,
            is_live_trading=True,
            user_approved_live_trading=True,
        )
        # Should pass live trading check (may fail others)
        self.assertTrue(guardrail.passed or guardrail.reason != RejectionReason.LIVE_TRADING_NOT_APPROVED)

    def test_paper_trading_allowed(self):
        """Test paper trading is allowed without approval."""
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        guardrail = engine.validate_trade(
            self.contract,
            max_loss_pct=1.0,
            num_contracts=1,
            is_live_trading=False,
            user_approved_live_trading=False,
        )
        # Should pass live trading check for paper trading
        self.assertTrue(guardrail.passed or guardrail.reason != RejectionReason.LIVE_TRADING_NOT_APPROVED)


class TestOptionsChainFilter(unittest.TestCase):
    """Test suite for options chain filtering."""

    def setUp(self):
        """Set up test fixtures."""
        self.good_contract = OptionContract(
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

    def test_filter_expired_contract(self):
        """Test filtering of expired contracts."""
        expired_contract = OptionContract(
            symbol="AAPL",
            expiration="2024-01-01",
            strike=150.0,
            contract_type="call",
            bid=2.0,
            ask=2.1,
            volume=100,
            open_interest=200,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=0,
        )
        filter_obj = OptionsChainFilter(risk_level=RiskLevel.MEDIUM)
        result = filter_obj._filter_single_contract(expired_contract)
        self.assertFalse(result.passed)
        self.assertEqual(result.rejection_reason, RejectionReason.EXPIRED)
        self.assertIn("expired", result.rejection_message.lower())

    def test_filter_missing_bid_ask(self):
        """Test filtering of contracts with missing bid/ask."""
        no_bid_contract = OptionContract(
            symbol="AAPL",
            expiration="2024-02-16",
            strike=150.0,
            contract_type="call",
            bid=None,
            ask=2.1,
            volume=100,
            open_interest=200,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
        )
        filter_obj = OptionsChainFilter(risk_level=RiskLevel.MEDIUM)
        result = filter_obj._filter_single_contract(no_bid_contract)
        self.assertFalse(result.passed)
        self.assertEqual(result.rejection_reason, RejectionReason.MISSING_BID_ASK)
        self.assertIn("bid or ask", result.rejection_message.lower())

    def test_filter_low_volume(self):
        """Test filtering of illiquid contracts (low volume)."""
        low_volume_contract = OptionContract(
            symbol="AAPL",
            expiration="2024-02-16",
            strike=150.0,
            contract_type="call",
            bid=2.0,
            ask=2.1,
            volume=5,  # Below minimum for MEDIUM risk (20)
            open_interest=200,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
        )
        filter_obj = OptionsChainFilter(risk_level=RiskLevel.MEDIUM)
        result = filter_obj._filter_single_contract(low_volume_contract)
        self.assertFalse(result.passed)
        self.assertEqual(result.rejection_reason, RejectionReason.VOLUME_TOO_LOW)
        self.assertIn("volume", result.rejection_message.lower())

    def test_filter_low_open_interest(self):
        """Test filtering of illiquid contracts (low open interest)."""
        low_oi_contract = OptionContract(
            symbol="AAPL",
            expiration="2024-02-16",
            strike=150.0,
            contract_type="call",
            bid=2.0,
            ask=2.1,
            volume=100,
            open_interest=20,  # Below minimum for MEDIUM risk (50)
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
        )
        filter_obj = OptionsChainFilter(risk_level=RiskLevel.MEDIUM)
        result = filter_obj._filter_single_contract(low_oi_contract)
        self.assertFalse(result.passed)
        self.assertEqual(result.rejection_reason, RejectionReason.OPEN_INTEREST_TOO_LOW)
        self.assertIn("open interest", result.rejection_message.lower())

    def test_filter_excessive_spread(self):
        """Test filtering of contracts with excessive bid-ask spread."""
        wide_spread_contract = OptionContract(
            symbol="AAPL",
            expiration="2024-02-16",
            strike=150.0,
            contract_type="call",
            bid=1.0,
            ask=1.3,  # 30% spread, exceeds MEDIUM risk max (10%)
            volume=100,
            open_interest=200,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
        )
        filter_obj = OptionsChainFilter(risk_level=RiskLevel.MEDIUM)
        result = filter_obj._filter_single_contract(wide_spread_contract)
        self.assertFalse(result.passed)
        self.assertEqual(result.rejection_reason, RejectionReason.BID_ASK_SPREAD_TOO_WIDE)
        self.assertIn("spread", result.rejection_message.lower())

    def test_filter_outside_expiration_window(self):
        """Test filtering by expiration window."""
        # Too short expiration for MEDIUM risk (min 5 days)
        short_expiration_contract = OptionContract(
            symbol="AAPL",
            expiration="2024-01-20",
            strike=150.0,
            contract_type="call",
            bid=2.0,
            ask=2.1,
            volume=100,
            open_interest=200,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=2,  # Below minimum
        )
        filter_obj = OptionsChainFilter(risk_level=RiskLevel.MEDIUM)
        result = filter_obj._filter_single_contract(short_expiration_contract)
        self.assertFalse(result.passed)
        self.assertEqual(result.rejection_reason, RejectionReason.OUTSIDE_EXPIRATION_WINDOW)
        self.assertIn("expiration", result.rejection_message.lower())

    def test_filter_passes_good_contract(self):
        """Test that good contracts pass all filters."""
        filter_obj = OptionsChainFilter(risk_level=RiskLevel.MEDIUM)
        result = filter_obj._filter_single_contract(self.good_contract)
        self.assertTrue(result.passed)
        self.assertEqual(result.rejection_reason, RejectionReason.PASSED)
        self.assertIn("passed", result.rejection_message.lower())

    def test_filter_contracts_batch(self):
        """Test filtering a batch of contracts."""
        expired_contract = OptionContract(
            symbol="MSFT",
            expiration="2024-01-01",
            strike=300.0,
            contract_type="call",
            bid=3.0,
            ask=3.1,
            volume=100,
            open_interest=200,
            implied_volatility=0.25,
            underlying_price=300.0,
            days_to_expiration=0,
        )
        contracts = [self.good_contract, expired_contract]
        filter_obj = OptionsChainFilter(risk_level=RiskLevel.MEDIUM)
        results = filter_obj.filter_contracts(contracts)
        
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].passed)
        self.assertFalse(results[1].passed)
        self.assertEqual(results[1].rejection_reason, RejectionReason.EXPIRED)

    def test_rejection_reason_stored(self):
        """Test that rejection reasons are properly stored in FilteredContract."""
        low_volume_contract = OptionContract(
            symbol="AAPL",
            expiration="2024-02-16",
            strike=150.0,
            contract_type="call",
            bid=2.0,
            ask=2.1,
            volume=5,
            open_interest=200,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
        )
        filter_obj = OptionsChainFilter(risk_level=RiskLevel.MEDIUM)
        result = filter_obj._filter_single_contract(low_volume_contract)
        
        # Verify rejection reason is stored
        self.assertIsNotNone(result.rejection_reason)
        self.assertEqual(result.rejection_reason, RejectionReason.VOLUME_TOO_LOW)
        # Verify rejection message is stored
        self.assertIsNotNone(result.rejection_message)
        self.assertGreater(len(result.rejection_message), 0)

    def test_filter_respects_risk_level(self):
        """Test that filter respects different risk levels."""
        # Contract with 30 volume: passes MEDIUM (min 20), fails LOW (min 50)
        medium_volume_contract = OptionContract(
            symbol="AAPL",
            expiration="2024-02-16",
            strike=150.0,
            contract_type="call",
            bid=2.0,
            ask=2.1,
            volume=30,
            open_interest=200,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
        )
        
        # Test with MEDIUM risk
        filter_medium = OptionsChainFilter(risk_level=RiskLevel.MEDIUM)
        result_medium = filter_medium._filter_single_contract(medium_volume_contract)
        # Should pass volume check for MEDIUM
        self.assertTrue(result_medium.passed or result_medium.rejection_reason != RejectionReason.VOLUME_TOO_LOW)
        
        # Test with LOW risk
        filter_low = OptionsChainFilter(risk_level=RiskLevel.LOW)
        result_low = filter_low._filter_single_contract(medium_volume_contract)
        # Should fail volume check for LOW
        self.assertFalse(result_low.passed)
        self.assertEqual(result_low.rejection_reason, RejectionReason.VOLUME_TOO_LOW)


if __name__ == "__main__":
    unittest.main()
