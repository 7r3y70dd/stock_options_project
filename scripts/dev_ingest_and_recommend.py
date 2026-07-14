"""
Dev-only data ingestion + options recommendation script.

Purpose:
- Pull quote/options/news from a selected data provider.
- Persist option contracts.
- Create scored Signal rows.
- Print the top paper-trade candidate.
- Make /api/api/dashboard/opportunities show recommendations.

Default provider is MockDataProvider because it gives clean complete data.
Use this for paper-trading workflow testing, not real-money decisions.
"""

import json
import os
from datetime import datetime
from typing import Any, Iterable

from app.core.database import Base, engine, SessionLocal
from app.models.database import User, Watchlist, WatchlistSymbol, OptionContract, Signal


USER_ID = int(os.getenv("DEMO_USER_ID", "1"))
DATA_PROVIDER = os.getenv("DATA_PROVIDER", "mock").strip().lower()
SYMBOLS = [
    symbol.strip().upper()
    for symbol in os.getenv("SYMBOLS", "AAPL,MSFT,NVDA").split(",")
    if symbol.strip()
]

MAX_SIGNALS_PER_SYMBOL = int(os.getenv("MAX_SIGNALS_PER_SYMBOL", "5"))
CLEAR_OPEN_SIGNALS = os.getenv("CLEAR_OPEN_SIGNALS", "1") == "1"


def get_provider():
    """Create selected data provider."""
    if DATA_PROVIDER == "mock":
        from app.data_sources.mock_provider import MockDataProvider

        return MockDataProvider()

    if DATA_PROVIDER in {"yfinance", "yf"}:
        # Class is currently named YfinanceProvider in this repo.
        from app.data_sources.yfinance_provider import YfinanceProvider

        return YfinanceProvider()

    if DATA_PROVIDER in {"alpha", "alpha_vantage", "alphavantage"}:
        from app.data_sources.alpha_vantage_provider import AlphaVantageProvider

        return AlphaVantageProvider()

    if DATA_PROVIDER == "finnhub":
        from app.data_sources.finnhub_provider import FinnhubProvider

        return FinnhubProvider()

    raise SystemExit(
        f"Unknown DATA_PROVIDER={DATA_PROVIDER!r}. "
        "Use mock, yfinance, alpha_vantage, or finnhub."
    )


def ensure_demo_user(db):
    """Create demo user if missing."""
    user = db.query(User).filter_by(id=USER_ID).first()
    if user:
        return user

    user = User(
        id=USER_ID,
        username="demo",
        email="demo@example.com",
        hashed_password="dev-only",
        risk_level="medium",
        paper_trading_enabled=True,
        live_trading_enabled=False,
        live_trading_approved=False,
        initial_portfolio_value=10000.0,
    )
    db.add(user)
    db.flush()
    return user


def ensure_default_watchlist(db, user):
    """Create active default watchlist if missing."""
    watchlist = (
        db.query(Watchlist)
        .filter_by(user_id=user.id, is_active=True)
        .first()
    )

    if watchlist:
        return watchlist

    watchlist = Watchlist(
        user_id=user.id,
        name="Default",
        description="Default demo watchlist",
        is_active=True,
    )
    db.add(watchlist)
    db.flush()
    return watchlist


def ensure_symbol_in_watchlist(db, watchlist, symbol: str):
    existing = (
        db.query(WatchlistSymbol)
        .filter_by(watchlist_id=watchlist.id, symbol=symbol)
        .first()
    )
    if existing:
        return existing

    row = WatchlistSymbol(watchlist_id=watchlist.id, symbol=symbol)
    db.add(row)
    db.flush()
    return row


def as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default


def as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except Exception:
        return default


def news_sentiment_score(news_items: Iterable[Any]) -> float:
    """
    Very simple dev sentiment score:
    positive = +1, neutral/unknown = 0, negative = -1
    """
    items = list(news_items or [])
    if not items:
        return 0.0

    score = 0.0
    for item in items:
        sentiment = (getattr(item, "sentiment", None) or "").lower()
        if sentiment == "positive":
            score += 1.0
        elif sentiment == "negative":
            score -= 1.0

    return score / max(len(items), 1)


def is_candidate(entry, quote_price: float) -> bool:
    """
    Keep only contracts with enough data to score.

    yfinance often returns None for bid/ask/open_interest/volume,
    so this filter intentionally rejects incomplete contracts.
    """
    bid = as_float(getattr(entry, "bid", None))
    ask = as_float(getattr(entry, "ask", None))
    strike = as_float(getattr(entry, "strike", None))
    volume = as_int(getattr(entry, "volume", None))
    open_interest = as_int(getattr(entry, "open_interest", None))

    if bid <= 0 or ask <= 0 or ask < bid:
        return False

    if strike <= 0:
        return False

    if volume <= 0 or open_interest <= 0:
        return False

    contract_type = (getattr(entry, "contract_type", "") or "").lower()

    # Prefer reasonably near-the-money candidates.
    if contract_type == "put":
        # Cash-secured put: prefer OTM puts below current price.
        return strike < quote_price and strike >= quote_price * 0.80

    if contract_type == "call":
        # Covered call: prefer OTM calls above current price.
        return strike > quote_price and strike <= quote_price * 1.20

    return False


def score_contract(entry, quote_price: float, sentiment: float) -> float:
    """
    Simple dev scoring model, 0-100.

    This is not financial advice. It is a deterministic paper-trading
    ranking heuristic for testing the app pipeline.
    """
    bid = as_float(getattr(entry, "bid", None))
    ask = as_float(getattr(entry, "ask", None))
    volume = as_int(getattr(entry, "volume", None))
    open_interest = as_int(getattr(entry, "open_interest", None))
    iv = as_float(getattr(entry, "implied_volatility", None), 0.30)
    delta = as_float(getattr(entry, "delta", None), 0.0)
    strike = as_float(getattr(entry, "strike", None))

    spread = max(ask - bid, 0.0)
    mid = (bid + ask) / 2 if bid and ask else 0.0
    spread_pct = spread / mid if mid else 1.0

    # Liquidity: reward volume/open interest.
    liquidity_score = min(100.0, (volume / 100.0) + (open_interest / 1000.0))

    # Spread: tighter spread is better.
    spread_score = max(0.0, 100.0 - spread_pct * 600.0)

    # IV: prefer moderate IV around 30-45% for this dev heuristic.
    iv_score = max(0.0, 100.0 - abs(iv - 0.35) * 150.0)

    # Moneyness: prefer near-ish OTM.
    moneyness = abs(strike - quote_price) / quote_price if quote_price else 1.0
    moneyness_score = max(0.0, 100.0 - moneyness * 500.0)

    # Delta sanity: not too extreme.
    delta_abs = abs(delta)
    delta_score = max(0.0, 100.0 - abs(delta_abs - 0.30) * 150.0)

    # Sentiment: small adjustment, not dominant.
    sentiment_score = 50.0 + sentiment * 15.0

    total = (
        liquidity_score * 0.25
        + spread_score * 0.25
        + iv_score * 0.20
        + moneyness_score * 0.15
        + delta_score * 0.10
        + sentiment_score * 0.05
    )

    return round(max(0.0, min(100.0, total)), 2)


def strategy_for(entry) -> str:
    contract_type = (getattr(entry, "contract_type", "") or "").lower()
    if contract_type == "put":
        return "cash_secured_put"
    if contract_type == "call":
        return "covered_call"
    return "unknown"


def expected_profit_and_max_loss(strategy: str, entry, quote_price: float) -> tuple[float, float]:
    """
    Approximate paper-trade economics.

    Cash-secured put:
      expected profit = premium collected
      max loss approx = strike*100 - premium

    Covered call:
      expected profit = premium collected
      max loss is not really captured without stock position accounting;
      approximate as underlying exposure minus premium.
    """
    bid = as_float(getattr(entry, "bid", None))
    ask = as_float(getattr(entry, "ask", None))
    strike = as_float(getattr(entry, "strike", None))

    premium = ((bid + ask) / 2.0) * 100.0

    if strategy == "cash_secured_put":
        max_loss = max(strike * 100.0 - premium, 0.0)
    elif strategy == "covered_call":
        max_loss = max(quote_price * 100.0 - premium, 0.0)
    else:
        max_loss = 0.0

    return round(premium, 2), round(max_loss, 2)


def upsert_option_contract(db, symbol: str, quote, entry):
    expiration = str(getattr(entry, "expiration"))
    strike = as_float(getattr(entry, "strike"))
    contract_type = str(getattr(entry, "contract_type")).lower()

    contract = (
        db.query(OptionContract)
        .filter_by(
            symbol=symbol,
            expiration=expiration,
            strike=strike,
            contract_type=contract_type,
        )
        .first()
    )

    if not contract:
        contract = OptionContract(
            symbol=symbol,
            underlying_symbol=symbol,
            expiration=expiration,
            strike=strike,
            contract_type=contract_type,
            bid=0.0,
            ask=0.0,
            volume=0,
            open_interest=0,
            implied_volatility=0.0,
            underlying_price=as_float(getattr(quote, "price", None)),
            days_to_expiration=7,
            last_updated=datetime.utcnow(),
        )
        db.add(contract)

    contract.bid = as_float(getattr(entry, "bid", None))
    contract.ask = as_float(getattr(entry, "ask", None))
    contract.last = as_float(getattr(entry, "last", None), None)
    contract.volume = as_int(getattr(entry, "volume", None))
    contract.open_interest = as_int(getattr(entry, "open_interest", None))
    contract.implied_volatility = as_float(
        getattr(entry, "implied_volatility", None)
    )
    contract.delta = as_float(getattr(entry, "delta", None), None)
    contract.gamma = as_float(getattr(entry, "gamma", None), None)
    contract.theta = as_float(getattr(entry, "theta", None), None)
    contract.vega = as_float(getattr(entry, "vega", None), None)
    contract.underlying_price = as_float(getattr(quote, "price", None))
    contract.last_updated = datetime.utcnow()

    db.flush()
    return contract


def create_signal(db, user, symbol: str, quote, entry, contract, score: float, sentiment: float):
    strategy = strategy_for(entry)
    expected_profit, max_loss = expected_profit_and_max_loss(
        strategy, entry, as_float(getattr(quote, "price", None))
    )

    bid = as_float(getattr(entry, "bid", None))
    ask = as_float(getattr(entry, "ask", None))
    mid = (bid + ask) / 2.0 if bid and ask else 0.0

    probability = round(max(0.05, min(0.95, score / 100.0)), 2)

    reason = (
        f"{strategy} candidate for {symbol}: score {score}/100. "
        f"Quote={as_float(getattr(quote, 'price', None)):.2f}, "
        f"strike={as_float(getattr(entry, 'strike', None)):.2f}, "
        f"expiration={getattr(entry, 'expiration', None)}, "
        f"mid premium={mid:.2f}. "
        "Score is based on liquidity, bid/ask spread, IV, moneyness, "
        "delta sanity, and simple news sentiment."
    )

    signal = Signal(
        user_id=user.id,
        symbol=symbol,
        strategy_type=strategy,
        risk_level=user.risk_level,
        score=score,
        expected_profit=expected_profit,
        max_loss=max_loss,
        probability_estimate=probability,
        reason=reason,
        status="pending",
        option_contract_id=contract.id,
        breakdown=json.dumps(
            {
                "provider": DATA_PROVIDER,
                "quote": as_float(getattr(quote, "price", None)),
                "expiration": getattr(entry, "expiration", None),
                "strike": as_float(getattr(entry, "strike", None)),
                "contract_type": getattr(entry, "contract_type", None),
                "bid": bid,
                "ask": ask,
                "mid": mid,
                "volume": as_int(getattr(entry, "volume", None)),
                "open_interest": as_int(getattr(entry, "open_interest", None)),
                "implied_volatility": as_float(
                    getattr(entry, "implied_volatility", None)
                ),
                "delta": as_float(getattr(entry, "delta", None), None),
                "sentiment_score": sentiment,
                "scoring_note": (
                    "Dev heuristic for paper-trading tests only; "
                    "not investment advice."
                ),
            }
        ),
        event_risks=json.dumps([]),
        exit_rules=json.dumps(
            {
                "paper_trade_only": True,
                "profit_target_pct": 50,
                "stop_loss_pct": 50,
                "max_days_held": 14,
                "review_frequency": "daily",
            }
        ),
    )

    db.add(signal)
    db.flush()
    return signal


def main():
    Base.metadata.create_all(bind=engine)

    provider = get_provider()
    db = SessionLocal()

    try:
        user = ensure_demo_user(db)
        watchlist = ensure_default_watchlist(db, user)

        if CLEAR_OPEN_SIGNALS:
            db.query(Signal).filter_by(user_id=user.id, status="open").delete(
                synchronize_session=False
            )

        all_signals = []

        print(f"DATA_PROVIDER={DATA_PROVIDER}")
        print(f"USER_ID={user.id}")
        print(f"RISK_LEVEL={user.risk_level}")
        print(f"SYMBOLS={','.join(SYMBOLS)}")
        print("")

        for symbol in SYMBOLS:
            ensure_symbol_in_watchlist(db, watchlist, symbol)

            quote = provider.get_quote(symbol)
            if not quote:
                print(f"{symbol}: no quote; skipping")
                continue

            chain = provider.get_options_chain(symbol)
            news = provider.get_news(symbol, limit=5)
            sentiment = news_sentiment_score(news)

            quote_price = as_float(getattr(quote, "price", None))
            candidates = [
                entry for entry in chain if is_candidate(entry, quote_price)
            ]

            ranked = sorted(
                candidates,
                key=lambda entry: score_contract(entry, quote_price, sentiment),
                reverse=True,
            )[:MAX_SIGNALS_PER_SYMBOL]

            print(
                f"{symbol}: quote={quote_price:.2f}, "
                f"chain={len(chain)}, candidates={len(candidates)}, "
                f"selected={len(ranked)}, sentiment={sentiment:.2f}"
            )

            for entry in ranked:
                score = score_contract(entry, quote_price, sentiment)
                contract = upsert_option_contract(db, symbol, quote, entry)
                signal = create_signal(
                    db, user, symbol, quote, entry, contract, score, sentiment
                )
                all_signals.append(signal)

        db.commit()

        all_signals = sorted(all_signals, key=lambda s: s.score, reverse=True)

        print("")
        print(f"CREATED_SIGNALS={len(all_signals)}")
        print("")

        for s in all_signals:
            print(
                {
                    "signal_id": s.id,
                    "symbol": s.symbol,
                    "strategy": s.strategy_type,
                    "score": s.score,
                    "probability_estimate": s.probability_estimate,
                    "expected_profit": s.expected_profit,
                    "max_loss": s.max_loss,
                    "risk_level": s.risk_level,
                    "status": s.status,
                }
            )

        print("")
        print("=== TOP PAPER-TRADE CANDIDATE ===")

        if not all_signals:
            print("No usable signals created.")
            print(
                "If using yfinance, many contracts may have null bid/ask/volume. "
                "Try DATA_PROVIDER=mock first."
            )
            return

        top = all_signals[0]
        print(f"Signal ID: {top.id}")
        print(f"Symbol: {top.symbol}")
        print(f"Strategy: {top.strategy_type}")
        print(f"Score: {top.score}/100")
        print(f"Probability estimate: {top.probability_estimate}")
        print(f"Expected profit: ${top.expected_profit}")
        print(f"Max loss estimate: ${top.max_loss}")
        print(f"Reason: {top.reason}")
        print("")
        print("Next: view it in the dashboard opportunities endpoint:")
        print(
            f'curl -i "http://localhost:8000/api/api/dashboard/opportunities'
            f'?user_id={user.id}&limit=10"'
        )
        print("")
        print("Reminder: paper trade / research only. Do not use as financial advice.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
