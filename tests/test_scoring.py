"""Tests for signal scoring formula."""

import pytest
from app.core.scoring import SignalScorer, ScoringBreakdown


class TestSignalScorer:
    """Tests for SignalScorer class."""

    def test_score_liquidity_with_preset_score(self):
        """Test liquidity scoring with preset score."""
        score = SignalScorer.score_liquidity(liquidity_score=75.0)
        assert score == 75.0

    def test_score_liquidity_clamps_to_range(self):
        """Test that liquidity score is clamped to 0-100."""
        assert SignalScorer.score_liquidity(liquidity_score=-10.0) == 0.0
        assert SignalScorer.score_liquidity(liquidity_score=150.0) == 100.0

    def test_score_liquidity_default(self):
        """Test default liquidity score."""
        score = SignalScorer.score_liquidity(liquidity_score=None)
        assert score == 50.0

    def test_score_liquidity_from_components(self):
        """Test liquidity scoring from bid/ask, volume, OI."""
        # Good liquidity
        score = SignalScorer.score_liquidity(
            liquidity_score=None,
            bid_ask_spread_pct=0.005,
            volume=5000,
            open_interest=2000,
        )
        assert score > 70.0

    def test_score_reward_risk_positive_ratio(self):
        """Test reward/risk scoring with positive ratio."""
        # 1:1 ratio should score around 50
        score = SignalScorer.score_reward_risk(expected_profit=100.0, max_loss=100.0)
        assert 45.0 < score < 55.0

    def test_score_reward_risk_high_ratio(self):
        """Test reward/risk scoring with high ratio."""
        # 3:1 ratio should score high
        score = SignalScorer.score_reward_risk(expected_profit=300.0, max_loss=100.0)
        assert score > 80.0

    def test_score_reward_risk_low_ratio(self):
        """Test reward/risk scoring with low ratio."""
        # 0.25:1 ratio should score low
        score = SignalScorer.score_reward_risk(expected_profit=25.0, max_loss=100.0)
        assert score < 30.0

    def test_score_reward_risk_zero_loss(self):
        """Test reward/risk with zero max loss."""
        score = SignalScorer.score_reward_risk(expected_profit=100.0, max_loss=0.0)
        assert score == 0.0

    def test_score_probability_below_50_percent(self):
        """Test probability scoring below 50%."""
        score = SignalScorer.score_probability(probability_estimate=0.45)
        assert score == 0.0

    def test_score_probability_50_percent(self):
        """Test probability scoring at 50%."""
        score = SignalScorer.score_probability(probability_estimate=0.50)
        assert score == 0.0

    def test_score_probability_60_percent(self):
        """Test probability scoring at 60%."""
        score = SignalScorer.score_probability(probability_estimate=0.60)
        assert 45.0 < score < 55.0

    def test_score_probability_70_percent(self):
        """Test probability scoring at 70%."""
        score = SignalScorer.score_probability(probability_estimate=0.70)
        assert score > 90.0

    def test_score_volatility_cheap(self):
        """Test volatility scoring when IV is cheap."""
        score = SignalScorer.score_volatility(volatility_context="cheap")
        assert score == 80.0

    def test_score_volatility_fair(self):
        """Test volatility scoring when IV is fair."""
        score = SignalScorer.score_volatility(volatility_context="fair")
        assert score == 60.0

    def test_score_volatility_expensive(self):
        """Test volatility scoring when IV is expensive."""
        score = SignalScorer.score_volatility(volatility_context="expensive")
        assert score == 40.0

    def test_score_volatility_none(self):
        """Test volatility scoring with no context."""
        score = SignalScorer.score_volatility(volatility_context=None)
        assert score == 50.0

    def test_score_volatility_from_iv_hv(self):
        """Test volatility scoring from IV vs HV."""
        # IV < HV (cheap)
        score = SignalScorer.score_volatility(
            volatility_context=None,
            implied_volatility=0.20,
            historical_volatility=0.30,
        )
        assert score > 60.0

    def test_score_sentiment_bullish(self):
        """Test sentiment scoring for bullish sentiment."""
        score = SignalScorer.score_sentiment(sentiment_score=1.0)
        assert score == 100.0

    def test_score_sentiment_bearish(self):
        """Test sentiment scoring for bearish sentiment."""
        score = SignalScorer.score_sentiment(sentiment_score=-1.0)
        assert score == 0.0

    def test_score_sentiment_neutral(self):
        """Test sentiment scoring for neutral sentiment."""
        score = SignalScorer.score_sentiment(sentiment_score=0.0)
        assert score == 50.0

    def test_score_sentiment_none(self):
        """Test sentiment scoring with no data."""
        score = SignalScorer.score_sentiment(sentiment_score=None)
        assert score == 50.0

    def test_score_trend_bullish_call_strategy(self):
        """Test trend scoring for bullish trend with call strategy."""
        score = SignalScorer.score_trend(
            trend_direction="up",
            strategy_type="covered_call",
        )
        assert score > 80.0

    def test_score_trend_bearish_call_strategy(self):
        """Test trend scoring for bearish trend with call strategy."""
        score = SignalScorer.score_trend(
            trend_direction="down",
            strategy_type="covered_call",
        )
        assert score < 30.0

    def test_score_trend_bullish_put_strategy(self):
        """Test trend scoring for bullish trend with put strategy."""
        score = SignalScorer.score_trend(
            trend_direction="up",
            strategy_type="cash_secured_put",
        )
        assert score < 30.0

    def test_score_trend_bearish_put_strategy(self):
        """Test trend scoring for bearish trend with put strategy."""
        score = SignalScorer.score_trend(
            trend_direction="down",
            strategy_type="cash_secured_put",
        )
        assert score > 80.0

    def test_score_trend_neutral(self):
        """Test trend scoring for neutral trend."""
        score = SignalScorer.score_trend(
            trend_direction="neutral",
            strategy_type="covered_call",
        )
        assert score == 50.0

    def test_score_trend_none(self):
        """Test trend scoring with no trend data."""
        score = SignalScorer.score_trend(trend_direction=None)
        assert score == 50.0

    def test_score_event_risk_no_events(self):
        """Test event risk scoring with no events."""
        score = SignalScorer.score_event_risk(event_risks=None)
        assert score == 80.0

    def test_score_event_risk_earnings(self):
        """Test event risk scoring with earnings event."""
        score = SignalScorer.score_event_risk(event_risks="earnings")
        assert score == 30.0

    def test_score_event_risk_fda_decision(self):
        """Test event risk scoring with FDA decision."""
        score = SignalScorer.score_event_risk(event_risks="fda_decision")
        assert score == 30.0

    def test_score_event_risk_analyst_upgrade(self):
        """Test event risk scoring with analyst upgrade."""
        score = SignalScorer.score_event_risk(event_risks="analyst_upgrade")
        assert score == 50.0

    def test_score_event_risk_macro_event(self):
        """Test event risk scoring with macro event."""
        score = SignalScorer.score_event_risk(event_risks="macro_event")
        assert score == 40.0

    def test_calculate_score_all_components(self):
        """Test comprehensive score calculation with all components."""
        final_score, breakdown = SignalScorer.calculate_score(
            liquidity_score=75.0,
            expected_profit=200.0,
            max_loss=100.0,
            probability_estimate=0.65,
            volatility_context="fair",
            sentiment_score=0.3,
            trend_direction="up",
            event_risks=None,
            strategy_type="covered_call",
        )
        
        # Final score should be in valid range
        assert 0.0 <= final_score <= 100.0
        
        # Breakdown should have all components
        assert "liquidity" in breakdown
        assert "reward_risk" in breakdown
        assert "probability" in breakdown
        assert "volatility" in breakdown
        assert "sentiment" in breakdown
        assert "trend" in breakdown
        assert "event_risk" in breakdown
        assert "final" in breakdown
        
        # Final score should match
        assert breakdown["final"] == final_score

    def test_calculate_score_minimal_inputs(self):
        """Test score calculation with minimal inputs."""
        final_score, breakdown = SignalScorer.calculate_score(
            expected_profit=100.0,
            max_loss=100.0,
            probability_estimate=0.55,
        )
        
        assert 0.0 <= final_score <= 100.0
        assert breakdown["final"] == final_score

    def test_calculate_score_high_quality_signal(self):
        """Test score calculation for high-quality signal."""
        final_score, breakdown = SignalScorer.calculate_score(
            liquidity_score=90.0,
            expected_profit=300.0,
            max_loss=100.0,
            probability_estimate=0.70,
            volatility_context="cheap",
            sentiment_score=0.8,
            trend_direction="up",
            event_risks=None,
            strategy_type="covered_call",
        )
        
        # High-quality signal should score well
        assert final_score > 70.0

    def test_calculate_score_low_quality_signal(self):
        """Test score calculation for low-quality signal."""
        final_score, breakdown = SignalScorer.calculate_score(
            liquidity_score=20.0,
            expected_profit=50.0,
            max_loss=200.0,
            probability_estimate=0.52,
            volatility_context="expensive",
            sentiment_score=-0.7,
            trend_direction="down",
            event_risks="earnings",
            strategy_type="covered_call",
        )
        
        # Low-quality signal should score poorly
        assert final_score < 40.0

    def test_scoring_breakdown_to_dict(self):
        """Test ScoringBreakdown.to_dict() method."""
        breakdown = ScoringBreakdown(
            liquidity_score=75.0,
            reward_risk_score=60.0,
            probability_score=70.0,
            volatility_score=50.0,
            sentiment_score=55.0,
            trend_score=80.0,
            event_risk_score=75.0,
            final_score=65.0,
        )
        
        breakdown_dict = breakdown.to_dict()
        
        assert breakdown_dict["liquidity"] == 75.0
        assert breakdown_dict["reward_risk"] == 60.0
        assert breakdown_dict["probability"] == 70.0
        assert breakdown_dict["volatility"] == 50.0
        assert breakdown_dict["sentiment"] == 55.0
        assert breakdown_dict["trend"] == 80.0
        assert breakdown_dict["event_risk"] == 75.0
        assert breakdown_dict["final"] == 65.0

    def test_weights_sum_to_one(self):
        """Test that scoring weights sum to 1.0."""
        total_weight = sum(SignalScorer.WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.001

    def test_score_components_are_independent(self):
        """Test that score components are calculated independently."""
        # Change one component, others should remain the same
        score1, breakdown1 = SignalScorer.calculate_score(
            liquidity_score=50.0,
            expected_profit=100.0,
            max_loss=100.0,
            probability_estimate=0.55,
        )
        
        score2, breakdown2 = SignalScorer.calculate_score(
            liquidity_score=90.0,  # Changed
            expected_profit=100.0,
            max_loss=100.0,
            probability_estimate=0.55,
        )
        
        # Liquidity should be different
        assert breakdown1["liquidity"] != breakdown2["liquidity"]
        
        # Other components should be the same
        assert breakdown1["reward_risk"] == breakdown2["reward_risk"]
        assert breakdown1["probability"] == breakdown2["probability"]
        
        # Final scores should be different
        assert score1 != score2
