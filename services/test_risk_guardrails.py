"""Unit tests for global risk guardrails and options chain filtering.

Tests verify that the RiskEngine correctly validates trades against all guardrails,
the OptionsChainFilter correctly filters contracts, and rejection reasons are properly stored.
Includes tests for event-risk detection and blocking of trades around high-risk events.
"""

import unittest
from datetime import datetime, timedelta

from services import RiskLevel, RejectionReason, EventType
from services.options_service import (
    RiskEngine,
    OptionContract,
    OptionsChainFilter,
    FilteredContract,
    EventRiskAnalyzer,
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
        )
        # Should pass live trading check (may fail others)
        self.assertTrue(guardrail.passed or guardrail.reason != RejectionReason.LIVE_TRADING_NOT_APPROVED)


class TestEventRiskDetection(unittest.TestCase):
    """Test suite for event-risk detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = EventRiskAnalyzer()
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

    def test_detect_earnings_event(self):
        """Test detection of earnings event."""
        contract = OptionContract(
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
            earnings_date="2024-02-10",
        )
        events = self.analyzer.detect_events("AAPL", contract)
        self.assertTrue(any(e[0] == EventType.EARNINGS for e in events))

    def test_detect_fda_event_from_news(self):
        """Test detection of FDA event from news articles."""
        news = [
            {
                "title": "FDA Approves New Drug",
                "description": "FDA approval for AAPL's new treatment",
            }
        ]
        events = self.analyzer.detect_events("AAPL", self.contract, news)
        self.assertTrue(any(e[0] == EventType.FDA_DECISION for e in events))

    def test_detect_lawsuit_event_from_news(self):
        """Test detection of lawsuit event from news articles."""
        news = [
            {
                "title": "AAPL Sued for Patent Infringement",
                "description": "Major lawsuit filed against AAPL",
            }
        ]
        events = self.analyzer.detect_events("AAPL", self.contract, news)
        self.assertTrue(any(e[0] == EventType.LAWSUIT for e in events))

    def test_detect_m_and_a_event_from_news(self):
        """Test detection of M&A event from news articles."""
        news = [
            {
                "title": "AAPL Acquisition Rumors",
                "description": "Reports of potential merger with competitor",
            }
        ]
        events = self.analyzer.detect_events("AAPL", self.contract, news)
        self.assertTrue(any(e[0] == EventType.M_AND_A for e in events))

    def test_detect_sec_investigation_event_from_news(self):
        """Test detection of SEC investigation event from news articles."""
        news = [
            {
                "title": "SEC Investigates AAPL",
                "description": "Securities and Exchange Commission opens investigation",
            }
        ]
        events = self.analyzer.detect_events("AAPL", self.contract, news)
        self.assertTrue(any(e[0] == EventType.SEC_INVESTIGATION for e in events))

    def test_detect_analyst_upgrade_from_news(self):
        """Test detection of analyst upgrade from news articles."""
        news = [
            {
                "title": "Goldman Sachs Upgrades AAPL",
                "description": "Analyst raised price target to $200",
            }
        ]
        events = self.analyzer.detect_events("AAPL", self.contract, news)
        self.assertTrue(any(e[0] == EventType.ANALYST_UPGRADE for e in events))

    def test_detect_analyst_downgrade_from_news(self):
        """Test detection of analyst downgrade from news articles."""
        news = [
            {
                "title": "Morgan Stanley Downgrades AAPL",
                "description": "Analyst lowered rating to underperform",
            }
        ]
        events = self.analyzer.detect_events("AAPL", self.contract, news)
        self.assertTrue(any(e[0] == EventType.ANALYST_DOWNGRADE for e in events))

    def test_detect_macro_event_from_news(self):
        """Test detection of macro event from news articles."""
        news = [
            {
                "title": "Fed Raises Interest Rates",
                "description": "Federal Reserve increases rates by 25 basis points",
            }
        ]
        events = self.analyzer.detect_events("AAPL", self.contract, news)
        self.assertTrue(any(e[0] == EventType.MACRO_EVENT for e in events))

    def test_assess_event_risk_low_risk_rejects_earnings(self):
        """Test that low risk level rejects earnings events."""
        events = [(EventType.EARNINGS, "Earnings on 2024-02-10")]
        acceptable, reason = self.analyzer.assess_event_risk(
            events, RiskLevel.LOW, days_to_expiration=30
        )
        self.assertFalse(acceptable)
        self.assertIsNotNone(reason)

    def test_assess_event_risk_low_risk_rejects_fda(self):
        """Test that low risk level rejects FDA events."""
        events = [(EventType.FDA_DECISION, "FDA decision pending")]
        acceptable, reason = self.analyzer.assess_event_risk(
            events, RiskLevel.LOW, days_to_expiration=30
        )
        self.assertFalse(acceptable)
        self.assertIsNotNone(reason)

    def test_assess_event_risk_medium_risk_allows_far_earnings(self):
        """Test that medium risk allows earnings far in the future."""
        events = [(EventType.EARNINGS, "Earnings on 2024-03-15")]
        acceptable, reason = self.analyzer.assess_event_risk(
            events, RiskLevel.MEDIUM, days_to_expiration=60
        )
        self.assertTrue(acceptable)

    def test_assess_event_risk_medium_risk_rejects_close_earnings(self):
        """Test that medium risk rejects earnings within 30 days."""
        events = [(EventType.EARNINGS, "Earnings on 2024-02-10")]
        acceptable, reason = self.analyzer.assess_event_risk(
            events, RiskLevel.MEDIUM, days_to_expiration=20
        )
        self.assertFalse(acceptable)
        self.assertIsNotNone(reason)

    def test_assess_event_risk_high_risk_allows_most_events(self):
        """Test that high risk allows most events except critical ones close to expiration."""
        events = [(EventType.EARNINGS, "Earnings on 2024-02-10")]
        acceptable, reason = self.analyzer.assess_event_risk(
            events, RiskLevel.HIGH, days_to_expiration=30
        )
        self.assertTrue(acceptable)

    def test_assess_event_risk_high_risk_rejects_critical_close(self):
        """Test that high risk rejects critical events within 7 days."""
        events = [(EventType.SEC_INVESTIGATION, "SEC investigation announced")]
        acceptable, reason = self.analyzer.assess_event_risk(
            events, RiskLevel.HIGH, days_to_expiration=5
        )
        self.assertFalse(acceptable)
        self.assertIsNotNone(reason)

    def test_event_risk_blocks_trade_in_risk_engine(self):
        """Test that event risk blocks trades in RiskEngine."""
        contract = OptionContract(
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
            days_to_expiration=20,
            event_risks=[(EventType.EARNINGS, "Earnings on 2024-02-10")],
        )
        engine = RiskEngine(risk_level=RiskLevel.MEDIUM)
        guardrail = engine.validate_trade(
            contract, max_loss_pct=1.0, num_contracts=1
        )
        self.assertFalse(guardrail.passed)
        self.assertEqual(guardrail.reason, RejectionReason.EVENT_RISK_TOO_HIGH)


class TestOptionsChainFilter(unittest.TestCase):
    """Test suite for options chain filtering."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = OptionsChainFilter(risk_level=RiskLevel.MEDIUM)
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

    def test_filter_accepts_good_contract(self):
        """Test that filter accepts a good contract."""
        result = self.filter._filter_single_contract(
            self.contract, self.filter.get_risk_config()
        )
        self.assertTrue(result.accepted)
        self.assertIsNone(result.rejection_reason)

    def test_filter_rejects_expired_contract(self):
        """Test that filter rejects expired contracts."""
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
        result = self.filter._filter_single_contract(
            expired_contract, self.filter.get_risk_config()
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.rejection_reason, RejectionReason.EXPIRED)

    def test_filter_detects_event_risk(self):
        """Test that filter detects and stores event risks."""
        news = [
            {
                "title": "AAPL Earnings Announcement",
                "description": "Company reports quarterly earnings",
            }
        ]
        result = self.filter._filter_single_contract(
            self.contract, self.filter.get_risk_config(), news
        )
        # Contract should have event_risks populated
        self.assertIsNotNone(result.contract.event_risks)
        self.assertTrue(len(result.contract.event_risks) > 0)


if __name__ == "__main__":
    unittest.main()
