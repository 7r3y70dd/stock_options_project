"""SQLAlchemy ORM models for Options Tracker.

Models for users, watchlists, option contracts, signals, trades, and backtest results.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Enum as SQLEnum,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    risk_level = Column(String(50), default="medium", nullable=False)  # low, medium, high
    paper_trading_enabled = Column(Boolean, default=True, nullable=False)
    live_trading_enabled = Column(Boolean, default=False, nullable=False)
    live_trading_approved = Column(Boolean, default=False, nullable=False)
    initial_portfolio_value = Column(Float, default=100000.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    watchlists = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="user", cascade="all, delete-orphan")
    backtest_results = relationship("BacktestResult", back_populates="user", cascade="all, delete-orphan")


class Watchlist(Base):
    """User watchlist model."""

    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="watchlists")
    symbols = relationship("WatchlistSymbol", back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistSymbol(Base):
    """Symbols in a watchlist."""

    __tablename__ = "watchlist_symbols"

    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey("watchlists.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    watchlist = relationship("Watchlist", back_populates="symbols")

    # Unique constraint: prevent duplicate symbols in the same watchlist
    __table_args__ = (
        UniqueConstraint('watchlist_id', 'symbol', name='uq_watchlist_symbol'),
    )


class OptionContract(Base):
    """Option contract model for storing normalized option chain data.
    
    Stores option contract data including Greeks (delta, gamma, theta, vega),
    market data (bid, ask, volume, open_interest), and contract specifications.
    """

    __tablename__ = "option_contracts"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    underlying_symbol = Column(String(20), nullable=True, index=True)  # For index options
    expiration = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    strike = Column(Float, nullable=False, index=True)
    contract_type = Column(String(10), nullable=False, index=True)  # call or put
    bid = Column(Float, nullable=False)
    ask = Column(Float, nullable=False)
    last = Column(Float, nullable=True)  # Last traded price
    volume = Column(Integer, nullable=False)
    open_interest = Column(Integer, nullable=False)
    implied_volatility = Column(Float, nullable=False)
    delta = Column(Float, nullable=True)  # Greek: delta
    gamma = Column(Float, nullable=True)  # Greek: gamma
    theta = Column(Float, nullable=True)  # Greek: theta
    vega = Column(Float, nullable=True)  # Greek: vega
    underlying_price = Column(Float, nullable=False)
    days_to_expiration = Column(Integer, nullable=False)
    earnings_date = Column(String(10), nullable=True)  # YYYY-MM-DD
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    trades = relationship("Trade", back_populates="option_contract")
    signals = relationship("Signal", back_populates="option_contract")

    # Composite index for efficient querying by expiration, strike, and contract_type
    __table_args__ = (
        Index('ix_option_contracts_expiration_strike_type', 'expiration', 'strike', 'contract_type'),
    )


class NewsArticle(Base):
    """News article model."""

    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String(2048), nullable=True, unique=True, index=True)  # URL is unique to prevent duplicates
    source = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=True, index=True)
    sentiment = Column(String(20), nullable=True)  # "positive", "negative", "neutral"
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # "finnhub", "alpha_vantage", "yfinance", etc.

    # Unique constraint: same URL should not be stored twice
    __table_args__ = (
        UniqueConstraint('url', name='uq_news_articles_url'),
    )


class Signal(Base):
    """Trading signal model."""

    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    option_contract_id = Column(Integer, ForeignKey("option_contracts.id"), nullable=False, index=True)
    signal_type = Column(String(50), nullable=False)  # buy, sell, hold, etc.
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    reason = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="signals")
    option_contract = relationship("OptionContract", back_populates="signals")


class Trade(Base):
    """Trade execution model."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    option_contract_id = Column(Integer, ForeignKey("option_contracts.id"), nullable=False, index=True)
    trade_type = Column(String(10), nullable=False)  # buy or sell
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    status = Column(String(50), default="open", nullable=False)  # open, closed, cancelled
    is_paper_trading = Column(Boolean, default=True, nullable=False)
    pnl = Column(Float, nullable=True)  # Profit/loss
    pnl_pct = Column(Float, nullable=True)  # Profit/loss percentage
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="trades")
    option_contract = relationship("OptionContract", back_populates="trades")


class BacktestResult(Base):
    """Backtest result model."""

    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    strategy_name = Column(String(255), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    start_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    end_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=False)
    total_return_pct = Column(Float, nullable=False)
    total_trades = Column(Integer, nullable=False)
    winning_trades = Column(Integer, nullable=False)
    losing_trades = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)
    max_drawdown_pct = Column(Float, nullable=False)
    sharpe_ratio = Column(Float, nullable=True)
    parameters = Column(Text, nullable=True)  # JSON string of strategy parameters
    results_summary = Column(Text, nullable=True)  # JSON string of detailed results
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="backtest_results")
