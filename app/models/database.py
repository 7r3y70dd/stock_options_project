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
    market data (bid, ask, volume, open_interest), volatility metrics
    (implied volatility, historical volatility, and volatility context),
    theoretical pricing (theoretical_price, pricing_difference),
    and event risk information.
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
    delta = Column(Float, nullable=True)  # Greek: delta (directional exposure)
    gamma = Column(Float, nullable=True)  # Greek: gamma (acceleration risk)
    theta = Column(Float, nullable=True)  # Greek: theta (time decay)
    vega = Column(Float, nullable=True)  # Greek: vega (volatility sensitivity)
    underlying_price = Column(Float, nullable=False)
    days_to_expiration = Column(Integer, nullable=False)
    earnings_date = Column(String(10), nullable=True)  # YYYY-MM-DD
    historical_volatility = Column(Float, nullable=True)  # Historical volatility calculated from price data
    volatility_context = Column(String(50), nullable=True)  # "expensive", "cheap", "fair", or None
    theoretical_price = Column(Float, nullable=True)  # Black-Scholes theoretical price
    pricing_difference = Column(Float, nullable=True)  # Market mid-price minus theoretical price
    pricing_assessment = Column(String(50), nullable=True)  # "overpriced", "underpriced", "fair"
    liquidity_score = Column(Float, nullable=True, default=0.0)  # Liquidity score 0-100
    event_risks = Column(Text, nullable=True)  # JSON string of detected event risks
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    trades = relationship("Trade", back_populates="option_contract")
    signals = relationship("Signal", back_populates="option_contract")

    # Composite index for efficient querying by expiration, strike, and contract_type
    __table_args__ = (
        Index('ix_option_contracts_expiration_strike_type', 'expiration', 'strike', 'contract_type'),
    )


class NewsArticle(Base):
    """News article model with sentiment analysis and event classification.
    
    Stores news articles with sentiment metadata including:
    - sentiment: Provider sentiment if available ("positive", "negative", "neutral")
    - sentiment_score: Normalized sentiment score (-1.0 to 1.0, where -1 is bearish, 0 is neutral, 1 is bullish)
    - confidence_score: Confidence in sentiment analysis (0.0 to 1.0)
    - event_type: Type of event detected (earnings, fda_decision, lawsuit, m_and_a, sec_investigation, analyst_upgrade, analyst_downgrade, macro_event)
    """

    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String(2048), nullable=True, unique=True, index=True)  # URL is unique to prevent duplicates
    source = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=True, index=True)
    sentiment = Column(String(20), nullable=True)  # "positive", "negative", "neutral" (from provider)
    sentiment_score = Column(Float, nullable=True)  # Normalized score: -1.0 (bearish) to 1.0 (bullish)
    confidence_score = Column(Float, nullable=True)  # Confidence in sentiment: 0.0 to 1.0
    event_type = Column(String(50), nullable=True)  # Type of event: earnings, fda_decision, lawsuit, m_and_a, sec_investigation, analyst_upgrade, analyst_downgrade, macro_event
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # "finnhub", "alpha_vantage", "yfinance", etc.

    # Unique constraint: same URL should not be stored twice
    __table_args__ = (
        UniqueConstraint('url', name='uq_news_articles_url'),
    )


class Signal(Base):
    """Trading signal model for storing generated trade ideas.
    
    Stores trading signals with comprehensive analysis including risk assessment,
    profit/loss estimates, strategy information, volatility context, Greeks analysis,
    and event-risk information. Every signal includes an explanation (reason) and 
    max-loss estimate as required.
    
    Status can be:
    - pending: Signal generated, awaiting review
    - approved: User approved the signal
    - rejected: User rejected the signal
    - expired: Signal expired (e.g., option expired)
    - executed: Trade was executed
    - no_trade: No safe opportunity found (risk thresholds not met)
    """

    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)  # Stock symbol
    strategy_type = Column(String(100), nullable=False)  # e.g., "bull_call_spread", "iron_condor"
    risk_level = Column(String(50), nullable=False)  # low, medium, high
    score = Column(Float, nullable=False)  # Overall signal score (0.0 to 1.0)
    expected_profit = Column(Float, nullable=False)  # Expected profit in dollars
    max_loss = Column(Float, nullable=False)  # Maximum loss estimate in dollars
    probability_estimate = Column(Float, nullable=False)  # Probability of profit (0.0 to 1.0)
    reason = Column(Text, nullable=False)  # Explanation of the signal (required)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, approved, rejected, expired, executed, no_trade
    option_contract_id = Column(Integer, ForeignKey("option_contracts.id"), nullable=True, index=True)  # Optional: linked contract
    breakdown = Column(Text, nullable=True)  # JSON string of factor scores and Greeks summary
    event_risks = Column(Text, nullable=True)  # JSON string of detected event risks
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="signals")
    option_contract = relationship("OptionContract", back_populates="signals")
    trades = relationship("Trade", back_populates="signal")

    # Composite index for efficient querying by user and status
    __table_args__ = (
        Index('ix_signals_user_status', 'user_id', 'status'),
    )


class Trade(Base):
    """Trade execution model for tracking paper and live trades.
    
    Stores trade execution details including entry/exit prices, P/L calculations,
    and links to signals and broker orders. Every trade is linked to a signal,
    and P/L can be calculated after the trade is closed.
    """

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False, index=True)  # Every order is linked to a signal
    option_contract_id = Column(Integer, ForeignKey("option_contracts.id"), nullable=False, index=True)
    broker_order_id = Column(String(255), nullable=True, index=True)  # Broker's order ID for tracking
    status = Column(String(50), default="open", nullable=False, index=True)  # open, closed, cancelled
    entry_price = Column(Float, nullable=False)  # Entry price per contract
    exit_price = Column(Float, nullable=True)  # Exit price per contract (null if still open)
    quantity = Column(Integer, nullable=False)  # Number of contracts
    realized_pnl = Column(Float, nullable=True)  # Realized P/L (null if still open)
    is_paper_trading = Column(Boolean, default=True, nullable=False)  # True for paper, False for live
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # When trade was opened
    closed_at = Column(DateTime, nullable=True)  # When trade was closed (null if still open)

    # Relationships
    user = relationship("User", back_populates="trades")
    signal = relationship("Signal", back_populates="trades")
    option_contract = relationship("OptionContract", back_populates="trades")

    # Composite index for efficient querying by user and status
    __table_args__ = (
        Index('ix_trades_user_status', 'user_id', 'status'),
    )


class BacktestResult(Base):
    """Backtest result model for storing historical signal replay results.
    
    Stores backtest metadata and summary statistics from historical signal replay.
    Each backtest result can have multiple associated simulated trades.
    """

    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    strategy_name = Column(String(255), nullable=False)  # Name of strategy tested
    symbol = Column(String(20), nullable=False, index=True)  # Stock symbol tested
    start_date = Column(DateTime, nullable=False)  # Backtest start date
    end_date = Column(DateTime, nullable=False)  # Backtest end date
    initial_cash = Column(Float, nullable=False)  # Starting capital
    final_value = Column(Float, nullable=False)  # Final portfolio value
    total_return = Column(Float, nullable=False)  # Total return percentage
    annual_return = Column(Float, nullable=False)  # Annualized return percentage
    sharpe_ratio = Column(Float, nullable=False)  # Sharpe ratio
    max_drawdown = Column(Float, nullable=False)  # Maximum drawdown percentage
    win_rate = Column(Float, nullable=False)  # Percentage of winning trades
    total_trades = Column(Integer, nullable=False)  # Number of trades executed
    avg_trade_profit = Column(Float, nullable=False)  # Average profit per trade
    best_trade = Column(Float, nullable=False)  # Best single trade profit
    worst_trade = Column(Float, nullable=False)  # Worst single trade loss
    profit_factor = Column(Float, nullable=False)  # Gross profit / gross loss
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="backtest_results")
    simulated_trades = relationship("SimulatedTrade", back_populates="backtest_result", cascade="all, delete-orphan")

    # Composite index for efficient querying by user and symbol
    __table_args__ = (
        Index('ix_backtest_results_user_symbol', 'user_id', 'symbol'),
    )


class SimulatedTrade(Base):
    """Simulated trade from historical signal replay.
    
    Stores individual trades generated during backtest/historical signal replay.
    Each trade is linked to a backtest result and includes entry/exit details,
    P&L, and the reason for entry.
    """

    __tablename__ = "simulated_trades"

    id = Column(Integer, primary_key=True, index=True)
    backtest_result_id = Column(Integer, ForeignKey("backtest_results.id"), nullable=False, index=True)
    entry_date = Column(DateTime, nullable=False)  # Date when trade was entered
    entry_price = Column(Float, nullable=False)  # Price at entry
    exit_date = Column(DateTime, nullable=True)  # Date when trade was exited (None if still open)
    exit_price = Column(Float, nullable=True)  # Price at exit (None if still open)
    quantity = Column(Integer, nullable=False)  # Number of shares/contracts
    pnl = Column(Float, nullable=True)  # Realized P&L (None if still open)
    pnl_pct = Column(Float, nullable=True)  # P&L as percentage (None if still open)
    reason = Column(Text, nullable=False)  # Reason for entry (from signal)
    signal_score = Column(Float, nullable=False)  # Score of the signal that triggered entry
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    backtest_result = relationship("BacktestResult", back_populates="simulated_trades")

    # Composite index for efficient querying by backtest result
    __table_args__ = (
        Index('ix_simulated_trades_backtest_result', 'backtest_result_id'),
    )
