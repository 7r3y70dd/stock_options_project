"""Dashboard service for aggregating user portfolio and trading data.

Provides a unified interface for fetching dashboard data including:
- Portfolio summary (total value, cash, positions, P/L)
- Watchlist symbols with current prices
- Top opportunities (ranked signals)
- Open trades with current P/L
- Recent news articles
- User risk settings
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.database import (
    User,
    Watchlist,
    WatchlistSymbol,
    Signal,
    Trade,
    OptionContract,
    NewsArticle,
)
from app.core.scoring import SignalScorer
from app.core.paper_broker_provider import PaperBrokerProvider
from services import RiskLevel

logger = logging.getLogger(__name__)


@dataclass
class PortfolioSummary:
    """Portfolio summary data."""
    total_value: float  # Total portfolio value
    cash: float  # Available cash
    positions_value: float  # Value of open positions
    open_pl: float  # Open profit/loss
    open_pl_pct: float  # Open P/L as percentage
    num_open_trades: int  # Number of open trades
    num_open_signals: int  # Number of pending signals


@dataclass
class WatchlistItem:
    """Watchlist item with current price."""
    symbol: str
    current_price: Optional[float]
    added_at: datetime


@dataclass
class OpportunityItem:
    """Top opportunity (ranked signal)."""
    signal_id: int
    symbol: str
    strategy_type: str
    score: float  # 0-100
    expected_profit: float
    max_loss: float
    probability_estimate: float
    reason: str
    status: str
    created_at: datetime
    breakdown: Optional[Dict[str, float]]


@dataclass
class TradeItem:
    """Open trade with current P/L."""
    trade_id: int
    symbol: str
    strategy_type: str
    entry_price: float
    current_price: Optional[float]
    quantity: int
    entry_date: datetime
    current_pl: Optional[float]  # Current profit/loss
    current_pl_pct: Optional[float]  # Current P/L as percentage
    status: str


@dataclass
class NewsItem:
    """Recent news article."""
    article_id: int
    symbol: str
    title: str
    description: Optional[str]
    url: Optional[str]
    source: Optional[str]
    published_at: Optional[datetime]
    sentiment: Optional[str]  # "positive", "negative", "neutral"
    sentiment_score: Optional[float]  # -1.0 to 1.0
    event_type: Optional[str]


@dataclass
class RiskSettings:
    """User risk settings."""
    risk_level: str  # "low", "medium", "high"
    paper_trading_enabled: bool
    live_trading_enabled: bool
    live_trading_approved: bool


@dataclass
class DashboardData:
    """Complete dashboard data."""
    portfolio_summary: PortfolioSummary
    watchlist: List[WatchlistItem]
    top_opportunities: List[OpportunityItem]
    open_trades: List[TradeItem]
    recent_news: List[NewsItem]
    risk_settings: RiskSettings
    timestamp: datetime


class Dashboard:
    """Dashboard service for aggregating user portfolio and trading data."""

    def __init__(
        self,
        broker_provider: Optional[PaperBrokerProvider] = None,
    ):
        """Initialize dashboard service.

        Args:
            broker_provider: Optional broker provider for P/L calculations
        """
        self.broker_provider = broker_provider or PaperBrokerProvider()

    def get_portfolio_summary(
        self,
        user_id: int,
        db: Session,
    ) -> PortfolioSummary:
        """Get portfolio summary for user.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            PortfolioSummary with portfolio metrics
        """
        try:
            # Get user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found")
                return PortfolioSummary(
                    total_value=0.0,
                    cash=0.0,
                    positions_value=0.0,
                    open_pl=0.0,
                    open_pl_pct=0.0,
                    num_open_trades=0,
                    num_open_signals=0,
                )

            # Get portfolio from broker
            portfolio = self.broker_provider.get_portfolio()

            # Count open trades and signals
            open_trades = db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.status == "open",
            ).all()
            num_open_trades = len(open_trades)

            pending_signals = db.query(Signal).filter(
                Signal.user_id == user_id,
                Signal.status == "pending",
            ).all()
            num_open_signals = len(pending_signals)

            # Calculate P/L
            total_value = portfolio.get("total_value", user.initial_portfolio_value)
            cash = portfolio.get("cash", user.initial_portfolio_value)
            positions_value = total_value - cash
            open_pl = total_value - user.initial_portfolio_value
            open_pl_pct = (open_pl / user.initial_portfolio_value * 100) if user.initial_portfolio_value > 0 else 0.0

            return PortfolioSummary(
                total_value=total_value,
                cash=cash,
                positions_value=positions_value,
                open_pl=open_pl,
                open_pl_pct=open_pl_pct,
                num_open_trades=num_open_trades,
                num_open_signals=num_open_signals,
            )
        except Exception as e:
            logger.error(f"Error getting portfolio summary for user {user_id}: {e}", exc_info=True)
            return PortfolioSummary(
                total_value=0.0,
                cash=0.0,
                positions_value=0.0,
                open_pl=0.0,
                open_pl_pct=0.0,
                num_open_trades=0,
                num_open_signals=0,
            )

    def get_watchlist(
        self,
        user_id: int,
        db: Session,
        watchlist_id: Optional[int] = None,
    ) -> List[WatchlistItem]:
        """Get watchlist items for user.

        Args:
            user_id: User ID
            db: Database session
            watchlist_id: Optional specific watchlist ID

        Returns:
            List of WatchlistItem objects
        """
        try:
            # Get watchlist symbols
            query = db.query(WatchlistSymbol).join(Watchlist).filter(
                Watchlist.user_id == user_id,
            )

            if watchlist_id:
                query = query.filter(Watchlist.id == watchlist_id)

            symbols = query.all()

            # Convert to WatchlistItem (price data would come from data provider)
            items = [
                WatchlistItem(
                    symbol=symbol.symbol,
                    current_price=None,  # Would be fetched from data provider
                    added_at=symbol.added_at,
                )
                for symbol in symbols
            ]

            return items
        except Exception as e:
            logger.error(f"Error getting watchlist for user {user_id}: {e}", exc_info=True)
            return []

    def get_top_opportunities(
        self,
        user_id: int,
        db: Session,
        limit: int = 10,
    ) -> List[OpportunityItem]:
        """Get top ranked opportunities (signals) for user.

        Args:
            user_id: User ID
            db: Database session
            limit: Maximum number of opportunities to return

        Returns:
            List of OpportunityItem objects sorted by score (highest first)
        """
        try:
            # Get pending signals sorted by score (highest first)
            signals = db.query(Signal).filter(
                Signal.user_id == user_id,
                Signal.status == "pending",
            ).order_by(Signal.score.desc()).limit(limit).all()

            items = []
            for signal in signals:
                # Parse breakdown if available
                breakdown = None
                if signal.breakdown:
                    try:
                        import json
                        breakdown = json.loads(signal.breakdown)
                    except Exception:
                        pass

                items.append(
                    OpportunityItem(
                        signal_id=signal.id,
                        symbol=signal.symbol,
                        strategy_type=signal.strategy_type,
                        score=signal.score * 100.0 if signal.score <= 1.0 else signal.score,  # Normalize to 0-100
                        expected_profit=signal.expected_profit,
                        max_loss=signal.max_loss,
                        probability_estimate=signal.probability_estimate,
                        reason=signal.reason,
                        status=signal.status,
                        created_at=signal.created_at,
                        breakdown=breakdown,
                    )
                )

            return items
        except Exception as e:
            logger.error(f"Error getting top opportunities for user {user_id}: {e}", exc_info=True)
            return []

    def get_open_trades(
        self,
        user_id: int,
        db: Session,
    ) -> List[TradeItem]:
        """Get open trades for user.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            List of TradeItem objects with current P/L
        """
        try:
            # Get open trades
            trades = db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.status == "open",
            ).all()

            items = []
            for trade in trades:
                # Calculate current P/L (would use current price from data provider)
                current_pl = None
                current_pl_pct = None

                if trade.entry_price and trade.quantity:
                    # Placeholder: would fetch current price from data provider
                    current_price = trade.entry_price  # Default to entry price
                    current_pl = (current_price - trade.entry_price) * trade.quantity
                    current_pl_pct = ((current_price - trade.entry_price) / trade.entry_price * 100) if trade.entry_price > 0 else 0.0

                items.append(
                    TradeItem(
                        trade_id=trade.id,
                        symbol=trade.symbol,
                        strategy_type=trade.strategy_type,
                        entry_price=trade.entry_price,
                        current_price=current_price if trade.entry_price else None,
                        quantity=trade.quantity,
                        entry_date=trade.entry_date,
                        current_pl=current_pl,
                        current_pl_pct=current_pl_pct,
                        status=trade.status,
                    )
                )

            return items
        except Exception as e:
            logger.error(f"Error getting open trades for user {user_id}: {e}", exc_info=True)
            return []

    def get_recent_news(
        self,
        user_id: int,
        db: Session,
        days: int = 7,
        limit: int = 20,
    ) -> List[NewsItem]:
        """Get recent news for user's watchlist symbols.

        Args:
            user_id: User ID
            db: Database session
            days: Number of days to look back
            limit: Maximum number of articles to return

        Returns:
            List of NewsItem objects sorted by published date (newest first)
        """
        try:
            # Get user's watchlist symbols
            watchlist_symbols = db.query(WatchlistSymbol).join(Watchlist).filter(
                Watchlist.user_id == user_id,
            ).all()

            symbols = [ws.symbol for ws in watchlist_symbols]

            if not symbols:
                return []

            # Get recent news for these symbols
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            articles = db.query(NewsArticle).filter(
                NewsArticle.symbol.in_(symbols),
                NewsArticle.fetched_at >= cutoff_date,
            ).order_by(NewsArticle.published_at.desc()).limit(limit).all()

            items = [
                NewsItem(
                    article_id=article.id,
                    symbol=article.symbol,
                    title=article.title,
                    description=article.description,
                    url=article.url,
                    source=article.source,
                    published_at=article.published_at,
                    sentiment=article.sentiment,
                    sentiment_score=article.sentiment_score,
                    event_type=article.event_type,
                )
                for article in articles
            ]

            return items
        except Exception as e:
            logger.error(f"Error getting recent news for user {user_id}: {e}", exc_info=True)
            return []

    def get_risk_settings(
        self,
        user_id: int,
        db: Session,
    ) -> RiskSettings:
        """Get user's risk settings.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            RiskSettings object
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found")
                return RiskSettings(
                    risk_level="medium",
                    paper_trading_enabled=True,
                    live_trading_enabled=False,
                    live_trading_approved=False,
                )

            return RiskSettings(
                risk_level=user.risk_level,
                paper_trading_enabled=user.paper_trading_enabled,
                live_trading_enabled=user.live_trading_enabled,
                live_trading_approved=user.live_trading_approved,
            )
        except Exception as e:
            logger.error(f"Error getting risk settings for user {user_id}: {e}", exc_info=True)
            return RiskSettings(
                risk_level="medium",
                paper_trading_enabled=True,
                live_trading_enabled=False,
                live_trading_approved=False,
            )

    def get_dashboard_data(
        self,
        user_id: int,
        db: Session,
        watchlist_id: Optional[int] = None,
    ) -> DashboardData:
        """Get complete dashboard data for user.

        Args:
            user_id: User ID
            db: Database session
            watchlist_id: Optional specific watchlist ID

        Returns:
            DashboardData with all dashboard sections
        """
        try:
            return DashboardData(
                portfolio_summary=self.get_portfolio_summary(user_id, db),
                watchlist=self.get_watchlist(user_id, db, watchlist_id),
                top_opportunities=self.get_top_opportunities(user_id, db),
                open_trades=self.get_open_trades(user_id, db),
                recent_news=self.get_recent_news(user_id, db),
                risk_settings=self.get_risk_settings(user_id, db),
                timestamp=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"Error getting dashboard data for user {user_id}: {e}", exc_info=True)
            # Return empty dashboard on error
            return DashboardData(
                portfolio_summary=PortfolioSummary(
                    total_value=0.0,
                    cash=0.0,
                    positions_value=0.0,
                    open_pl=0.0,
                    open_pl_pct=0.0,
                    num_open_trades=0,
                    num_open_signals=0,
                ),
                watchlist=[],
                top_opportunities=[],
                open_trades=[],
                recent_news=[],
                risk_settings=RiskSettings(
                    risk_level="medium",
                    paper_trading_enabled=True,
                    live_trading_enabled=False,
                    live_trading_approved=False,
                ),
                timestamp=datetime.utcnow(),
            )
