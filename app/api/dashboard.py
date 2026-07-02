"""Dashboard API endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.frontend.dashboard import Dashboard, DashboardData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Initialize dashboard service
_dashboard: Optional[Dashboard] = None


def get_dashboard() -> Dashboard:
    """Get or initialize dashboard service.
    
    Returns:
        Dashboard instance
    """
    global _dashboard
    if _dashboard is None:
        _dashboard = Dashboard()
    return _dashboard


@router.get("/", response_model=dict)
async def get_dashboard_data(
    user_id: int = Query(..., description="User ID"),
    watchlist_id: Optional[int] = Query(None, description="Optional watchlist ID"),
    db: Session = Depends(get_db),
    dashboard: Dashboard = Depends(get_dashboard),
) -> dict:
    """Get complete dashboard data for user.
    
    Args:
        user_id: User ID
        watchlist_id: Optional specific watchlist ID
        db: Database session
        dashboard: Dashboard service
        
    Returns:
        Dashboard data with all sections
        
    Raises:
        HTTPException: If user not found or error occurs
    """
    try:
        data = dashboard.get_dashboard_data(user_id, db, watchlist_id)
        
        # Convert dataclasses to dicts for JSON response
        return {
            "portfolio_summary": {
                "total_value": data.portfolio_summary.total_value,
                "cash": data.portfolio_summary.cash,
                "positions_value": data.portfolio_summary.positions_value,
                "open_pl": data.portfolio_summary.open_pl,
                "open_pl_pct": data.portfolio_summary.open_pl_pct,
                "num_open_trades": data.portfolio_summary.num_open_trades,
                "num_open_signals": data.portfolio_summary.num_open_signals,
            },
            "watchlist": [
                {
                    "symbol": item.symbol,
                    "current_price": item.current_price,
                    "added_at": item.added_at.isoformat(),
                    "last_updated": item.last_updated.isoformat() if item.last_updated else None,
                    "data_freshness_seconds": item.data_freshness_seconds,
                }
                for item in data.watchlist
            ],
            "top_opportunities": [
                {
                    "signal_id": item.signal_id,
                    "symbol": item.symbol,
                    "strategy_type": item.strategy_type,
                    "score": item.score,
                    "expected_profit": item.expected_profit,
                    "max_loss": item.max_loss,
                    "probability_estimate": item.probability_estimate,
                    "reason": item.reason,
                    "status": item.status,
                    "created_at": item.created_at.isoformat(),
                    "breakdown": item.breakdown,
                }
                for item in data.top_opportunities
            ],
            "open_trades": [
                {
                    "trade_id": item.trade_id,
                    "symbol": item.symbol,
                    "strategy_type": item.strategy_type,
                    "entry_price": item.entry_price,
                    "current_price": item.current_price,
                    "quantity": item.quantity,
                    "entry_date": item.entry_date.isoformat(),
                    "current_pl": item.current_pl,
                    "current_pl_pct": item.current_pl_pct,
                    "status": item.status,
                }
                for item in data.open_trades
            ],
            "recent_news": [
                {
                    "article_id": item.article_id,
                    "symbol": item.symbol,
                    "title": item.title,
                    "description": item.description,
                    "url": item.url,
                    "source": item.source,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                    "sentiment": item.sentiment,
                    "sentiment_score": item.sentiment_score,
                    "event_type": item.event_type,
                }
                for item in data.recent_news
            ],
            "risk_settings": {
                "risk_level": data.risk_settings.risk_level,
                "paper_trading_enabled": data.risk_settings.paper_trading_enabled,
                "live_trading_enabled": data.risk_settings.live_trading_enabled,
                "live_trading_approved": data.risk_settings.live_trading_approved,
            },
            "timestamp": data.timestamp.isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting dashboard data for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")


@router.get("/portfolio", response_model=dict)
async def get_portfolio_summary(
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
    dashboard: Dashboard = Depends(get_dashboard),
) -> dict:
    """Get portfolio summary for user.
    
    Args:
        user_id: User ID
        db: Database session
        dashboard: Dashboard service
        
    Returns:
        Portfolio summary data
    """
    try:
        summary = dashboard.get_portfolio_summary(user_id, db)
        return {
            "total_value": summary.total_value,
            "cash": summary.cash,
            "positions_value": summary.positions_value,
            "open_pl": summary.open_pl,
            "open_pl_pct": summary.open_pl_pct,
            "num_open_trades": summary.num_open_trades,
            "num_open_signals": summary.num_open_signals,
        }
    except Exception as e:
        logger.error(f"Error getting portfolio summary for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve portfolio summary")


@router.get("/watchlist", response_model=dict)
async def get_watchlist(
    user_id: int = Query(..., description="User ID"),
    watchlist_id: Optional[int] = Query(None, description="Optional watchlist ID"),
    db: Session = Depends(get_db),
    dashboard: Dashboard = Depends(get_dashboard),
) -> dict:
    """Get watchlist for user with current prices and data freshness.
    
    Args:
        user_id: User ID
        watchlist_id: Optional specific watchlist ID
        db: Database session
        dashboard: Dashboard service
        
    Returns:
        Watchlist with symbols and prices
    """
    try:
        watchlist = dashboard.get_watchlist(user_id, db, watchlist_id)
        return {
            "symbols": [
                {
                    "symbol": item.symbol,
                    "current_price": item.current_price,
                    "added_at": item.added_at.isoformat(),
                    "last_updated": item.last_updated.isoformat() if item.last_updated else None,
                    "data_freshness_seconds": item.data_freshness_seconds,
                }
                for item in watchlist
            ],
            "count": len(watchlist),
        }
    except Exception as e:
        logger.error(f"Error getting watchlist for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve watchlist")


@router.post("/watchlist/add", response_model=dict)
async def add_watchlist_symbol(
    user_id: int = Query(..., description="User ID"),
    symbol: str = Query(..., description="Stock symbol to add"),
    watchlist_id: Optional[int] = Query(None, description="Optional watchlist ID"),
    db: Session = Depends(get_db),
    dashboard: Dashboard = Depends(get_dashboard),
) -> dict:
    """Add a symbol to user's watchlist.
    
    Args:
        user_id: User ID
        symbol: Stock symbol to add
        watchlist_id: Optional specific watchlist ID
        db: Database session
        dashboard: Dashboard service
        
    Returns:
        Result of add operation
    """
    try:
        result = dashboard.add_symbol(user_id, symbol, db, watchlist_id)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding symbol {symbol} for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add symbol")


@router.post("/watchlist/remove", response_model=dict)
async def remove_watchlist_symbol(
    user_id: int = Query(..., description="User ID"),
    symbol: str = Query(..., description="Stock symbol to remove"),
    watchlist_id: Optional[int] = Query(None, description="Optional watchlist ID"),
    db: Session = Depends(get_db),
    dashboard: Dashboard = Depends(get_dashboard),
) -> dict:
    """Remove a symbol from user's watchlist.
    
    Args:
        user_id: User ID
        symbol: Stock symbol to remove
        watchlist_id: Optional specific watchlist ID
        db: Database session
        dashboard: Dashboard service
        
    Returns:
        Result of remove operation
    """
    try:
        result = dashboard.remove_symbol(user_id, symbol, db, watchlist_id)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing symbol {symbol} for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to remove symbol")


@router.post("/watchlist/validate", response_model=dict)
async def validate_symbol(
    symbol: str = Query(..., description="Stock symbol to validate"),
    dashboard: Dashboard = Depends(get_dashboard),
) -> dict:
    """Validate a stock symbol format.
    
    Args:
        symbol: Stock symbol to validate
        dashboard: Dashboard service
        
    Returns:
        Validation result
    """
    try:
        result = dashboard.validate_symbol(symbol)
        return result
    except Exception as e:
        logger.error(f"Error validating symbol {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to validate symbol")


@router.get("/opportunities", response_model=dict)
async def get_top_opportunities(
    user_id: int = Query(..., description="User ID"),
    limit: int = Query(10, description="Maximum number of opportunities"),
    db: Session = Depends(get_db),
    dashboard: Dashboard = Depends(get_dashboard),
) -> dict:
    """Get top ranked opportunities for user.
    
    Args:
        user_id: User ID
        limit: Maximum number of opportunities
        db: Database session
        dashboard: Dashboard service
        
    Returns:
        List of top opportunities
    """
    try:
        opportunities = dashboard.get_top_opportunities(user_id, db, limit)
        return {
            "opportunities": [
                {
                    "signal_id": item.signal_id,
                    "symbol": item.symbol,
                    "strategy_type": item.strategy_type,
                    "score": item.score,
                    "expected_profit": item.expected_profit,
                    "max_loss": item.max_loss,
                    "probability_estimate": item.probability_estimate,
                    "reason": item.reason,
                    "status": item.status,
                    "created_at": item.created_at.isoformat(),
                    "breakdown": item.breakdown,
                }
                for item in opportunities
            ],
            "count": len(opportunities),
        }
    except Exception as e:
        logger.error(f"Error getting opportunities for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve opportunities")


@router.get("/risk-settings", response_model=dict)
async def get_risk_settings(
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
    dashboard: Dashboard = Depends(get_dashboard),
) -> dict:
    """Get user's risk settings.
    
    Args:
        user_id: User ID
        db: Database session
        dashboard: Dashboard service
        
    Returns:
        Risk settings
    """
    try:
        settings = dashboard.get_risk_settings(user_id, db)
        return {
            "risk_level": settings.risk_level,
            "paper_trading_enabled": settings.paper_trading_enabled,
            "live_trading_enabled": settings.live_trading_enabled,
            "live_trading_approved": settings.live_trading_approved,
        }
    except Exception as e:
        logger.error(f"Error getting risk settings for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve risk settings")
