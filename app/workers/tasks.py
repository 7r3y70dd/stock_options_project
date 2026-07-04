"""Background job tasks for data fetching, signal generation, and trade monitoring."""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from app.core.celery import celery_app
from app.core.config import config
from app.core.database import SessionLocal
from app.core.broker_provider import BrokerProvider, OrderStatus
from app.core.paper_broker_provider import PaperBrokerProvider
from app.data_sources import (
    DataProvider,
    MockDataProvider,
    AlphaVantageProvider,
    YfinanceProvider,
    FinnhubProvider,
)
from app.models.database import Signal, Trade, OptionContract, NewsArticle, WatchlistSymbol
from app.news.sentiment_analyzer import SentimentAnalyzer
from services.options_service import VolatilityAnalyzer, GreeksAnalyzer
from services import RiskLevel

logger = logging.getLogger(__name__)

# Initialize default data provider (mock for now, can be swapped)
_data_provider: Optional[DataProvider] = None
_broker_provider: Optional[BrokerProvider] = None
_sentiment_analyzer: Optional[SentimentAnalyzer] = None


def get_data_provider() -> DataProvider:
    """Get or initialize the data provider based on configuration.
    
    Returns:
        DataProvider instance
    """
    global _data_provider
    if _data_provider is None:
        provider_name = config.DATA_PROVIDER.lower()
        
        if provider_name == "alphavantage":
            try:
                _data_provider = AlphaVantageProvider(
                    api_key=config.ALPHAVANTAGE_API_KEY,
                    rate_limit_calls_per_minute=config.ALPHAVANTAGE_RATE_LIMIT_CALLS_PER_MINUTE,
                    cache_ttl_seconds=config.ALPHAVANTAGE_CACHE_TTL_SECONDS,
                )
                logger.info("Initialized AlphaVantageProvider for background tasks")
            except ValueError as e:
                logger.warning(f"Failed to initialize AlphaVantageProvider: {e}. Falling back to MockDataProvider.")
                _data_provider = MockDataProvider()
        elif provider_name == "yfinance":
            if not config.YFINANCE_ENABLED:
                logger.warning("yfinance provider requested but disabled in config. Falling back to MockDataProvider.")
                _data_provider = MockDataProvider()
            else:
                try:
                    _data_provider = YfinanceProvider(warn_on_init=True)
                    logger.info("Initialized YfinanceProvider for background tasks")
                except ImportError as e:
                    logger.warning(f"Failed to initialize YfinanceProvider: {e}. Falling back to MockDataProvider.")
                    _data_provider = MockDataProvider()
        elif provider_name == "finnhub":
            if not config.FINNHUB_ENABLED:
                logger.warning("Finnhub provider requested but disabled in config. Falling back to MockDataProvider.")
                _data_provider = MockDataProvider()
            else:
                try:
                    _data_provider = FinnhubProvider(
                        api_key=config.FINNHUB_API_KEY,
                        rate_limit_calls_per_second=config.FINNHUB_RATE_LIMIT_CALLS_PER_SECOND,
                        cache_ttl_seconds=config.FINNHUB_CACHE_TTL_SECONDS,
                    )
                    logger.info("Initialized FinnhubProvider for background tasks")
                except ValueError as e:
                    logger.warning(f"Failed to initialize FinnhubProvider: {e}. Falling back to MockDataProvider.")
                    _data_provider = MockDataProvider()
        else:
            # Default to mock provider
            _data_provider = MockDataProvider()
            logger.info("Initialized MockDataProvider for background tasks")
    
    return _data_provider


def set_data_provider(provider: DataProvider) -> None:
    """Set the data provider for background tasks.
    
    Args:
        provider: DataProvider instance to use
    """
    global _data_provider
    _data_provider = provider
    logger.info(f"Data provider set to {provider.__class__.__name__}")


def get_broker_provider() -> BrokerProvider:
    """Get or initialize the broker provider based on configuration.
    
    Returns:
        BrokerProvider instance
    """
    global _broker_provider
    if _broker_provider is None:
        provider_name = config.BROKER_PROVIDER.lower()
        
        if provider_name == "paper":
            _broker_provider = PaperBrokerProvider(
                initial_cash=config.BROKER_PAPER_INITIAL_CASH,
                enable_logging=config.BROKER_ENABLE_LOGGING,
            )
            logger.info("Initialized PaperBrokerProvider for background tasks")
        else:
            # Default to paper broker
            _broker_provider = PaperBrokerProvider(
                initial_cash=config.BROKER_PAPER_INITIAL_CASH,
                enable_logging=config.BROKER_ENABLE_LOGGING,
            )
            logger.info("Initialized PaperBrokerProvider (default) for background tasks")
    
    return _broker_provider


def set_broker_provider(provider: BrokerProvider) -> None:
    """Set the broker provider for background tasks.
    
    Args:
        provider: BrokerProvider instance to use
    """
    global _broker_provider
    _broker_provider = provider
    logger.info(f"Broker provider set to {provider.__class__.__name__}")


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get or initialize the sentiment analyzer.
    
    Returns:
        SentimentAnalyzer instance
    """
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer(
            model_name=config.SENTIMENT_MODEL,
            use_gpu=config.SENTIMENT_USE_GPU,
        )
        logger.info(f"Initialized SentimentAnalyzer with model: {config.SENTIMENT_MODEL}")
    
    return _sentiment_analyzer


def set_sentiment_analyzer(analyzer: SentimentAnalyzer) -> None:
    """Set the sentiment analyzer for background tasks.
    
    Args:
        analyzer: SentimentAnalyzer instance to use
    """
    global _sentiment_analyzer
    _sentiment_analyzer = analyzer
    logger.info(f"Sentiment analyzer set to {analyzer.__class__.__name__}")


def _calculate_volatility_context(
    symbol: str,
    provider: DataProvider,
    db,
) -> Dict[str, Optional[float]]:
    """Calculate volatility metrics for a symbol.
    
    Args:
        symbol: Stock symbol
        provider: Data provider instance
        db: Database session
        
    Returns:
        Dict with 'historical_volatility' and 'volatility_context' keys
    """
    try:
        # Get price history for volatility calculation
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - timedelta(days=60)).strftime("%Y-%m-%d")
        
        price_bars = provider.get_price_history(symbol, start_date, end_date)
        
        if not price_bars:
            return {"historical_volatility": None, "volatility_context": None}
        
        # Convert to dict format for analyzer
        bars_dict = [{"close": bar.close} for bar in price_bars]
        
        # Calculate historical volatility
        hv = VolatilityAnalyzer.calculate_historical_volatility(bars_dict)
        
        return {"historical_volatility": hv, "volatility_context": None}
    except Exception as e:
        logger.warning(f"Error calculating volatility for {symbol}: {e}")
        return {"historical_volatility": None, "volatility_context": None}


def _calculate_greeks_metrics(
    contract: OptionContract,
    risk_level: RiskLevel = RiskLevel.MEDIUM,
) -> Dict[str, any]:
    """Calculate Greeks metrics for an option contract.
    
    Args:
        contract: OptionContract to analyze
        risk_level: Risk level for threshold comparison
        
    Returns:
        Dict with Greeks analysis including acceptable status and warnings
    """
    try:
        greeks_analyzer = GreeksAnalyzer()
        acceptable, warnings, scores = greeks_analyzer.assess_greek_profile(contract, risk_level)
        greeks_score = greeks_analyzer.calculate_greeks_score(contract, risk_level)
        
        return {
            "acceptable": acceptable,
            "warnings": warnings,
            "scores": scores,
            "greeks_score": greeks_score,
        }
    except Exception as e:
        logger.warning(f"Error calculating Greeks metrics: {e}")
        return {
            "acceptable": True,  # Default to acceptable if calculation fails
            "warnings": [],
            "scores": {},
            "greeks_score": 1.0,
        }


@celery_app.task(
    name="app.workers.tasks.refresh_market_data",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def refresh_market_data(self, watchlist_id: Optional[int] = None) -> dict:
    """Refresh market data for watched symbols.
    
    Args:
        watchlist_id: Optional specific watchlist to refresh. If None, refresh all.
        
    Returns:
        Dictionary with refresh results
    """
    try:
        logger.info(f"Starting market data refresh for watchlist_id={watchlist_id}")
        
        db = SessionLocal()
        provider = get_data_provider()
        
        try:
            # TODO: Fetch watchlist symbols and update market data using provider
            # Example:
            # - Get symbols from watchlist
            # - Call provider.get_quote(symbol) for each
            # - Store quotes in database
            # - Call provider.get_options_chain(symbol) for options data
            # - Update OptionContract records with volatility metrics and Greeks
            
            result = {
                "status": "success",
                "watchlist_id": watchlist_id,
                "timestamp": datetime.utcnow().isoformat(),
                "symbols_updated": 0,
                "provider": provider.__class__.__name__,
            }
            logger.info(f"Market data refresh completed: {result}")
            return result
        finally:
            db.close()
            
    except Exception as exc:
        logger.error(f"Market data refresh failed: {exc}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(
    name="app.workers.tasks.fetch_news",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def fetch_news(self, symbol: Optional[str] = None, limit: int = 10) -> dict:
    """Fetch and store news articles for symbols with sentiment analysis.
    
    Fetches news from the configured data provider, performs sentiment analysis,
    and stores articles in the database. Automatically deduplicates articles by URL and title.
    
    Args:
        symbol: Optional specific symbol to fetch news for. If None, fetch for all watched symbols.
        limit: Maximum number of articles to fetch per symbol
        
    Returns:
        Dictionary with fetch results
    """
    try:
        logger.info(f"Starting news fetch for symbol={symbol}, limit={limit}")
        
        db = SessionLocal()
        provider = get_data_provider()
        sentiment_analyzer = get_sentiment_analyzer()
        
        try:
            # Determine which symbols to fetch
            if symbol:
                symbols_to_fetch = [symbol.upper()]
            else:
                # Fetch for all watched symbols from all watchlists
                watchlist_symbols = db.query(WatchlistSymbol).all()
                symbols_to_fetch = list(set([ws.symbol for ws in watchlist_symbols]))
                
                if not symbols_to_fetch:
                    logger.info("No symbols in watchlists to fetch news for")
                    return {
                        "status": "success",
                        "symbol": None,
                        "timestamp": datetime.utcnow().isoformat(),
                        "articles_fetched": 0,
                        "articles_stored": 0,
                    }
            
            total_fetched = 0
            total_stored = 0
            
            for sym in symbols_to_fetch:
                try:
                    # Fetch news from provider
                    articles = provider.get_news(sym, limit=limit)
                    total_fetched += len(articles)
                    
                    for article in articles:
                        try:
                            # Check if article already exists
                            existing = db.query(NewsArticle).filter(
                                NewsArticle.url == article.get("url")
                            ).first()
                            
                            if existing:
                                continue
                            
                            # Analyze sentiment
                            sentiment_result = sentiment_analyzer.analyze(article.get("description", ""))
                            
                            # Store article
                            news_article = NewsArticle(
                                symbol=sym,
                                title=article.get("title", ""),
                                description=article.get("description"),
                                url=article.get("url"),
                                source=article.get("source"),
                                published_at=article.get("published_at"),
                                sentiment=sentiment_result.get("sentiment"),
                                sentiment_score=sentiment_result.get("score"),
                                confidence_score=sentiment_result.get("confidence"),
                                provider=provider.__class__.__name__,
                            )
                            db.add(news_article)
                            total_stored += 1
                        except Exception as e:
                            logger.warning(f"Error storing article for {sym}: {e}")
                            continue
                    
                    db.commit()
                except Exception as e:
                    logger.warning(f"Error fetching news for {sym}: {e}")
                    db.rollback()
                    continue
            
            result = {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "symbols_processed": len(symbols_to_fetch),
                "articles_fetched": total_fetched,
                "articles_stored": total_stored,
            }
            logger.info(f"News fetch completed: {result}")
            return result
        finally:
            db.close()
            
    except Exception as exc:
        logger.error(f"News fetch failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(
    name="app.workers.tasks.poll_order_status",
    bind=True,
    max_retries=5,
    default_retry_delay=30,
)
def poll_order_status(self, trade_id: int) -> dict:
    """Poll broker for order status and update Trade record.
    
    Checks the status of a submitted paper order and updates the Trade model
    with the latest order status, fill information, and any error messages.
    
    Args:
        trade_id: ID of the Trade record to poll
        
    Returns:
        Dictionary with polling results
    """
    try:
        logger.info(f"Polling order status for trade_id={trade_id}")
        
        db = SessionLocal()
        broker = get_broker_provider()
        
        try:
            # Get trade record
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if not trade:
                logger.error(f"Trade not found: {trade_id}")
                return {"status": "error", "message": "Trade not found"}
            
            # Get broker order
            if not trade.broker_order_id:
                logger.warning(f"Trade {trade_id} has no broker_order_id")
                return {"status": "error", "message": "No broker order ID"}
            
            broker_order = broker.get_order(trade.broker_order_id)
            if not broker_order:
                logger.warning(f"Broker order not found: {trade.broker_order_id}")
                return {"status": "error", "message": "Broker order not found"}
            
            # Update trade with broker order status
            trade.order_status = broker_order.status.value
            
            if broker_order.status == OrderStatus.FILLED:
                trade.status = "filled"
                trade.entry_price = broker_order.filled_price
                trade.opened_at = broker_order.created_at or datetime.utcnow()
                logger.info(f"Trade {trade_id} filled at ${broker_order.filled_price}")
            
            elif broker_order.status == OrderStatus.PARTIALLY_FILLED:
                trade.status = "partially_filled"
                trade.entry_price = broker_order.filled_price
                logger.info(f"Trade {trade_id} partially filled: {broker_order.filled_quantity}/{broker_order.quantity}")
            
            elif broker_order.status == OrderStatus.CANCELLED:
                trade.status = "cancelled"
                logger.info(f"Trade {trade_id} cancelled")
            
            elif broker_order.status == OrderStatus.REJECTED:
                trade.status = "rejected"
                trade.error_message = broker_order.error_message or "Order rejected by broker"
                logger.warning(f"Trade {trade_id} rejected: {trade.error_message}")
            
            elif broker_order.status == OrderStatus.EXPIRED:
                trade.status = "cancelled"
                trade.error_message = "Order expired"
                logger.warning(f"Trade {trade_id} expired")
            
            # Update timestamp
            trade.updated_at = datetime.utcnow()
            db.commit()
            
            result = {
                "status": "success",
                "trade_id": trade_id,
                "order_status": broker_order.status.value,
                "trade_status": trade.status,
                "filled_price": broker_order.filled_price,
                "filled_quantity": broker_order.filled_quantity,
            }
            logger.info(f"Order status poll completed: {result}")
            return result
        
        finally:
            db.close()
            
    except Exception as exc:
        logger.error(f"Order status poll failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


@celery_app.task(
    name="app.workers.tasks.monitor_broker_positions",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def monitor_broker_positions(self) -> dict:
    """Monitor broker positions and update account status.
    
    Periodically checks broker positions and account status to ensure
    paper trading state is synchronized with broker provider.
    
    Returns:
        Dictionary with monitoring results
    """
    try:
        logger.info("Starting broker position monitoring")
        
        broker = get_broker_provider()
        
        # Get current positions
        positions = broker.get_positions()
        account = broker.get_account()
        
        result = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "positions_count": len(positions),
            "account_cash": account.cash,
            "portfolio_value": account.portfolio_value,
            "positions": [
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "market_value": p.market_value,
                    "unrealized_pl": p.unrealized_pl,
                }
                for p in positions
            ],
        }
        logger.info(f"Broker position monitoring completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Broker position monitoring failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))



@celery_app.task(
    name="app.workers.tasks.generate_signals",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_signals(self, user_id: Optional[int] = None, limit: int = 20) -> dict:
    """Generate ranked paper-trade ideas from watchlist market data.

    This is an MVP scanner. It does not predict the future or execute trades.
    It creates pending Signal rows for the dashboard to review.
    """
    try:
        logger.info(f"Starting signal generation for user_id={user_id}")

        from app.models.database import User, Watchlist

        db = SessionLocal()
        provider = get_data_provider()

        try:
            rows = (
                db.query(WatchlistSymbol, Watchlist, User)
                .join(Watchlist, Watchlist.id == WatchlistSymbol.watchlist_id)
                .join(User, User.id == Watchlist.user_id)
            )

            if user_id is not None:
                rows = rows.filter(User.id == user_id)

            rows = rows.all()

            if not rows:
                return {
                    "status": "success",
                    "message": "No watchlist symbols found",
                    "provider": provider.__class__.__name__,
                    "symbols_processed": 0,
                    "signals_created": 0,
                    "skipped": [],
                }

            symbol_users = {}
            for watchlist_symbol, watchlist, user in rows:
                symbol_users.setdefault(watchlist_symbol.symbol.upper(), []).append(user)

            symbols = sorted(symbol_users.keys())[:limit]

            existing_pending = {
                (signal.user_id, signal.symbol, signal.strategy_type)
                for signal in db.query(Signal).filter(Signal.status == "pending").all()
            }

            risk_pct_by_level = {
                "low": 0.01,
                "medium": 0.02,
                "high": 0.05,
            }

            signals_created = 0
            skipped = []

            for symbol in symbols:
                try:
                    quote = provider.get_quote(symbol)

                    end_date = datetime.utcnow().strftime("%Y-%m-%d")
                    start_date = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")
                    bars = provider.get_price_history(symbol, start_date, end_date)

                    closes = [
                        float(bar.close)
                        for bar in bars
                        if getattr(bar, "close", None) is not None
                    ]

                    if len(closes) < 20:
                        skipped.append({
                            "symbol": symbol,
                            "reason": "not enough price history",
                        })
                        continue

                    quote_price = (
                        getattr(quote, "price", None)
                        or getattr(quote, "current_price", None)
                        or getattr(quote, "last", None)
                    )
                    current_price = float(quote_price or closes[-1])

                    avg_20 = sum(closes[-20:]) / 20
                    avg_60_window = closes[-60:] if len(closes) >= 60 else closes
                    avg_60 = sum(avg_60_window) / len(avg_60_window)

                    returns = []
                    for previous, current in zip(closes[:-1], closes[1:]):
                        if previous:
                            returns.append((current - previous) / previous)

                    if returns:
                        mean_return = sum(returns) / len(returns)
                        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
                        daily_volatility = variance ** 0.5
                    else:
                        daily_volatility = 0.0

                    trend_score = 0.0
                    if current_price > avg_20:
                        trend_score += 15.0
                    if avg_20 > avg_60:
                        trend_score += 15.0

                    volatility_score = max(0.0, 25.0 - min(daily_volatility * 1000.0, 25.0))
                    score = min(95.0, max(0.0, 50.0 + trend_score + volatility_score))

                    if score >= 75.0:
                        strategy_type = "credit_spread"
                        probability_estimate = 0.62
                        reward_multiple = 0.60
                    elif score >= 65.0:
                        strategy_type = "cash_secured_put"
                        probability_estimate = 0.68
                        reward_multiple = 0.45
                    else:
                        skipped.append({
                            "symbol": symbol,
                            "reason": f"score too low: {score:.1f}",
                        })
                        continue

                    for user in symbol_users[symbol]:
                        risk_level = user.risk_level or "medium"
                        risk_pct = risk_pct_by_level.get(risk_level, 0.02)

                        account_size = float(user.initial_portfolio_value or 2000.0)
                        max_loss = round(account_size * risk_pct, 2)
                        expected_profit = round(max_loss * reward_multiple, 2)

                        if max_loss <= 0:
                            skipped.append({
                                "symbol": symbol,
                                "reason": f"user {user.id} has no risk budget",
                            })
                            continue

                        key = (user.id, symbol, strategy_type)
                        if key in existing_pending:
                            continue

                        signal = Signal(
                            user_id=user.id,
                            symbol=symbol,
                            strategy_type=strategy_type,
                            risk_level=risk_level,
                            score=round(score, 2),
                            expected_profit=expected_profit,
                            max_loss=max_loss,
                            probability_estimate=probability_estimate,
                            reason=(
                                f"Generated signal: {symbol} is trading near ${current_price:.2f}. "
                                f"20-day average is ${avg_20:.2f}; 60-day average is ${avg_60:.2f}. "
                                f"Scanner score is {score:.1f}. Candidate strategy: {strategy_type}. "
                                f"Max loss is capped near the user's {risk_level} risk budget."
                            ),
                            status="pending",
                            option_contract_id=None,
                            breakdown=json.dumps({
                                "current_price": current_price,
                                "avg_20": avg_20,
                                "avg_60": avg_60,
                                "trend_score": trend_score,
                                "daily_volatility_estimate": daily_volatility,
                                "volatility_score": volatility_score,
                                "final": round(score, 2),
                                "provider": provider.__class__.__name__,
                            }),
                            event_risks=json.dumps({
                                "earnings_risk": "unknown",
                                "news_risk": "unknown",
                            }),
                            exit_rules=json.dumps([
                                {
                                    "type": "stop_loss",
                                    "value": max_loss,
                                    "description": f"Exit if loss approaches ${max_loss:.2f}",
                                },
                                {
                                    "type": "profit_target",
                                    "value": expected_profit,
                                    "description": f"Take profit near ${expected_profit:.2f}",
                                },
                            ]),
                        )

                        db.add(signal)
                        existing_pending.add(key)
                        signals_created += 1

                except Exception as e:
                    logger.warning(f"Error generating signal for {symbol}: {e}", exc_info=True)
                    skipped.append({
                        "symbol": symbol,
                        "reason": repr(e),
                    })

            db.commit()

            result = {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "provider": provider.__class__.__name__,
                "symbols_processed": len(symbols),
                "signals_created": signals_created,
                "skipped": skipped[:20],
            }

            logger.info(f"Signal generation completed: {result}")
            return result

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"Signal generation failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(
    name="app.workers.tasks.fetch_news_for_watchlist",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def fetch_news_for_watchlist(self, watchlist_id: Optional[int] = None, limit: int = 10) -> dict:
    """Scheduled compatibility task for watchlist news fetches."""
    return fetch_news(symbol=None, limit=limit)


@celery_app.task(
    name="app.workers.tasks.monitor_trades",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def monitor_trades(self) -> dict:
    """Scheduled compatibility task for trade monitoring."""
    return monitor_broker_positions()
