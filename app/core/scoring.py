"""Signal scoring formula for generating explainable 0-100 scores.

Implements a comprehensive scoring system that combines multiple factors:
- Liquidity score (20%): Tradability of the option contract
- Reward/risk ratio (20%): Expected profit vs maximum loss
- Probability estimate (20%): Estimated probability of profit
- Volatility context (10%): Whether volatility is favorable
- News sentiment (12%): Aggregate sentiment from recent news
- Trend direction (13%): Price trend alignment with strategy
- Event risk (5%): Upcoming events that could impact the trade

Each component is independently scored 0-100 and weighted to produce a final score.
The breakdown is provided for full transparency and explainability.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScoringBreakdown:
    """Detailed breakdown of signal score components."""
    liquidity_score: float  # 0-100
    reward_risk_score: float  # 0-100
    probability_score: float  # 0-100
    volatility_score: float  # 0-100
    sentiment_score: float  # 0-100
    trend_score: float  # 0-100
    event_risk_score: float  # 0-100
    final_score: float  # 0-100 (weighted average)

    def to_dict(self) -> Dict[str, float]:
        """Convert breakdown to dictionary."""
        return {
            "liquidity": self.liquidity_score,
            "reward_risk": self.reward_risk_score,
            "probability": self.probability_score,
            "volatility": self.volatility_score,
            "sentiment": self.sentiment_score,
            "trend": self.trend_score,
            "event_risk": self.event_risk_score,
            "final": self.final_score,
        }


class SignalScorer:
    """Scores trading signals on a 0-100 scale with explainable breakdown.
    
    Combines multiple factors to produce a comprehensive signal score:
    - Liquidity (20%): How easily the contract can be traded
    - Reward/Risk (20%): Profit potential vs downside risk
    - Probability (20%): Estimated probability of profit
    - Volatility (10%): Whether current volatility is favorable
    - Sentiment (12%): News sentiment alignment with strategy
    - Trend (13%): Price trend alignment with strategy direction
    - Event Risk (5%): Impact of upcoming events
    """

    # Weighting factors (must sum to 1.0)
    WEIGHTS = {
        "liquidity": 0.20,
        "reward_risk": 0.20,
        "probability": 0.20,
        "volatility": 0.10,
        "sentiment": 0.12,
        "trend": 0.13,
        "event_risk": 0.05,
    }

    @staticmethod
    def score_liquidity(
        liquidity_score: Optional[float],
        bid_ask_spread_pct: Optional[float] = None,
        volume: Optional[int] = None,
        open_interest: Optional[int] = None,
    ) -> float:
        """Score liquidity of an option contract (0-100).
        
        Args:
            liquidity_score: Pre-calculated liquidity score (0-100) if available
            bid_ask_spread_pct: Bid-ask spread as percentage
            volume: Trading volume
            open_interest: Open interest
            
        Returns:
            Liquidity score 0-100
        """
        if liquidity_score is not None:
            return max(0.0, min(100.0, liquidity_score))
        
        # Fallback: calculate from components if available
        if bid_ask_spread_pct is not None or volume is not None or open_interest is not None:
            score = 50.0  # Default middle score
            
            # Adjust based on spread
            if bid_ask_spread_pct is not None:
                if bid_ask_spread_pct < 0.01:
                    score += 15.0
                elif bid_ask_spread_pct < 0.05:
                    score += 10.0
                elif bid_ask_spread_pct < 0.10:
                    score += 5.0
            
            # Adjust based on volume
            if volume is not None:
                if volume > 1000:
                    score += 15.0
                elif volume > 100:
                    score += 10.0
                elif volume > 10:
                    score += 5.0
            
            # Adjust based on open interest
            if open_interest is not None:
                if open_interest > 1000:
                    score += 15.0
                elif open_interest > 100:
                    score += 10.0
                elif open_interest > 10:
                    score += 5.0
            
            return max(0.0, min(100.0, score))
        
        return 50.0  # Default neutral score

    @staticmethod
    def score_reward_risk(
        expected_profit: float,
        max_loss: float,
    ) -> float:
        """Score reward/risk ratio (0-100).
        
        Args:
            expected_profit: Expected profit in dollars
            max_loss: Maximum loss in dollars
            
        Returns:
            Reward/risk score 0-100
        """
        if max_loss <= 0:
            return 0.0
        
        ratio = expected_profit / max_loss
        
        # Score based on reward/risk ratio
        # 0.5:1 = 20, 1:1 = 50, 2:1 = 80, 3:1+ = 100
        if ratio < 0.5:
            score = ratio * 40.0  # 0-20
        elif ratio < 1.0:
            score = 20.0 + (ratio - 0.5) * 60.0  # 20-50
        elif ratio < 2.0:
            score = 50.0 + (ratio - 1.0) * 30.0  # 50-80
        else:
            score = 80.0 + min(20.0, (ratio - 2.0) * 10.0)  # 80-100
        
        return max(0.0, min(100.0, score))

    @staticmethod
    def score_probability(
        probability_estimate: float,
    ) -> float:
        """Score probability of profit (0-100).
        
        Args:
            probability_estimate: Probability of profit (0.0-1.0)
            
        Returns:
            Probability score 0-100
        """
        # Direct conversion: 0.5 (50%) = 0, 0.6 (60%) = 50, 0.7 (70%) = 100
        if probability_estimate < 0.5:
            return 0.0
        elif probability_estimate < 0.6:
            score = (probability_estimate - 0.5) * 500.0  # 0-50
        else:
            score = 50.0 + (probability_estimate - 0.6) * 500.0  # 50-100
        
        return max(0.0, min(100.0, score))

    @staticmethod
    def score_volatility(
        volatility_context: Optional[str],
        implied_volatility: Optional[float] = None,
        historical_volatility: Optional[float] = None,
    ) -> float:
        """Score volatility context (0-100).
        
        Args:
            volatility_context: "expensive", "cheap", "fair", or None
            implied_volatility: Current implied volatility
            historical_volatility: Historical volatility for comparison
            
        Returns:
            Volatility score 0-100
        """
        if volatility_context == "cheap":
            return 80.0  # Good for buying options
        elif volatility_context == "fair":
            return 60.0  # Neutral
        elif volatility_context == "expensive":
            return 40.0  # Less favorable for buying
        
        # Fallback: compare IV to HV if available
        if implied_volatility is not None and historical_volatility is not None:
            if implied_volatility < historical_volatility:
                return 70.0  # IV cheap relative to HV
            elif implied_volatility > historical_volatility * 1.2:
                return 40.0  # IV expensive
            else:
                return 55.0  # IV fair
        
        return 50.0  # Default neutral

    @staticmethod
    def score_sentiment(
        sentiment_score: Optional[float],
    ) -> float:
        """Score news sentiment (0-100).
        
        Args:
            sentiment_score: Normalized sentiment (-1.0 to 1.0)
                -1.0 = bearish, 0.0 = neutral, 1.0 = bullish
            
        Returns:
            Sentiment score 0-100
        """
        if sentiment_score is None:
            return 50.0  # Neutral if no sentiment data
        
        # Convert from -1.0..1.0 to 0..100
        # -1.0 = 0, 0.0 = 50, 1.0 = 100
        return max(0.0, min(100.0, (sentiment_score + 1.0) * 50.0))

    @staticmethod
    def score_trend(
        trend_direction: Optional[str],
        strategy_type: str = "",
    ) -> float:
        """Score price trend alignment (0-100).
        
        Args:
            trend_direction: "up", "down", "neutral", or None
            strategy_type: Type of strategy (for context)
            
        Returns:
            Trend score 0-100
        """
        if trend_direction is None:
            return 50.0  # Neutral if no trend data
        
        trend_direction = trend_direction.lower().strip()
        
        # For bullish strategies (calls, bull spreads)
        if "call" in strategy_type.lower() or "bull" in strategy_type.lower():
            if trend_direction == "up":
                return 85.0
            elif trend_direction == "neutral":
                return 50.0
            else:  # down
                return 20.0
        
        # For bearish strategies (puts, bear spreads)
        elif "put" in strategy_type.lower() or "bear" in strategy_type.lower():
            if trend_direction == "down":
                return 85.0
            elif trend_direction == "neutral":
                return 50.0
            else:  # up
                return 20.0
        
        # Default: neutral trend is okay
        return 50.0

    @staticmethod
    def score_event_risk(
        event_risks: Optional[str],
    ) -> float:
        """Score event risk impact (0-100).
        
        Args:
            event_risks: JSON string or comma-separated list of event risks
            
        Returns:
            Event risk score 0-100 (higher = less risk)
        """
        if not event_risks:
            return 80.0  # No events = good
        
        event_risks_str = str(event_risks).lower()
        
        # High-risk events
        high_risk_events = ["earnings", "fda_decision", "lawsuit", "sec_investigation"]
        for event in high_risk_events:
            if event in event_risks_str:
                return 30.0  # High risk
        
        # Medium-risk events
        medium_risk_events = ["m_and_a", "analyst_upgrade", "analyst_downgrade"]
        for event in medium_risk_events:
            if event in event_risks_str:
                return 50.0  # Medium risk
        
        # Macro events
        if "macro_event" in event_risks_str:
            return 40.0  # Moderate risk
        
        return 80.0  # No recognized events

    @classmethod
    def calculate_score(
        cls,
        liquidity_score: Optional[float] = None,
        expected_profit: float = 0.0,
        max_loss: float = 1.0,
        probability_estimate: float = 0.5,
        volatility_context: Optional[str] = None,
        sentiment_score: Optional[float] = None,
        trend_direction: Optional[str] = None,
        event_risks: Optional[str] = None,
        strategy_type: str = "",
        **kwargs,
    ) -> tuple:
        """Calculate comprehensive signal score (0-100) with breakdown.
        
        Args:
            liquidity_score: Liquidity score 0-100
            expected_profit: Expected profit in dollars
            max_loss: Maximum loss in dollars
            probability_estimate: Probability of profit 0.0-1.0
            volatility_context: "expensive", "cheap", "fair"
            sentiment_score: Sentiment -1.0 to 1.0
            trend_direction: "up", "down", "neutral"
            event_risks: Event risk description
            strategy_type: Type of strategy
            **kwargs: Additional parameters (ignored)
            
        Returns:
            Tuple of (final_score, breakdown_dict)
            - final_score: 0-100
            - breakdown_dict: Dict with all component scores
        """
        # Score each component
        liquidity = cls.score_liquidity(liquidity_score)
        reward_risk = cls.score_reward_risk(expected_profit, max_loss)
        probability = cls.score_probability(probability_estimate)
        volatility = cls.score_volatility(volatility_context)
        sentiment = cls.score_sentiment(sentiment_score)
        trend = cls.score_trend(trend_direction, strategy_type)
        event_risk = cls.score_event_risk(event_risks)
        
        # Calculate weighted average
        final_score = (
            liquidity * cls.WEIGHTS["liquidity"]
            + reward_risk * cls.WEIGHTS["reward_risk"]
            + probability * cls.WEIGHTS["probability"]
            + volatility * cls.WEIGHTS["volatility"]
            + sentiment * cls.WEIGHTS["sentiment"]
            + trend * cls.WEIGHTS["trend"]
            + event_risk * cls.WEIGHTS["event_risk"]
        )
        
        breakdown = ScoringBreakdown(
            liquidity_score=liquidity,
            reward_risk_score=reward_risk,
            probability_score=probability,
            volatility_score=volatility,
            sentiment_score=sentiment,
            trend_score=trend,
            event_risk_score=event_risk,
            final_score=final_score,
        )
        
        return final_score, breakdown.to_dict()
