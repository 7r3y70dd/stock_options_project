"""Database models for the stock options trading application.

Defines SQLAlchemy ORM models for users, watchlists, signals, trades,
options contracts, news articles, and market quotes.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class User(Base):
    """User account model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    watchlists = relationship("WatchlistSymbol", back_populates="user")
    signals = relationship("Signal", back_populates="user")
    trades = relationship("Trade", back_populates="user")


class WatchlistSymbol(Base):
    """Watchlist symbol model."""
    __tablename__ = "watchlist_symbols"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="watchlists")
    market_quotes = relationship("MarketQuote", back_populates="watchlist_symbol")


class MarketQuote(Base):
    """Market quote snapshot model for storing price data."""
    __tablename__ = "market_quotes"
    
    id = Column(Integer, primary_key=True)
    watchlist_symbol_id = Column(Integer, ForeignKey("watchlist_symbols.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    price = Column(Float, nullable=False)
    bid = Column(Float, nullable=True)
    ask = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    provider = Column(String(50), nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    watchlist_symbol = relationship("WatchlistSymbol", back_populates="market_quotes")


class Signal(Base):
    """Trading signal model."""
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    strategy_type = Column(String(50), nullable=False)
    score = Column(Float, nullable=False)
    expected_profit = Column(Float, nullable=True)
    max_loss = Column(Float, nullable=True)
    probability_estimate = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    breakdown = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="signals")
    trades = relationship("Trade", back_populates="signal")


class Trade(Base):
    """Trade execution model."""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)
    symbol = Column(String(20), nullable=False)
    strategy_type = Column(String(50), nullable=False)
    status = Column(String(50), default="open")
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=True)
    profit_loss = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="trades")
    signal = relationship("Signal", back_populates="trades")


class OptionContract(Base):
    """Option contract model."""
    __tablename__ = "option_contracts"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    expiration = Column(String(20), nullable=False)
    strike = Column(Float, nullable=False)
    contract_type = Column(String(10), nullable=False)  # call or put
    bid = Column(Float, nullable=True)
    ask = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    open_interest = Column(Integer, nullable=True)
    implied_volatility = Column(Float, nullable=True)
    delta = Column(Float, nullable=True)
    gamma = Column(Float, nullable=True)
    theta = Column(Float, nullable=True)
    vega = Column(Float, nullable=True)
    rho = Column(Float, nullable=True)
    underlying_price = Column(Float, nullable=True)
    days_to_expiration = Column(Integer, nullable=True)
    liquidity_score = Column(Float, nullable=True)
    provider = Column(String(50), nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)


class NewsArticle(Base):
    """News article model."""
    __tablename__ = "news_articles"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String(500), nullable=True)
    source = Column(String(100), nullable=True)
    published_at = Column(DateTime, nullable=True)
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    sentiment_score = Column(Float, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
