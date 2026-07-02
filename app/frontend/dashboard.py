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
                    last_updated=None,
                    data_freshness_seconds=None,
                )
                for symbol in symbols
            ]

            return items
        except Exception as e:
            logger.error(f"Error getting watchlist for user {user_id}: {e}", exc_info=True)
            return []

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
            if not symbol or not isinstance(symbol, str):
                return {"status": "error", "message": "Invalid symbol format"}
            
            symbol = symbol.upper().strip()
            
            # Symbol should be 1-5 characters, alphanumeric
            if not (1 <= len(symbol) <= 5 and symbol.isalpha()):
                return {"status": "error", "message": f"Invalid symbol: {symbol}. Must be 1-5 letters."}
            
            # Get user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"status": "error", "message": "User not found"}
            
            # Get or create watchlist
            if watchlist_id:
                watchlist = db.query(Watchlist).filter(
                    Watchlist.id == watchlist_id,
                    Watchlist.user_id == user_id,
                ).first()
            else:
                # Get first watchlist or create default
                watchlist = db.query(Watchlist).filter(
                    Watchlist.user_id == user_id,
                ).first()
                
                if not watchlist:
                    watchlist = Watchlist(
                        user_id=user_id,
                        name="Default Watchlist",
                    )
                    db.add(watchlist)
                    db.commit()
            
            if not watchlist:
                return {"status": "error", "message": "Watchlist not found"}
            
            # Check if symbol already exists
            existing = db.query(WatchlistSymbol).filter(
                WatchlistSymbol.watchlist_id == watchlist.id,
                WatchlistSymbol.symbol == symbol,
            ).first()
            
            if existing:
                return {"status": "error", "message": f"Symbol {symbol} already in watchlist"}
            
            # Add symbol
            ws = WatchlistSymbol(
                watchlist_id=watchlist.id,
                symbol=symbol,
            )
            db.add(ws)
            db.commit()
            
            logger.info(f"Added symbol {symbol} to watchlist {watchlist.id} for user {user_id}")
            return {"status": "success", "message": f"Symbol {symbol} added to watchlist", "symbol": symbol}
        except Exception as e:
            logger.error(f"Error adding symbol {symbol} for user {user_id}: {e}", exc_info=True)
            db.rollback()
            return {"status": "error", "message": f"Failed to add symbol: {str(e)}"}

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
                return {"status": "error", "message": "User not found"}
            
            # Find and remove symbol
            query = db.query(WatchlistSymbol).join(Watchlist).filter(
                Watchlist.user_id == user_id,
                WatchlistSymbol.symbol == symbol,
            )
            
            if watchlist_id:
                query = query.filter(Watchlist.id == watchlist_id)
            
            ws = query.first()
            
            if not ws:
                return {"status": "error", "message": f"Symbol {symbol} not found in watchlist"}
            
            db.delete(ws)
            db.commit()
            
            logger.info(f"Removed symbol {symbol} from watchlist for user {user_id}")
            return {"status": "success", "message": f"Symbol {symbol} removed from watchlist", "symbol": symbol}
        except Exception as e:
            logger.error(f"Error removing symbol {symbol} for user {user_id}: {e}", exc_info=True)
            db.rollback()
            return {"status": "error", "message": f"Failed to remove symbol: {str(e)}"}

    def validate_symbol(self, symbol: str) -> Dict[str, Any]:
        """Validate a stock symbol format.

        Args:
            symbol: Stock symbol to validate

        Returns:
            Dictionary with validation result
        """
        try:
            if not symbol or not isinstance(symbol, str):
                return {"valid": False, "message": "Invalid symbol format"}
            
            symbol = symbol.upper().strip()
            
            # Symbol should be 1-5 characters, alphanumeric
            if not (1 <= len(symbol) <= 5 and symbol.isalpha()):
                return {"valid": False, "message": f"Symbol must be 1-5 letters"}
            
            return {"valid": True, "symbol": symbol}
        except Exception as e:
            logger.error(f"Error validating symbol {symbol}: {e}", exc_info=True)
            return {"valid": False, "message": f"Validation error: {str(e)}"}

    def get_top_opportunities(
        self,
        user_id: int,
        db: Session,
        limit: int = 10,
    ) -> List[OpportunityItem]:
        """Get top ranked opportunities for user.

        Args:
            user_id: User ID
            db: Database session
            limit: Maximum number of opportunities

        Returns:
            List of top opportunities sorted by score
        """
        try:
            signals = db.query(Signal).filter(
                Signal.user_id == user_id,
                Signal.status == "pending",
            ).order_by(Signal.score.desc()).limit(limit).all()

            items = []
            for signal in signals:
                breakdown = None
                if signal.breakdown:
                    try:
                        breakdown = json.loads(signal.breakdown)
                    except (json.JSONDecodeError, TypeError):
                        breakdown = None
                
                items.append(OpportunityItem(
                    signal_id=signal.id,
                    symbol=signal.symbol,
                    strategy_type=signal.strategy_type,
                    score=signal.score,
                    expected_profit=signal.expected_profit,
                    max_loss=signal.max_loss,
                    probability_estimate=signal.probability_estimate,
                    reason=signal.reason,
                    status=signal.status,
                    created_at=signal.created_at,
                    breakdown=breakdown,
                ))
            
            return items
        except Exception as e:
            logger.error(f"Error getting top opportunities for user {user_id}: {e}", exc_info=True)
            return []

    def get_signal_detail(
        self,
        user_id: int,
        signal_id: int,
        db: Session,
    ) -> Optional[SignalDetail]:
        """Get complete signal detail page data.

        Args:
            user_id: User ID
            signal_id: Signal ID
            db: Database session

        Returns:
            SignalDetail with all sections or None if not found
        """
        try:
            # Get signal
            signal = db.query(Signal).filter(
                Signal.id == signal_id,
                Signal.user_id == user_id,
            ).first()
            
            if not signal:
                logger.warning(f"Signal {signal_id} not found for user {user_id}")
                return None
            
            # Parse breakdown
            breakdown = None
            if signal.breakdown:
                try:
                    breakdown = json.loads(signal.breakdown)
                except (json.JSONDecodeError, TypeError):
                    breakdown = None
            
            # Parse event risks
            event_risks = None
            if signal.event_risks:
                try:
                    event_risks = json.loads(signal.event_risks)
                except (json.JSONDecodeError, TypeError):
                    event_risks = None
            
            # Parse exit rules
            exit_rules = []
            if signal.exit_rules:
                try:
                    exit_rules = json.loads(signal.exit_rules)
                except (json.JSONDecodeError, TypeError):
                    exit_rules = []
            
            # Get related contracts
            contracts = []
            if signal.option_contract_id:
                contract = db.query(OptionContract).filter(
                    OptionContract.id == signal.option_contract_id
                ).first()
                if contract:
                    contracts.append(ContractDetail(
                        contract_id=contract.id,
                        symbol=contract.symbol,
                        expiration=contract.expiration,
                        strike=contract.strike,
                        contract_type=contract.contract_type,
                        bid=contract.bid,
                        ask=contract.ask,
                        volume=contract.volume,
                        open_interest=contract.open_interest,
                        implied_volatility=contract.implied_volatility,
                        delta=contract.delta,
                        gamma=contract.gamma,
                        theta=contract.theta,
                        vega=contract.vega,
                        underlying_price=contract.underlying_price,
                        days_to_expiration=contract.days_to_expiration,
                        liquidity_score=contract.liquidity_score,
                    ))
            
            # Get related news
            related_news = []
            news_articles = db.query(NewsArticle).filter(
                NewsArticle.symbol == signal.symbol,
            ).order_by(NewsArticle.published_at.desc()).limit(5).all()
            
            for article in news_articles:
                related_news.append(NewsItem(
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
                ))
            
            # Get related trades (backtest/paper history)
            related_trades = []
            trades = db.query(Trade).filter(
                Trade.signal_id == signal_id,
            ).all()
            
            for trade in trades:
                related_trades.append(TradeItem(
                    trade_id=trade.id,
                    symbol=signal.symbol,
                    strategy_type=signal.strategy_type,
                    entry_price=trade.entry_price,
                    current_price=trade.exit_price,  # Use exit price if available
                    quantity=trade.quantity,
                    entry_date=trade.opened_at,
                    current_pl=trade.realized_pnl,
                    current_pl_pct=(trade.realized_pnl / (trade.entry_price * trade.quantity) * 100) if trade.entry_price > 0 else None,
                    status=trade.status,
                ))
            
            # Calculate Greeks summary
            greeks_summary = None
            if contracts:
                greeks_summary = {
                    "delta": sum(c.delta or 0.0 for c in contracts) / len(contracts) if contracts else 0.0,
                    "gamma": sum(c.gamma or 0.0 for c in contracts) / len(contracts) if contracts else 0.0,
                    "theta": sum(c.theta or 0.0 for c in contracts) / len(contracts) if contracts else 0.0,
                    "vega": sum(c.vega or 0.0 for c in contracts) / len(contracts) if contracts else 0.0,
                }
            
            return SignalDetail(
                signal_id=signal.id,
                symbol=signal.symbol,
                strategy_type=signal.strategy_type,
                risk_level=signal.risk_level,
                score=signal.score,
                expected_profit=signal.expected_profit,
                max_loss=signal.max_loss,
                probability_estimate=signal.probability_estimate,
                reason=signal.reason,
                status=signal.status,
                created_at=signal.created_at,
                updated_at=signal.updated_at,
                breakdown=breakdown,
                contracts=contracts,
                event_risks=event_risks,
                exit_rules=exit_rules,
                related_news=related_news,
                related_trades=related_trades,
                greeks_summary=greeks_summary,
            )
        except Exception as e:
            logger.error(f"Error getting signal detail for signal {signal_id}: {e}", exc_info=True)
            return None

    def approve_signal(
        self,
        user_id: int,
        signal_id: int,
        db: Session,
    ) -> Dict[str, Any]:
        """Approve a signal for trading.

        Args:
            user_id: User ID
            signal_id: Signal ID
            db: Database session

        Returns:
            Dictionary with status and message
        """
        try:
            signal = db.query(Signal).filter(
                Signal.id == signal_id,
                Signal.user_id == user_id,
            ).first()
            
            if not signal:
                return {"status": "error", "message": "Signal not found"}
            
            if signal.status != "pending":
                return {"status": "error", "message": f"Cannot approve signal with status '{signal.status}'"}
            
            signal.status = "approved"
            signal.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Signal {signal_id} approved by user {user_id}")
            return {"status": "success", "message": "Signal approved", "signal_id": signal_id}
        except Exception as e:
            logger.error(f"Error approving signal {signal_id}: {e}", exc_info=True)
            db.rollback()
            return {"status": "error", "message": f"Failed to approve signal: {str(e)}"}

    def reject_signal(
        self,
        user_id: int,
        signal_id: int,
        db: Session,
    ) -> Dict[str, Any]:
        """Reject a signal.

        Args:
            user_id: User ID
            signal_id: Signal ID
            db: Database session

        Returns:
            Dictionary with status and message
        """
        try:
            signal = db.query(Signal).filter(
                Signal.id == signal_id,
                Signal.user_id == user_id,
            ).first()
            
            if not signal:
                return {"status": "error", "message": "Signal not found"}
            
            if signal.status != "pending":
                return {"status": "error", "message": f"Cannot reject signal with status '{signal.status}'"}
            
            signal.status = "rejected"
            signal.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Signal {signal_id} rejected by user {user_id}")
            return {"status": "success", "message": "Signal rejected", "signal_id": signal_id}
        except Exception as e:
            logger.error(f"Error rejecting signal {signal_id}: {e}", exc_info=True)
            db.rollback()
            return {"status": "error", "message": f"Failed to reject signal: {str(e)}"}

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
            portfolio_summary = self.get_portfolio_summary(user_id, db)
            watchlist = self.get_watchlist(user_id, db, watchlist_id)
            top_opportunities = self.get_top_opportunities(user_id, db)
            
            # Get open trades
            open_trades = []
            trades = db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.status == "open",
            ).all()
            
            for trade in trades:
                open_trades.append(TradeItem(
                    trade_id=trade.id,
                    symbol=trade.signal.symbol if trade.signal else "UNKNOWN",
                    strategy_type=trade.signal.strategy_type if trade.signal else "UNKNOWN",
                    entry_price=trade.entry_price,
                    current_price=None,  # Would be fetched from data provider
                    quantity=trade.quantity,
                    entry_date=trade.opened_at,
                    current_pl=None,
                    current_pl_pct=None,
                    status=trade.status,
                ))
            
            # Get recent news
            recent_news = []
            news_articles = db.query(NewsArticle).order_by(
                NewsArticle.published_at.desc()
            ).limit(10).all()
            
            for article in news_articles:
                recent_news.append(NewsItem(
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
                ))
            
            # Get user risk settings
            user = db.query(User).filter(User.id == user_id).first()
            risk_settings = RiskSettings(
                risk_level=user.risk_level if user else "medium",
                paper_trading_enabled=user.paper_trading_enabled if user else True,
                live_trading_enabled=user.live_trading_enabled if user else False,
                live_trading_approved=user.live_trading_approved if user else False,
            )
            
            return DashboardData(
                portfolio_summary=portfolio_summary,
                watchlist=watchlist,
                top_opportunities=top_opportunities,
                open_trades=open_trades,
                recent_news=recent_news,
                risk_settings=risk_settings,
                timestamp=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"Error getting dashboard data for user {user_id}: {e}", exc_info=True)
            raise
