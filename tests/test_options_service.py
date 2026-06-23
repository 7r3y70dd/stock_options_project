"""Tests for options service Greeks analysis and risk guardrails."""

import pytest
from services.options_service import (
    OptionContract,
    ScoredOption,
    VolatilityAnalyzer,
    GreeksAnalyzer,
    OptionsChainFilter,
)
from services import RiskLevel, RejectionReason


class TestGreeksAnalyzer:
    """Tests for GreeksAnalyzer class."""

    def test_analyze_greeks_with_all_greeks(self):
        """Test analyzing Greeks when all values are present."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            delta=0.65,
            gamma=0.03,
            theta=-0.05,
            vega=0.15,
        )
        
        analysis = GreeksAnalyzer.analyze_greeks(contract)
        
        assert analysis["delta"] == 0.65
        assert analysis["delta_abs"] == 0.65
        assert analysis["gamma"] == 0.03
        assert analysis["gamma_abs"] == 0.03
        assert analysis["theta"] == -0.05
        assert analysis["theta_abs"] == 0.05
        assert analysis["vega"] == 0.15
        assert analysis["vega_abs"] == 0.15

    def test_analyze_greeks_with_partial_greeks(self):
        """Test analyzing Greeks when only some values are present."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            delta=0.65,
            gamma=None,
            theta=-0.05,
            vega=None,
        )
        
        analysis = GreeksAnalyzer.analyze_greeks(contract)
        
        assert "delta" in analysis
        assert "gamma" not in analysis
        assert "theta" in analysis
        assert "vega" not in analysis

    def test_assess_greek_profile_low_risk_acceptable(self):
        """Test assessing Greek profile for low risk level - acceptable contract."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            delta=0.25,  # Within low risk threshold of 0.30
            gamma=0.03,  # Within low risk threshold of 0.05
            theta=-0.01,  # Within low risk threshold of -0.02
            vega=0.08,  # Within low risk threshold of 0.10
        )
        
        acceptable, warnings, scores = GreeksAnalyzer.assess_greek_profile(
            contract, RiskLevel.LOW
        )
        
        assert acceptable is True
        assert len(warnings) == 0
        assert "delta_score" in scores
        assert "gamma_score" in scores
        assert "theta_score" in scores
        assert "vega_score" in scores

    def test_assess_greek_profile_low_risk_unacceptable_delta(self):
        """Test assessing Greek profile for low risk level - unacceptable delta."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            delta=0.50,  # Exceeds low risk threshold of 0.30
            gamma=0.03,
            theta=-0.01,
            vega=0.08,
        )
        
        acceptable, warnings, scores = GreeksAnalyzer.assess_greek_profile(
            contract, RiskLevel.LOW
        )
        
        assert acceptable is False
        assert len(warnings) > 0
        assert any("Delta" in w for w in warnings)
        assert any("directional exposure" in w for w in warnings)

    def test_assess_greek_profile_low_risk_unacceptable_gamma(self):
        """Test assessing Greek profile for low risk level - unacceptable gamma."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            delta=0.25,
            gamma=0.08,  # Exceeds low risk threshold of 0.05
            theta=-0.01,
            vega=0.08,
        )
        
        acceptable, warnings, scores = GreeksAnalyzer.assess_greek_profile(
            contract, RiskLevel.LOW
        )
        
        assert acceptable is False
        assert len(warnings) > 0
        assert any("Gamma" in w for w in warnings)
        assert any("acceleration risk" in w for w in warnings)

    def test_assess_greek_profile_low_risk_unacceptable_theta(self):
        """Test assessing Greek profile for low risk level - unacceptable theta."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            delta=0.25,
            gamma=0.03,
            theta=-0.03,  # Exceeds low risk threshold of -0.02
            vega=0.08,
        )
        
        acceptable, warnings, scores = GreeksAnalyzer.assess_greek_profile(
            contract, RiskLevel.LOW
        )
        
        assert acceptable is False
        assert len(warnings) > 0
        assert any("Theta" in w for w in warnings)
        assert any("time decay" in w for w in warnings)

    def test_assess_greek_profile_low_risk_unacceptable_vega(self):
        """Test assessing Greek profile for low risk level - unacceptable vega."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            delta=0.25,
            gamma=0.03,
            theta=-0.01,
            vega=0.15,  # Exceeds low risk threshold of 0.10
        )
        
        acceptable, warnings, scores = GreeksAnalyzer.assess_greek_profile(
            contract, RiskLevel.LOW
        )
        
        assert acceptable is False
        assert len(warnings) > 0
        assert any("Vega" in w for w in warnings)
        assert any("volatility sensitivity" in w for w in warnings)

    def test_assess_greek_profile_medium_risk(self):
        """Test assessing Greek profile for medium risk level."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            delta=0.55,  # Within medium risk threshold of 0.60
            gamma=0.08,  # Within medium risk threshold of 0.10
            theta=-0.04,  # Within medium risk threshold of -0.05
            vega=0.18,  # Within medium risk threshold of 0.20
        )
        
        acceptable, warnings, scores = GreeksAnalyzer.assess_greek_profile(
            contract, RiskLevel.MEDIUM
        )
        
        assert acceptable is True
        assert len(warnings) == 0

    def test_assess_greek_profile_high_risk(self):
        """Test assessing Greek profile for high risk level."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            delta=0.85,  # Within high risk threshold of 0.90
            gamma=0.18,  # Within high risk threshold of 0.20
            theta=-0.08,  # Within high risk threshold of -0.10
            vega=0.35,  # Within high risk threshold of 0.40
        )
        
        acceptable, warnings, scores = GreeksAnalyzer.assess_greek_profile(
            contract, RiskLevel.HIGH
        )
        
        assert acceptable is True
        assert len(warnings) == 0

    def test_calculate_greeks_score_acceptable(self):
        """Test calculating Greeks score for acceptable contract."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            delta=0.25,
            gamma=0.03,
            theta=-0.01,
            vega=0.08,
        )
        
        score = GreeksAnalyzer.calculate_greeks_score(contract, RiskLevel.LOW)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be relatively high for acceptable contract

    def test_calculate_greeks_score_unacceptable(self):
        """Test calculating Greeks score for unacceptable contract."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            delta=0.95,  # Way over threshold
            gamma=0.25,  # Way over threshold
            theta=-0.15,  # Way over threshold
            vega=0.50,  # Way over threshold
        )
        
        score = GreeksAnalyzer.calculate_greeks_score(contract, RiskLevel.LOW)
        
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Should be relatively low for unacceptable contract

    def test_calculate_greeks_score_no_greeks(self):
        """Test calculating Greeks score when no Greeks data available."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
        )
        
        score = GreeksAnalyzer.calculate_greeks_score(contract, RiskLevel.LOW)
        
        assert score == 1.0  # Should default to perfect score


class TestOptionsChainFilterGreeks:
    """Tests for OptionsChainFilter Greeks integration."""

    def test_filter_contracts_rejects_unacceptable_greeks(self):
        """Test that filter rejects contracts with unacceptable Greeks."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            delta=0.95,  # Exceeds low risk threshold
            gamma=0.03,
            theta=-0.01,
            vega=0.08,
        )
        
        filter_obj = OptionsChainFilter(RiskLevel.LOW)
        results = filter_obj.filter_contracts([contract])
        
        assert len(results) == 1
        assert results[0].passed is False
        assert results[0].rejection_reason == RejectionReason.UNACCEPTABLE_GREEKS
        assert "Greeks" in results[0].rejection_message

    def test_filter_contracts_accepts_acceptable_greeks(self):
        """Test that filter accepts contracts with acceptable Greeks."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            delta=0.25,
            gamma=0.03,
            theta=-0.01,
            vega=0.08,
        )
        
        filter_obj = OptionsChainFilter(RiskLevel.LOW)
        results = filter_obj.filter_contracts([contract])
        
        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].rejection_reason == RejectionReason.PASSED

    def test_filter_contracts_multiple_greeks_violations(self):
        """Test that filter reports multiple Greeks violations."""
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
            delta=0.95,  # Exceeds threshold
            gamma=0.10,  # Exceeds threshold
            theta=-0.05,  # Exceeds threshold
            vega=0.15,  # Exceeds threshold
        )
        
        filter_obj = OptionsChainFilter(RiskLevel.LOW)
        results = filter_obj.filter_contracts([contract])
        
        assert len(results) == 1
        assert results[0].passed is False
        # Should mention multiple Greeks violations
        message = results[0].rejection_message
        assert message.count(";") >= 3  # At least 3 violations separated by semicolons


class TestVolatilityAnalyzer:
    """Tests for VolatilityAnalyzer class."""

    def test_calculate_historical_volatility_sufficient_data(self):
        """Test calculating historical volatility with sufficient data."""
        price_bars = [
            {"close": 100.0},
            {"close": 101.0},
            {"close": 102.0},
            {"close": 101.5},
            {"close": 103.0},
        ]
        
        hv = VolatilityAnalyzer.calculate_historical_volatility(price_bars)
        
        assert hv is not None
        assert hv > 0
        assert hv < 1.0  # Should be reasonable volatility

    def test_calculate_historical_volatility_insufficient_data(self):
        """Test calculating historical volatility with insufficient data."""
        price_bars = [{"close": 100.0}]
        
        hv = VolatilityAnalyzer.calculate_historical_volatility(price_bars)
        
        assert hv is None

    def test_compare_volatilities_expensive(self):
        """Test comparing volatilities - expensive contract."""
        iv = 0.40
        hv = 0.25
        
        ratio, context = VolatilityAnalyzer.compare_volatilities(iv, hv)
        
        assert ratio == pytest.approx(1.6, rel=0.01)
        assert context == "expensive"

    def test_compare_volatilities_cheap(self):
        """Test comparing volatilities - cheap contract."""
        iv = 0.15
        hv = 0.25
        
        ratio, context = VolatilityAnalyzer.compare_volatilities(iv, hv)
        
        assert ratio == pytest.approx(0.6, rel=0.01)
        assert context == "cheap"

    def test_compare_volatilities_fair(self):
        """Test comparing volatilities - fair contract."""
        iv = 0.25
        hv = 0.25
        
        ratio, context = VolatilityAnalyzer.compare_volatilities(iv, hv)
        
        assert ratio == pytest.approx(1.0, rel=0.01)
        assert context == "fair"

    def test_compare_volatilities_missing_data(self):
        """Test comparing volatilities with missing data."""
        ratio, context = VolatilityAnalyzer.compare_volatilities(None, 0.25)
        
        assert ratio is None
        assert context is None
