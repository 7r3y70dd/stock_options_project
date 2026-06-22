"""Database seed script for initial data population."""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.database import (
    User,
    Watchlist,
    WatchlistSymbol,
    OptionContract,
)

logger = logging.getLogger(__name__)


def seed_database() -> None:
    """Populate database with initial seed data."""
    db = SessionLocal()
    try:
        # Check if data already exists
        if db.query(User).first():
            logger.info("Database already seeded, skipping")
            return

        logger.info("Seeding database with initial data...")

        # Create test user
        test_user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="$2b$12$test_hashed_password",  # Placeholder
            is_active=True,
            risk_level="medium",
            paper_trading_enabled=True,
            live_trading_enabled=False,
            live_trading_approved=False,
            initial_portfolio_value=100000.0,
        )
        db.add(test_user)
        db.flush()  # Get the user ID

        # Create watchlist
        watchlist = Watchlist(
            user_id=test_user.id,
            name="Tech Stocks",
            description="Technology sector stocks for options trading",
            is_active=True,
        )
        db.add(watchlist)
        db.flush()

        # Add symbols to watchlist
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "META"]
        for symbol in symbols:
            ws = WatchlistSymbol(
                watchlist_id=watchlist.id,
                symbol=symbol,
            )
            db.add(ws)

        # Create sample option contracts
        today = datetime.utcnow()
        expiration = (today + timedelta(days=30)).strftime("%Y-%m-%d")

        sample_contracts = [
            {
                "symbol": "AAPL",
                "expiration": expiration,
                "strike": 150.0,
                "contract_type": "call",
                "bid": 2.0,
                "ask": 2.1,
                "volume": 1000,
                "open_interest": 5000,
                "implied_volatility": 0.25,
                "underlying_price": 150.0,
                "days_to_expiration": 30,
            },
            {
                "symbol": "MSFT",
                "expiration": expiration,
                "strike": 300.0,
                "contract_type": "call",
                "bid": 3.5,
                "ask": 3.7,
                "volume": 800,
                "open_interest": 4000,
                "implied_volatility": 0.22,
                "underlying_price": 300.0,
                "days_to_expiration": 30,
            },
            {
                "symbol": "GOOGL",
                "expiration": expiration,
                "strike": 100.0,
                "contract_type": "put",
                "bid": 1.5,
                "ask": 1.6,
                "volume": 600,
                "open_interest": 3000,
                "implied_volatility": 0.28,
                "underlying_price": 100.0,
                "days_to_expiration": 30,
            },
        ]

        for contract_data in sample_contracts:
            contract = OptionContract(**contract_data)
            db.add(contract)

        db.commit()
        logger.info("Database seeded successfully")

    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import logging.config

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    seed_database()
