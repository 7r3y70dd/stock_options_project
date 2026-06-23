"""Background job tasks for data fetching, signal generation, and trade monitoring."""

import logging
from datetime import datetime
from typing import Optional, List, Dict

from app.core.celery import celery_app
from app.core.config import config
from app.core.database import SessionLocal
from app.core.broker_provider import BrokerProvider
from app.core.paper_broker_provider import PaperBrokerProvider
from app.data_sources import (
    DataProvider,
    MockDataProvider,
    AlphaVantageProvider,
    YfinanceProvider,
    FinnhubProvider,
)
from app.models.database import Signal, Trade, OptionContract, NewsArticle
from services.options_service import VolatilityAnalyzer

logger = logging.getLogger(__name__)

# Initialize default data provider (mock for now, can be swapped)
_data_provider: Optional[DataProvider] = None
_broker_provider: Optional[BrokerProvider] = None


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
        from datetime import timedelta
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
            # - Update OptionContract records with volatility metrics
            
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
    """Fetch and store news articles for symbols.
    
    Fetches news from the configured data provider and stores articles in the database.
    Automatically deduplicates articles by URL.
    
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
        
        try:
            symbols_to_fetch = [symbol] if symbol else ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
            articles_fetched = 0
            articles_stored = 0
            articles_duplicated = 0
            
            for sym in symbols_to_fetch:
                try:
                    # Fetch news from provider
                    articles = provider.get_news(sym, limit=limit)
                    articles_fetched += len(articles)
                    
                    # Store articles in database with deduplication
                    for article in articles:
                        try:
                            # Check if article already exists by URL
                            if article.url:
                                existing = db.query(NewsArticle).filter(
                                    NewsArticle.url == article.url
                                ).first()
                                
                                if existing:
                                    logger.debug(f"Skipping duplicate article: {article.url}")
                                    articles_duplicated += 1
                                    continue
                            
                            # Store new article
                            db_article = NewsArticle(
                                symbol=article.symbol,
                                title=article.title,
                                description=article.description,
                                url=article.url,
                                source=article.source,
                                published_at=article.published_at,
                                sentiment=article.sentiment,
                                provider=provider.__class__.__name__,
                            )
                            db.add(db_article)
                            articles_stored += 1
                        except Exception as e:
                            logger.warning(f"Error storing article for {sym}: {e}")
                            continue
                    
                    db.commit()
                    
                except Exception as e:
                    logger.warning(f"Error fetching news for {sym}: {e}")
                    continue
            
            result = {
                "status": "success",
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat(),
                "articles_fetched": articles_fetched,
                "articles_stored": articles_stored,
                "articles_duplicated": articles_duplicated,
                "provider": provider.__class__.__name__,
            }
            logger.info(f"News fetch completed: {result}")
            return result
        finally:
            db.close()
            
    except Exception as exc:
        logger.error(f"News fetch failed: {exc}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(
    name="app.workers.tasks.generate_signals",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_signals(self, user_id: Optional[int] = None) -> dict:
    """Generate trading signals based on current market data.
    
    Args:
        user_id: Optional specific user to generate signals for. If None, generate for all.
        
    Returns:
        Dictionary with signal generation results
    """
    try:
        logger.info(f"Starting signal generation for user_id={user_id}")
        
        db = SessionLocal()
        provider = get_data_provider()
        
        try:
            # TODO: Implement actual signal generation logic
            # Example:
            # - Get user watchlists and symbols
            # - Call provider.get_price_history() for technical analysis
            # - Call provider.get_news() for sentiment analysis
            # - Calculate volatility metrics using VolatilityAnalyzer
            # - Generate signals based on strategies with volatility context
            # - Store Signal records in database with IV/HV context in reason field
            
            result = {
                "status": "success",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "signals_generated": 0,
                "provider": provider.__class__.__name__,
            }
            logger.info(f"Signal generation completed: {result}")
            return result
        finally:
            db.close()
            
    except Exception as exc:
        logger.error(f"Signal generation failed: {exc}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(
    name="app.workers.tasks.monitor_trades",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def monitor_trades(self, user_id: Optional[int] = None) -> dict:
    """Monitor open trades and update their status.
    
    Args:
        user_id: Optional specific user to monitor. If None, monitor all.
        
    Returns:
        Dictionary with monitoring results
    """
    try:
        logger.info(f"Starting trade monitoring for user_id={user_id}")
        
        db = SessionLocal()
        provider = get_data_provider()
        
        try:
            # TODO: Implement trade monitoring logic
            # Example:
            # - Get open trades for user
            # - Get current prices using provider
            # - Update unrealized P/L
            # - Check stop-loss and take-profit levels
            # - Close trades if necessary
            
            result = {
                "status": "success",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "trades_monitored": 0,
                "trades_closed": 0,
                "provider": provider.__class__.__name__,
            }
            logger.info(f"Trade monitoring completed: {result}")
            return result
        finally:
            db.close()
            
    except Exception as exc:
        logger.error(f"Trade monitoring failed: {exc}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
