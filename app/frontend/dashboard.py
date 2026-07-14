"""Dashboard service for aggregating user portfolio and trading data.

Provides a unified interface for fetching dashboard data including:
- Portfolio summary (total value, cash, positions, P/L)
- Watchlist symbols with current prices
- Top opportunities (ranked signals)
- Open trades with current P/L
- Recent news articles
- User risk settings
- Signal detail pages with full explanation
"""

import logging
import json
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
    """Watchlist item with current price and data freshness."""
    symbol: str
    current_price: Optional[float]
    added_at: datetime
    last_updated: Optional[datetime] = None  # When price was last fetched
    data_freshness_seconds: Optional[int] = None  # How old the price data is


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
class RiskLevelInfo:
    """Information about a risk level."""
    level: str  # "low", "medium", "high"
    description: str
    max_position_size_pct: float  # Max position size as % of portfolio
    allowed_strategies: List[str]
    max_loss_per_trade_pct: float  # Max loss per trade as % of portfolio
    requires_confirmation: bool  # Whether this level requires explicit confirmation


@dataclass
class RiskSettings:
    """User risk settings."""
    risk_level: str  # "low", "medium", "high"
    paper_trading_enabled: bool
    live_trading_enabled: bool
    live_trading_approved: bool
    risk_levels_info: List[RiskLevelInfo]  # Info about each risk level


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


@dataclass
class ContractDetail:
    """Option contract detail for signal."""
    contract_id: int
    symbol: str
    expiration: str
    strike: float
    contract_type: str  # call or put
    bid: float
    ask: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: Optional[float]
    gamma: Optional[float]
    theta: Optional[float]
    vega: Optional[float]
    underlying_price: float
    days_to_expiration: int
    liquidity_score: Optional[float]


@dataclass
class SignalDetail:
    """Complete signal detail page data."""
    signal_id: int
    symbol: str
    strategy_type: str
    risk_level: str
    score: float  # 0-100
    expected_profit: float
    max_loss: float
    probability_estimate: float
    reason: str  # Strategy summary
    status: str
    created_at: datetime
    updated_at: datetime
    
    # Sections
    breakdown: Optional[Dict[str, float]]  # Score breakdown
    contracts: List[ContractDetail]  # Contracts involved
    event_risks: Optional[Dict[str, Any]]  # Event risk details
    exit_rules: List[Dict[str, Any]]  # Exit plan
    related_news: List[NewsItem]  # News context
    related_trades: List[TradeItem]  # Backtest/paper history
    
    # Greeks summary
    greeks_summary: Optional[Dict[str, float]]  # Aggregate Greeks


class Dashboard:
    """Dashboard service for aggregating user portfolio and trading data."""

    # Risk level configurations
    RISK_LEVEL_CONFIGS = {
        "low": RiskLevelInfo(
            level="low",
            description="Conservative: Favors high liquidity, defined risk, lower max loss",
            max_position_size_pct=2.0,
            allowed_strategies=["covered_call", "cash_secured_put"],
            max_loss_per_trade_pct=1.0,
            requires_confirmation=False,
        ),
        "medium": RiskLevelInfo(
            level="medium",
            description="Balanced: Allows wider reward/risk ratios with moderate risk",
            max_position_size_pct=5.0,
            allowed_strategies=["covered_call", "cash_secured_put", "debit_spread", "credit_spread"],
            max_loss_per_trade_pct=2.0,
            requires_confirmation=False,
        ),
        "high": RiskLevelInfo(
            level="high",
            description="Aggressive: Allows volatility and lower probability if payoff is larger",
            max_position_size_pct=10.0,
            allowed_strategies=["covered_call", "cash_secured_put", "debit_spread", "credit_spread", "long_call", "long_put"],
            max_loss_per_trade_pct=5.0,
            requires_confirmation=True,
        ),
    }

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
            portfolio = self.broker_provider.get_portfolio(user_id=user_id, db=db)

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
                    last_updated=None,
                    data_freshness_seconds=None,
                )
                for symbol in symbols
            ]

            return items
        except Exception as e:
            logger.error(f"Error getting watchlist for user {user_id}: {e}", exc_info=True)
            return []

    def validate_symbol(self, symbol: str) -> Dict[str, Any]:
        """Validate a stock symbol format.

        Args:
            symbol: Stock symbol to validate

        Returns:
            Dictionary with valid, message, and symbol
        """
        try:
            if not symbol or not isinstance(symbol, str):
                return {
                    "valid": False,
                    "message": "Symbol must be a non-empty string",
                    "symbol": symbol,
                }
            
            symbol_upper = symbol.upper().strip()
            
            # Symbol should be 1-5 characters, alphanumeric
            if not (1 <= len(symbol_upper) <= 5 and symbol_upper.isalpha()):
                return {
                    "valid": False,
                    "message": f"Invalid symbol format. Must be 1-5 letters (got '{symbol_upper}')",
                    "symbol": symbol_upper,
                }
            
            return {
                "valid": True,
                "message": "Symbol is valid",
                "symbol": symbol_upper,
            }
        except Exception as e:
            logger.error(f"Error validating symbol {symbol}: {e}", exc_info=True)
            return {
                "valid": False,
                "message": "Error validating symbol",
                "symbol": symbol,
            }

    def add_symbol(
        self,
        user_id: int,
        symbol: str,
        db: Session,
        watchlist_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Add a symbol to user's watchlist.

        Args:
            user_id: User ID
            symbol: Stock symbol to add
            db: Database session
            watchlist_id: Optional specific watchlist ID. If None, uses first watchlist.

        Returns:
            Dictionary with status and message
        """
        try:
            # Validate symbol format
            validation = self.validate_symbol(symbol)
            if not validation["valid"]:
                return {
                    "status": "error",
                    "message": validation["message"],
                    "symbol": symbol,
                }
            
            symbol = validation["symbol"]
            
            # Get user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"status": "error", "message": "User not found", "symbol": symbol}
            
            # Get or create watchlist
            if watchlist_id:
                watchlist = db.query(Watchlist).filter(
                    Watchlist.id == watchlist_id,
                    Watchlist.user_id == user_id,
                ).first()
                if not watchlist:
                    return {
                        "status": "error",
                        "message": "Watchlist not found",
                        "symbol": symbol,
                    }
            else:
                # Get first watchlist or create default
                watchlist = db.query(Watchlist).filter(
                    Watchlist.user_id == user_id,
                ).first()
                
                if not watchlist:
                    watchlist = Watchlist(
                        user_id=user_id,
                        name="Default Watchlist",
                        description="Default watchlist",
                    )
                    db.add(watchlist)
                    db.commit()
            
            # Check if symbol already exists
            existing = db.query(WatchlistSymbol).filter(
                WatchlistSymbol.watchlist_id == watchlist.id,
                WatchlistSymbol.symbol == symbol,
            ).first()
            
            if existing:
                return {
                    "status": "error",
                    "message": f"Symbol {symbol} already in watchlist",
                    "symbol": symbol,
                }
            
            # Add symbol
            ws = WatchlistSymbol(
                watchlist_id=watchlist.id,
                symbol=symbol,
            )
            db.add(ws)
            db.commit()
            
            return {
                "status": "success",
                "message": f"Symbol {symbol} added to watchlist",
                "symbol": symbol,
            }
        except Exception as e:
            logger.error(f"Error adding symbol {symbol} for user {user_id}: {e}", exc_info=True)
            db.rollback()
            return {
                "status": "error",
                "message": "Failed to add symbol",
                "symbol": symbol,
            }

    def remove_symbol(
        self,
        user_id: int,
        symbol: str,
        db: Session,
        watchlist_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Remove a symbol from user's watchlist.

        Args:
            user_id: User ID
            symbol: Stock symbol to remove
            db: Database session
            watchlist_id: Optional specific watchlist ID

        Returns:
            Dictionary with status and message
        """
        try:
            symbol = symbol.upper().strip()
            
            # Get user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"status": "error", "message": "User not found", "symbol": symbol}
            
            # Find watchlist
            query = db.query(Watchlist).filter(Watchlist.user_id == user_id)
            if watchlist_id:
                query = query.filter(Watchlist.id == watchlist_id)
            
            watchlist = query.first()
            if not watchlist:
                return {
                    "status": "error",
                    "message": "Watchlist not found",
                    "symbol": symbol,
                }
            
            # Find and remove symbol
            ws = db.query(WatchlistSymbol).filter(
                WatchlistSymbol.watchlist_id == watchlist.id,
                WatchlistSymbol.symbol == symbol,
            ).first()
            
            if not ws:
                return {
                    "status": "error",
                    "message": f"Symbol {symbol} not in watchlist",
                    "symbol": symbol,
                }
            
            db.delete(ws)
            db.commit()
            
            return {
                "status": "success",
                "message": f"Symbol {symbol} removed from watchlist",
                "symbol": symbol,
            }
        except Exception as e:
            logger.error(f"Error removing symbol {symbol} for user {user_id}: {e}", exc_info=True)
            db.rollback()
            return {
                "status": "error",
                "message": "Failed to remove symbol",
                "symbol": symbol,
            }

    def get_top_opportunities(
        self,
        user_id: int,
        db: Session,
        limit: int = 10,
    ) -> List[OpportunityItem]:
        """Get top ranked opportunities for user."""
        try:
            # Accept both app-generated pending signals and dev-generated open signals.
            signals = (
                db.query(Signal)
                .filter(
                    Signal.user_id == user_id,
                    Signal.status.in_(["pending", "open"]),
                )
                .order_by(Signal.score.desc())
                .limit(limit)
                .all()
            )

            items = []

            for signal in signals:
                contract = None
                if signal.option_contract_id:
                    contract = (
                        db.query(OptionContract)
                        .filter(OptionContract.id == signal.option_contract_id)
                        .first()
                    )

                raw_score = float(signal.score or 0.0)
                display_score = raw_score * 100.0 if raw_score <= 1.0 else raw_score

                raw_probability = signal.probability_estimate
                if raw_probability is None:
                    probability = raw_score if raw_score <= 1.0 else raw_score / 100.0
                else:
                    probability = float(raw_probability)
                    if probability > 1.0:
                        probability = probability / 100.0

                breakdown = None
                if signal.breakdown:
                    try:
                        breakdown = json.loads(signal.breakdown)
                    except Exception:
                        breakdown = {"raw": signal.breakdown}

                items.append(
                    OpportunityItem(
                        signal_id=signal.id,
                        symbol=signal.symbol or (contract.symbol if contract else "UNKNOWN"),
                        strategy_type=signal.strategy_type,
                        score=round(display_score, 2),
                        expected_profit=float(signal.expected_profit or 0.0),
                        max_loss=float(signal.max_loss or 0.0),
                        probability_estimate=round(probability, 4),
                        reason=signal.reason or "No reason provided",
                        status=signal.status,
                        created_at=signal.created_at,
                        breakdown=breakdown,
                    )
                )

            return items

        except Exception as e:
            logger.error(
                f"Error getting top opportunities for user {user_id}: {e}",
                exc_info=True,
            )
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
            List of TradeItem objects
        """
        try:
            trades = db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.status == "open",
            ).all()
            
            items = []
            for trade in trades:
                signal = None
                contract = None

                if getattr(trade, "signal_id", None):
                    signal = (
                        db.query(Signal)
                        .filter(Signal.id == trade.signal_id)
                        .first()
                    )

                if getattr(trade, "option_contract_id", None):
                    contract = (
                        db.query(OptionContract)
                        .filter(OptionContract.id == trade.option_contract_id)
                        .first()
                    )

                if signal and getattr(signal, "symbol", None):
                    symbol = signal.symbol
                elif contract and getattr(contract, "symbol", None):
                    symbol = contract.symbol
                else:
                    symbol = "UNKNOWN"

                strategy_type = (
                    signal.strategy_type
                    if signal and getattr(signal, "strategy_type", None)
                    else "unknown"
                )

                entry_date = (
                    getattr(trade, "entry_date", None)
                    or getattr(trade, "opened_at", None)
                    or getattr(trade, "created_at", None)
                    or datetime.utcnow()
                )

                items.append(
                    TradeItem(
                        trade_id=trade.id,
                        symbol=symbol,
                        strategy_type=strategy_type,
                        entry_price=float(trade.entry_price or 0.0),
                        current_price=None,  # Would fetch from data provider
                        quantity=int(trade.quantity or 0),
                        entry_date=entry_date,
                        current_pl=None,  # Would calculate later
                        current_pl_pct=None,  # Would calculate later
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
        limit: int = 10,
    ) -> List[NewsItem]:
        """Get recent news for user's watchlist symbols.

        Args:
            user_id: User ID
            db: Database session
            limit: Maximum number of articles

        Returns:
            List of NewsItem objects
        """
        try:
            # Get watchlist symbols
            watchlist_symbols = db.query(WatchlistSymbol).join(Watchlist).filter(
                Watchlist.user_id == user_id,
            ).all()
            
            symbols = [ws.symbol for ws in watchlist_symbols]
            
            if not symbols:
                return []
            
            # Get recent news for those symbols
            articles = db.query(NewsArticle).filter(
                NewsArticle.symbol.in_(symbols),
            ).order_by(NewsArticle.published_at.desc()).limit(limit).all()
            
            items = []
            for article in articles:
                items.append(
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
                )
            
            return items
        except Exception as e:
            logger.error(f"Error getting recent news for user {user_id}: {e}", exc_info=True)
            return []

    def get_risk_settings(
        self,
        user_id: int,
        db: Session,
    ) -> RiskSettings:
        """Get user risk settings.

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
                    risk_levels_info=list(self.RISK_LEVEL_CONFIGS.values()),
                )
            
            return RiskSettings(
                risk_level=user.risk_level or "medium",
                paper_trading_enabled=user.paper_trading_enabled,
                live_trading_enabled=user.live_trading_enabled,
                live_trading_approved=user.live_trading_approved,
                risk_levels_info=list(self.RISK_LEVEL_CONFIGS.values()),
            )
        except Exception as e:
            logger.error(f"Error getting risk settings for user {user_id}: {e}", exc_info=True)
            return RiskSettings(
                risk_level="medium",
                paper_trading_enabled=True,
                live_trading_enabled=False,
                live_trading_approved=False,
                risk_levels_info=list(self.RISK_LEVEL_CONFIGS.values()),
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
            DashboardData with all sections
        """
        try:
            return DashboardData(
                portfolio_summary=self.get_portfolio_summary(user_id, db),
                watchlist=self.get_watchlist(user_id, db, watchlist_id),
                top_opportunities=self.get_top_opportunities(user_id, db, limit=5),
                open_trades=self.get_open_trades(user_id, db),
                recent_news=self.get_recent_news(user_id, db, limit=5),
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
                risk_settings=self.get_risk_settings(user_id, db),
                timestamp=datetime.utcnow(),
            )

    def update_risk_level(
        self,
        user_id: int,
        risk_level: str,
        db,
        confirmed: bool = False,
    ) -> dict:
        """Update a user's risk level."""
        from app.models.database import User

        normalized_risk_level = (risk_level or "").strip().lower()
        valid_risk_levels = {"low", "medium", "high"}

        if normalized_risk_level not in valid_risk_levels:
            return {
                "status": "error",
                "message": (
                    "Invalid risk level. Expected one of: "
                    "low, medium, high"
                ),
            }

        if normalized_risk_level == "high" and not confirmed:
            return {
                "status": "confirmation_required",
                "message": "High risk level requires explicit confirmation",
                "risk_level": normalized_risk_level,
                "requires_confirmation": True,
            }

        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return {
                "status": "error",
                "message": f"User {user_id} not found",
            }

        user.risk_level = normalized_risk_level
        db.commit()
        db.refresh(user)

        return {
            "status": "success",
            "message": f"Risk level updated to {normalized_risk_level}",
            "risk_level": user.risk_level,
        }

