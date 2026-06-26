"""Long call/put strategy implementation.

Generates high-risk directional trades using long calls or long puts.
Supports both bullish (long call) and bearish (long put) positions.
"""

from typing import Optional, List
from datetime import datetime, timedelta
import logging

from app.strategies.strategy import Strategy, StrategySignal, MarketData, NewsContext
from services.options_service import OptionContract, ScoredOption
from services import RiskLevel
from app.core.config import config

logger = logging.getLogger(__name__)


class LongCallPutStrategy(Strategy):
    """Long call/put strategy for high-risk directional trades.
    
    Generates bullish (long call) or bearish (long put) positions by:
    1. Filtering by trend, news sentiment, and volatility
    2. Selecting expiration window
    3. Selecting delta range
    4. Estimating premium at risk
    5. Rejecting if total premium exceeds risk budget
    6. Ensuring strategy is only available for high-risk profiles
    """

    def __init__(self, name: str = "long_call_put", enabled: bool = True):
        """Initialize long call/put strategy.
        
        Args:
            name: Strategy identifier
            enabled: Whether strategy is active
        """
        super().__init__(name=name, enabled=enabled)

    def generate(
        self,
        symbol: str,
        market_data: MarketData,
        options_chain: List[OptionContract],
        news_context: Optional[NewsContext] = None,
        risk_profile: RiskLevel = RiskLevel.MEDIUM,
    ) -> Optional[StrategySignal]:
        """Generate a long call/put signal.
        
        Args:
            symbol: Stock symbol to analyze
            market_data: Current market data including price
            options_chain: Available option contracts
            news_context: Optional news sentiment
            risk_profile: User's risk tolerance
            
        Returns:
            StrategySignal if a trade opportunity is identified, None otherwise
        """
        # Only available for high-risk profiles
        if risk_profile != RiskLevel.HIGH:
            return None
        
        if not options_chain:
            return None

        current_price = market_data.current_price
        
        # Determine direction based on trend, news, and volatility
        is_bullish = self._should_be_bullish(market_data, news_context)
        
        if is_bullish:
            option = self._select_long_call(symbol, current_price, options_chain, market_data)
        else:
            option = self._select_long_put(symbol, current_price, options_chain, market_data)
        
        if option is None:
            return None
        
        # Estimate premium at risk
        premium_at_risk = (option.bid + option.ask) / 2
        
        # Reject if premium exceeds risk budget
        if premium_at_risk > config.LONG_CALL_PUT_MAX_PREMIUM:
            logger.debug(
                f"Long {option.contract_type} rejected for {symbol}: "
                f"premium {premium_at_risk:.2f} exceeds max {config.LONG_CALL_PUT_MAX_PREMIUM:.2f}"
            )
            return None
        
        # Create signal
        signal = StrategySignal(
            symbol=symbol,
            strategy_type="long_call_put",
            risk_level=risk_profile,
            score=self._calculate_score(option, market_data, news_context),
            expected_profit=self._estimate_max_profit(option, current_price),
            max_loss=premium_at_risk,  # Max loss equals premium paid
            probability_estimate=self._estimate_probability(option, market_data, news_context),
            reason=self._generate_reason(option, is_bullish, market_data, news_context),
            option_contracts=[
                ScoredOption(
                    contract=option,
                    score=self._calculate_score(option, market_data, news_context),
                    liquidity_score=option.liquidity_score,
                )
            ],
            breakdown={
                "premium_at_risk": premium_at_risk,
                "max_loss": premium_at_risk,
                "strike": option.strike,
                "delta": option.delta if hasattr(option, 'delta') else 0.0,
                "days_to_expiration": option.days_to_expiration,
                "implied_volatility": option.implied_volatility,
                "liquidity_score": option.liquidity_score,
            },
        )
        
        return signal

    def _should_be_bullish(self, market_data: MarketData, news_context: Optional[NewsContext]) -> bool:
        """Determine if position should be bullish or bearish.
        
        Uses trend analysis, news sentiment, and volatility filters.
        
        Args:
            market_data: Current market data including price history
            news_context: Optional news sentiment
            
        Returns:
            True for bullish (long call), False for bearish (long put)
        """
        # Analyze trend from price history
        trend_score = self._analyze_trend(market_data.price_history)
        
        # Get news sentiment
        sentiment_score = 0.0
        if news_context and news_context.sentiment_score is not None:
            sentiment_score = news_context.sentiment_score
        
        # Combine trend and sentiment (trend weighted more heavily)
        combined_score = trend_score * 0.6 + sentiment_score * 0.4
        
        return combined_score > 0.0

    def _analyze_trend(self, price_history: List[dict]) -> float:
        """Analyze price trend from historical data.
        
        Args:
            price_history: List of price bars with OHLCV data
            
        Returns:
            Trend score from -1.0 (bearish) to 1.0 (bullish)
        """
        if not price_history or len(price_history) < 2:
            return 0.0
        
        # Get recent closes
        closes = [bar.get('close', 0) for bar in price_history[-20:]]
        if not closes or len(closes) < 2:
            return 0.0
        
        # Calculate simple trend: compare recent average to older average
        recent_avg = sum(closes[-5:]) / 5 if len(closes) >= 5 else closes[-1]
        older_avg = sum(closes[:5]) / 5 if len(closes) >= 5 else closes[0]
        
        if older_avg == 0:
            return 0.0
        
        trend_pct = (recent_avg - older_avg) / older_avg
        # Normalize to -1.0 to 1.0 range
        return max(-1.0, min(1.0, trend_pct * 10))

    def _select_long_call(
        self,
        symbol: str,
        current_price: float,
        options_chain: List[OptionContract],
        market_data: MarketData,
    ) -> Optional[OptionContract]:
        """Select a long call option.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            options_chain: Available options
            market_data: Market data for volatility analysis
            
        Returns:
            Selected call option or None if no valid option found
        """
        # Filter calls with valid expiration and liquidity
        calls = [
            opt for opt in options_chain
            if opt.contract_type == "call"
            and config.LONG_CALL_PUT_MIN_DTE <= opt.days_to_expiration <= config.LONG_CALL_PUT_MAX_DTE
            and opt.volume >= config.LONG_CALL_PUT_MIN_VOLUME
            and opt.open_interest >= config.LONG_CALL_PUT_MIN_OPEN_INTEREST
            and opt.liquidity_score >= config.LONG_CALL_PUT_MIN_LIQUIDITY_SCORE
        ]
        
        if not calls:
            return None
        
        # Filter by delta range (0.40 to 0.70 for bullish directional trades)
        delta_filtered = [
            call for call in calls
            if hasattr(call, 'delta') and config.LONG_CALL_PUT_MIN_DELTA <= call.delta <= config.LONG_CALL_PUT_MAX_DELTA
        ]
        
        # If no delta data, use strike-based filtering (ATM to slightly OTM)
        if not delta_filtered:
            delta_filtered = [
                call for call in calls
                if call.strike <= current_price * (1 + config.LONG_CALL_PUT_MAX_OTM_THRESHOLD)
            ]
        
        if not delta_filtered:
            return None
        
        # Score and select best option
        best_option = None
        best_score = -1.0
        
        for call in delta_filtered:
            score = self._score_option(call, market_data)
            if score > best_score:
                best_score = score
                best_option = call
        
        return best_option

    def _select_long_put(
        self,
        symbol: str,
        current_price: float,
        options_chain: List[OptionContract],
        market_data: MarketData,
    ) -> Optional[OptionContract]:
        """Select a long put option.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            options_chain: Available options
            market_data: Market data for volatility analysis
            
        Returns:
            Selected put option or None if no valid option found
        """
        # Filter puts with valid expiration and liquidity
        puts = [
            opt for opt in options_chain
            if opt.contract_type == "put"
            and config.LONG_CALL_PUT_MIN_DTE <= opt.days_to_expiration <= config.LONG_CALL_PUT_MAX_DTE
            and opt.volume >= config.LONG_CALL_PUT_MIN_VOLUME
            and opt.open_interest >= config.LONG_CALL_PUT_MIN_OPEN_INTEREST
            and opt.liquidity_score >= config.LONG_CALL_PUT_MIN_LIQUIDITY_SCORE
        ]
        
        if not puts:
            return None
        
        # Filter by delta range (negative delta, -0.70 to -0.40 for bearish directional trades)
        delta_filtered = [
            put for put in puts
            if hasattr(put, 'delta') and -config.LONG_CALL_PUT_MAX_DELTA <= put.delta <= -config.LONG_CALL_PUT_MIN_DELTA
        ]
        
        # If no delta data, use strike-based filtering (ATM to slightly OTM)
        if not delta_filtered:
            delta_filtered = [
                put for put in puts
                if put.strike >= current_price * (1 - config.LONG_CALL_PUT_MAX_OTM_THRESHOLD)
            ]
        
        if not delta_filtered:
            return None
        
        # Score and select best option
        best_option = None
        best_score = -1.0
        
        for put in delta_filtered:
            score = self._score_option(put, market_data)
            if score > best_score:
                best_score = score
                best_option = put
        
        return best_option

    def _score_option(self, option: OptionContract, market_data: MarketData) -> float:
        """Score an option based on multiple factors.
        
        Args:
            option: Option contract to score
            market_data: Market data for context
            
        Returns:
            Score from 0.0 to 1.0
        """
        # Liquidity score (0-100 normalized to 0-1)
        liquidity_score = min(option.liquidity_score / 100.0, 1.0)
        
        # Volatility score (higher IV is better for long options)
        volatility_score = min(option.implied_volatility / 0.5, 1.0)  # Normalize assuming max IV ~50%
        
        # Time decay score (prefer more time)
        dte_score = min(option.days_to_expiration / config.LONG_CALL_PUT_MAX_DTE, 1.0)
        
        # Combine scores
        combined_score = (
            liquidity_score * 0.4 +
            volatility_score * 0.4 +
            dte_score * 0.2
        )
        
        return combined_score

    def _estimate_max_profit(self, option: OptionContract, current_price: float) -> float:
        """Estimate maximum profit potential.
        
        Args:
            option: Option contract
            current_price: Current stock price
            
        Returns:
            Estimated max profit in dollars
        """
        premium = (option.bid + option.ask) / 2
        
        if option.contract_type == "call":
            # For long call, max profit is theoretically unlimited
            # Estimate as 2x the premium (conservative estimate)
            return premium * 2.0
        else:
            # For long put, max profit is strike - premium
            return max(option.strike - premium, 0.0)

    def _calculate_score(self, option: OptionContract, market_data: MarketData, news_context: Optional[NewsContext]) -> float:
        """Calculate signal score based on multiple factors.
        
        Args:
            option: Option contract
            market_data: Market data
            news_context: Optional news context
            
        Returns:
            Score from 0.0 to 1.0
        """
        # Option quality score
        option_score = self._score_option(option, market_data)
        
        # Trend score
        trend_score = (self._analyze_trend(market_data.price_history) + 1.0) / 2.0  # Normalize to 0-1
        
        # News sentiment score
        sentiment_score = 0.5  # Neutral default
        if news_context and news_context.sentiment_score is not None:
            sentiment_score = (news_context.sentiment_score + 1.0) / 2.0  # Normalize to 0-1
        
        # Combine scores
        combined_score = (
            option_score * 0.5 +
            trend_score * 0.3 +
            sentiment_score * 0.2
        )
        
        return combined_score

    def _estimate_probability(self, option: OptionContract, market_data: MarketData, news_context: Optional[NewsContext]) -> float:
        """Estimate probability of profit.
        
        Args:
            option: Option contract
            market_data: Market data
            news_context: Optional news context
            
        Returns:
            Probability estimate from 0.0 to 1.0
        """
        # Use delta as proxy for probability (delta ≈ probability ITM)
        if hasattr(option, 'delta'):
            if option.contract_type == "call":
                return abs(option.delta)
            else:
                return abs(option.delta)
        
        # Fallback: use trend and sentiment
        trend_score = (self._analyze_trend(market_data.price_history) + 1.0) / 2.0
        sentiment_score = 0.5
        if news_context and news_context.sentiment_score is not None:
            sentiment_score = (news_context.sentiment_score + 1.0) / 2.0
        
        return trend_score * 0.6 + sentiment_score * 0.4

    def _generate_reason(self, option: OptionContract, is_bullish: bool, market_data: MarketData, news_context: Optional[NewsContext]) -> str:
        """Generate explanation for the signal.
        
        Args:
            option: Option contract
            is_bullish: Whether position is bullish
            market_data: Market data
            news_context: Optional news context
            
        Returns:
            Explanation string
        """
        direction = "bullish" if is_bullish else "bearish"
        option_type = "call" if is_bullish else "put"
        
        trend_score = self._analyze_trend(market_data.price_history)
        trend_desc = "strong uptrend" if trend_score > 0.5 else "uptrend" if trend_score > 0 else "downtrend" if trend_score < -0.5 else "downtrend"
        
        sentiment_desc = ""
        if news_context and news_context.sentiment_score is not None:
            if news_context.sentiment_score > 0.3:
                sentiment_desc = " with positive sentiment"
            elif news_context.sentiment_score < -0.3:
                sentiment_desc = " with negative sentiment"
        
        premium = (option.bid + option.ask) / 2
        
        return (
            f"High-risk {direction} long {option_type} at ${option.strike:.2f} strike "
            f"({trend_desc}{sentiment_desc}). "
            f"Premium at risk: ${premium:.2f}. "
            f"Max loss equals premium paid. "
            f"DTE: {option.days_to_expiration}."
        )
