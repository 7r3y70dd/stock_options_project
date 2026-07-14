"""Unit tests for risk guardrails.

Tests verify that RiskGuardrails correctly validates signals and contracts
against all guardrails for low, medium, and high risk levels.
"""

import pytest
from unittest.mock import Mock, MagicMock

from app.risk.guardrails import (
    RiskLevel,
    RejectionReason,
    RiskDecision,
    RiskGuardrails,
)


class TestRiskGuardrails:
    """Test suite for RiskGuardrails."""

    @pytest.fixture
    def guardrails(self):
        """Create a RiskGuardrails instance."""
        return RiskGuardrails()

    @pytest.fixture
    def mock_user_low(self):
        """Create a mock low-risk user."""
        user = Mock()
        user.risk_level = "low"
        user.initial_portfolio_value = 10000.0
        return user

    @pytest.fixture
    def mock_user_medium(self):
        """Create a mock medium-risk user."""
        user = Mock()
        user.risk_level = "medium"
        user.initial_portfolio_value = 10000.0
        return user

    @pytest.fixture
    def mock_user_high(self):
        """Create a mock high-risk user."""
        user = Mock()
        user.risk_level = "high"
        user.initial_portfolio_value = 10000.0
        return user

    @pytest.fixture
    def mock_signal(self):
        """Create a mock signal."""
        signal = Mock()
        signal.strategy_type = "covered_call"
        signal.max_loss = 50.0
        return signal

    @pytest.fixture
    def mock_contract_good(self):
        """Create a mock contract with good liquidity."""
        contract = Mock()
        contract.bid = 2.0
        contract.ask = 2.1
        contract.volume = 500
        contract.open_interest = 1000
        return contract

    @pytest.fixture
    def mock_contract_low_volume(self):
        """Create a mock contract with low volume."""
        contract = Mock()
        contract.bid = 2.0
        contract.ask = 2.1
        contract.volume = 5
        contract.open_interest = 1000
        return contract

    @pytest.fixture
    def mock_contract_low_open_interest(self):
        """Create a mock contract with low open interest."""
        contract = Mock()
        contract.bid = 2.0
        contract.ask = 2.1
        contract.volume = 500
        contract.open_interest = 10
        return contract

    @pytest.fixture
    def mock_contract_wide_spread(self):
        """Create a mock contract with wide bid-ask spread."""
        contract = Mock()
        contract.bid = 1.0
        contract.ask = 3.0
        contract.volume = 500
        contract.open_interest = 1000
        return contract

    # Strategy validation tests

    def test_low_risk_rejects_long_call(self, guardrails, mock_user_low, mock_signal):
        """Test that low risk rejects long_call strategy."""
        mock_signal.strategy_type = "long_call"
        decision = guardrails.validate_signal(mock_user_low, mock_signal)
        assert not decision.approved
        assert RejectionReason.STRATEGY_NOT_ALLOWED in decision.reasons

    def test_low_risk_accepts_covered_call(self, guardrails, mock_user_low, mock_signal):
        """Test that low risk accepts covered_call strategy."""
        mock_signal.strategy_type = "covered_call"
        decision = guardrails.validate_signal(mock_user_low, mock_signal)
        assert decision.approved

    def test_low_risk_accepts_cash_secured_put(
        self, guardrails, mock_user_low, mock_signal
    ):
        """Test that low risk accepts cash_secured_put strategy."""
        mock_signal.strategy_type = "cash_secured_put"
        decision = guardrails.validate_signal(mock_user_low, mock_signal)
        assert decision.approved

    def test_low_risk_rejects_debit_spread(self, guardrails, mock_user_low, mock_signal):
        """Test that low risk rejects debit_spread strategy."""
        mock_signal.strategy_type = "debit_spread"
        decision = guardrails.validate_signal(mock_user_low, mock_signal)
        assert not decision.approved
        assert RejectionReason.STRATEGY_NOT_ALLOWED in decision.reasons

    def test_medium_risk_accepts_debit_spread(
        self, guardrails, mock_user_medium, mock_signal
    ):
        """Test that medium risk accepts debit_spread strategy."""
        mock_signal.strategy_type = "debit_spread"
        decision = guardrails.validate_signal(mock_user_medium, mock_signal)
        assert decision.approved

    def test_medium_risk_rejects_long_call(
        self, guardrails, mock_user_medium, mock_signal
    ):
        """Test that medium risk rejects long_call strategy."""
        mock_signal.strategy_type = "long_call"
        decision = guardrails.validate_signal(mock_user_medium, mock_signal)
        assert not decision.approved
        assert RejectionReason.STRATEGY_NOT_ALLOWED in decision.reasons

    def test_high_risk_accepts_long_call(self, guardrails, mock_user_high, mock_signal):
        """Test that high risk accepts long_call strategy."""
        mock_signal.strategy_type = "long_call"
        decision = guardrails.validate_signal(mock_user_high, mock_signal)
        assert decision.approved

    def test_high_risk_accepts_long_put(self, guardrails, mock_user_high, mock_signal):
        """Test that high risk accepts long_put strategy."""
        mock_signal.strategy_type = "long_put"
        decision = guardrails.validate_signal(mock_user_high, mock_signal)
        assert decision.approved

    # Max loss tests

    def test_max_loss_exceeded_low_risk(self, guardrails, mock_user_low, mock_signal):
        """Test that max loss exceeding 1% is rejected for low risk."""
        mock_signal.max_loss = 150.0  # 1.5% of 10000
        decision = guardrails.validate_signal(mock_user_low, mock_signal)
        assert not decision.approved
        assert RejectionReason.MAX_LOSS_EXCEEDED in decision.reasons

    def test_max_loss_within_limit_low_risk(self, guardrails, mock_user_low, mock_signal):
        """Test that max loss within 1% is accepted for low risk."""
        mock_signal.max_loss = 50.0  # 0.5% of 10000
        decision = guardrails.validate_signal(mock_user_low, mock_signal)
        assert decision.approved

    def test_max_loss_exceeded_medium_risk(
        self, guardrails, mock_user_medium, mock_signal
    ):
        """Test that max loss exceeding 2% is rejected for medium risk."""
        mock_signal.max_loss = 250.0  # 2.5% of 10000
        decision = guardrails.validate_signal(mock_user_medium, mock_signal)
        assert not decision.approved
        assert RejectionReason.MAX_LOSS_EXCEEDED in decision.reasons

    def test_max_loss_within_limit_medium_risk(
        self, guardrails, mock_user_medium, mock_signal
    ):
        """Test that max loss within 2% is accepted for medium risk."""
        mock_signal.max_loss = 150.0  # 1.5% of 10000
        decision = guardrails.validate_signal(mock_user_medium, mock_signal)
        assert decision.approved

    def test_max_loss_exceeded_high_risk(self, guardrails, mock_user_high, mock_signal):
        """Test that max loss exceeding 5% is rejected for high risk."""
        mock_signal.max_loss = 600.0  # 6% of 10000
        decision = guardrails.validate_signal(mock_user_high, mock_signal)
        assert not decision.approved
        assert RejectionReason.MAX_LOSS_EXCEEDED in decision.reasons

    def test_max_loss_within_limit_high_risk(
        self, guardrails, mock_user_high, mock_signal
    ):
        """Test that max loss within 5% is accepted for high risk."""
        mock_signal.max_loss = 400.0  # 4% of 10000
        decision = guardrails.validate_signal(mock_user_high, mock_signal)
        assert decision.approved

    # Liquidity tests

    def test_low_volume_rejects_low_risk(
        self, guardrails, mock_user_low, mock_signal, mock_contract_low_volume
    ):
        """Test that low volume is rejected for low risk."""
        decision = guardrails.validate_contract(
            mock_user_low, mock_contract_low_volume, "covered_call"
        )
        assert not decision.approved
        assert RejectionReason.LOW_VOLUME in decision.reasons

    def test_low_volume_accepted_high_risk(
        self, guardrails, mock_user_high, mock_contract_low_volume
    ):
        """Test that low volume is accepted for high risk."""
        decision = guardrails.validate_contract(
            mock_user_high, mock_contract_low_volume, "long_call"
        )
        assert decision.approved

    def test_low_open_interest_rejects_low_risk(
        self, guardrails, mock_user_low, mock_contract_low_open_interest
    ):
        """Test that low open interest is rejected for low risk."""
        decision = guardrails.validate_contract(
            mock_user_low, mock_contract_low_open_interest, "covered_call"
        )
        assert not decision.approved
        assert RejectionReason.LOW_OPEN_INTEREST in decision.reasons

    def test_low_open_interest_accepted_high_risk(
        self, guardrails, mock_user_high, mock_contract_low_open_interest
    ):
        """Test that low open interest is accepted for high risk."""
        decision = guardrails.validate_contract(
            mock_user_high, mock_contract_low_open_interest, "long_call"
        )
        assert decision.approved

    def test_wide_spread_rejects_low_risk(
        self, guardrails, mock_user_low, mock_contract_wide_spread
    ):
        """Test that wide bid-ask spread is rejected for low risk."""
        decision = guardrails.validate_contract(
            mock_user_low, mock_contract_wide_spread, "covered_call"
        )
        assert not decision.approved
        assert RejectionReason.WIDE_BID_ASK_SPREAD in decision.reasons

    def test_wide_spread_accepted_high_risk(
        self, guardrails, mock_user_high, mock_contract_wide_spread
    ):
        """Test that wide bid-ask spread is accepted for high risk."""
        decision = guardrails.validate_contract(
            mock_user_high, mock_contract_wide_spread, "long_call"
        )
        assert decision.approved

    def test_valid_contract_approves(
        self, guardrails, mock_user_low, mock_contract_good
    ):
        """Test that valid contract is approved."""
        decision = guardrails.validate_contract(
            mock_user_low, mock_contract_good, "covered_call"
        )
        assert decision.approved

    # Invalid contract tests

    def test_missing_bid_rejects(
        self, guardrails, mock_user_low, mock_contract_good
    ):
        """Test that missing bid price is rejected."""
        mock_contract_good.bid = None
        decision = guardrails.validate_contract(
            mock_user_low, mock_contract_good, "covered_call"
        )
        assert not decision.approved
        assert RejectionReason.INVALID_CONTRACT in decision.reasons

    def test_missing_ask_rejects(
        self, guardrails, mock_user_low, mock_contract_good
    ):
        """Test that missing ask price is rejected."""
        mock_contract_good.ask = None
        decision = guardrails.validate_contract(
            mock_user_low, mock_contract_good, "covered_call"
        )
        assert not decision.approved
        assert RejectionReason.INVALID_CONTRACT in decision.reasons

    def test_negative_bid_rejects(
        self, guardrails, mock_user_low, mock_contract_good
    ):
        """Test that negative bid price is rejected."""
        mock_contract_good.bid = -1.0
        decision = guardrails.validate_contract(
            mock_user_low, mock_contract_good, "covered_call"
        )
        assert not decision.approved
        assert RejectionReason.INVALID_CONTRACT in decision.reasons

    def test_ask_less_than_bid_rejects(
        self, guardrails, mock_user_low, mock_contract_good
    ):
        """Test that ask < bid is rejected."""
        mock_contract_good.bid = 3.0
        mock_contract_good.ask = 2.0
        decision = guardrails.validate_contract(
            mock_user_low, mock_contract_good, "covered_call"
        )
        assert not decision.approved
        assert RejectionReason.INVALID_CONTRACT in decision.reasons

    # Allowed strategies tests

    def test_allowed_strategies_low(self, guardrails):
        """Test allowed strategies for low risk."""
        strategies = guardrails.allowed_strategies_for_level("low")
        assert "covered_call" in strategies
        assert "cash_secured_put" in strategies
        assert "long_call" not in strategies

    def test_allowed_strategies_medium(self, guardrails):
        """Test allowed strategies for medium risk."""
        strategies = guardrails.allowed_strategies_for_level("medium")
        assert "covered_call" in strategies
        assert "debit_spread" in strategies
        assert "long_call" not in strategies

    def test_allowed_strategies_high(self, guardrails):
        """Test allowed strategies for high risk."""
        strategies = guardrails.allowed_strategies_for_level("high")
        assert "covered_call" in strategies
        assert "long_call" in strategies
        assert "long_put" in strategies

    # Combined validation tests

    def test_signal_validation_with_contract(
        self, guardrails, mock_user_low, mock_signal, mock_contract_good
    ):
        """Test signal validation with contract."""
        decision = guardrails.validate_signal(
            mock_user_low, mock_signal, mock_contract_good
        )
        assert decision.approved

    def test_signal_validation_rejects_bad_contract(
        self, guardrails, mock_user_low, mock_signal, mock_contract_low_volume
    ):
        """Test signal validation rejects bad contract."""
        decision = guardrails.validate_signal(
            mock_user_low, mock_signal, mock_contract_low_volume
        )
        assert not decision.approved
        assert RejectionReason.LOW_VOLUME in decision.reasons

    def test_signal_validation_multiple_rejections(
        self, guardrails, mock_user_low, mock_signal
    ):
        """Test signal validation with multiple rejection reasons."""
        mock_signal.strategy_type = "long_call"
        mock_signal.max_loss = 500.0
        decision = guardrails.validate_signal(mock_user_low, mock_signal)
        assert not decision.approved
        assert len(decision.reasons) >= 2
        assert RejectionReason.STRATEGY_NOT_ALLOWED in decision.reasons
        assert RejectionReason.MAX_LOSS_EXCEEDED in decision.reasons

    def test_decision_has_messages(self, guardrails, mock_user_low, mock_signal):
        """Test that decision includes human-readable messages."""
        mock_signal.strategy_type = "long_call"
        decision = guardrails.validate_signal(mock_user_low, mock_signal)
        assert not decision.approved
        assert len(decision.messages) > 0
        assert any("long_call" in msg for msg in decision.messages)
