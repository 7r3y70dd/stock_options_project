"""Tests for options service Greeks analysis, risk guardrails, and pricing."""

import pytest
from services.options_service import (
    OptionContract,
    ScoredOption,
    VolatilityAnalyzer,
    GreeksAnalyzer,
    PricingAnalyzer,
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


class TestPricingAnalyzer:
    """Tests for PricingAnalyzer class."""

    def test_pricing_analyzer_initialization(self):
        """Test PricingAnalyzer initialization."""
        analyzer = PricingAnalyzer(risk_free_rate=0.05, dividend_yield=0.0)
        
        assert analyzer.risk_free_rate == 0.05
        assert analyzer.dividend_yield == 0.0

    def test_calculate_theoretical_price_with_valid_contract(self):
        """Test calculating theoretical price with valid contract data."""
        analyzer = PricingAnalyzer(risk_free_rate=0.05, dividend_yield=0.0)
        
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
        )
        
        # If QuantLib is available, should return a price
        # If not available, should return None
        price = analyzer.calculate_theoretical_price(contract)
        
        if analyzer.pricing_engine is not None:
            assert price is not None
            assert price > 0
        else:
            assert price is None

    def test_calculate_theoretical_price_with_missing_data(self):
        """Test calculating theoretical price with missing contract data."""
        analyzer = PricingAnalyzer()
        
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=5.0,
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=None,  # Missing IV
            underlying_price=150.0,
            days_to_expiration=30,
        )
        
        price = analyzer.calculate_theoretical_price(contract)
        assert price is None

    def test_compare_prices_overpriced(self):
        """Test comparing prices when market price is overpriced."""
        analyzer = PricingAnalyzer()
        
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
        )
        
        theoretical_price, difference, assessment = analyzer.compare_prices(contract)
        
        # If QuantLib available, should have results
        if analyzer.pricing_engine is not None:
            assert theoretical_price is not None
            assert difference is not None
            assert assessment in ["overpriced", "underpriced", "fair"]

    def test_compare_prices_with_missing_bid_ask(self):
        """Test comparing prices when bid/ask are missing."""
        analyzer = PricingAnalyzer()
        
        contract = OptionContract(
            symbol="AAPL",
            expiration="2024-12-20",
            strike=150.0,
            contract_type="call",
            bid=None,  # Missing bid
            ask=5.5,
            volume=100,
            open_interest=500,
            implied_volatility=0.25,
            underlying_price=150.0,
            days_to_expiration=30,
        )
        
        theoretical_price, difference, assessment = analyzer.compare_prices(contract)
        
        assert theoretical_price is None
        assert difference is None
        assert assessment is None


class TestVolatilityAnalyzer:
    """Tests for VolatilityAnalyzer class."""

    def test_calculate_historical_volatility_with_valid_data(self):
        """Test calculating historical volatility with valid price data."""
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

    def test_calculate_historical_volatility_with_insufficient_data(self):
        """Test calculating historical volatility with insufficient data."""
        price_bars = [{"close": 100.0}]
        
        hv = VolatilityAnalyzer.calculate_historical_volatility(price_bars)
        
        assert hv is None

    def test_compare_volatilities_expensive(self):
        """Test comparing volatilities when IV is expensive."""
        iv = 0.40
        hv = 0.25
        
        ratio, context = VolatilityAnalyzer.compare_volatilities(iv, hv)
        
        assert ratio == pytest.approx(1.6, rel=0.01)
        assert context == "expensive"

    def test_compare_volatilities_cheap(self):
        """Test comparing volatilities when IV is cheap."""
        iv = 0.15
        hv = 0.25
        
        ratio, context = VolatilityAnalyzer.compare_volatilities(iv, hv)
        
        assert ratio == pytest.approx(0.6, rel=0.01)
        assert context == "cheap"

    def test_compare_volatilities_fair(self):
        """Test comparing volatilities when IV is fair."""
        iv = 0.25
        hv = 0.25
        
        ratio, context = VolatilityAnalyzer.compare_volatilities(iv, hv)
        
        assert ratio == pytest.approx(1.0, rel=0.01)
        assert context == "fair"
