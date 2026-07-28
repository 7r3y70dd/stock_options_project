from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/api/dashboard", tags=["dev-workflows"])

FILTERS_PATH = Path(os.getenv("STRATEGY_FILTERS_PATH", "/tmp/options_tracker_strategy_filters.json"))
BACKTESTS_PATH = Path(os.getenv("BACKTESTS_PATH", "/tmp/options_tracker_backtests.json"))

DEFAULT_FILTERS = {
    "data_provider": "marketdata",
    "enabled_strategies": ["covered_call", "cash_secured_put"],
    "max_signals_per_symbol": 2,
    "strike_limit": 10,
    "dte": 30,
    "min_volume": 50,
    "min_open_interest": 250,
    "max_bid_ask_spread_pct": 15,
    "min_score": 0,
    "max_loss_pct": 2,
    "clear_open_signals": True,
}


def get_any(obj: Any, names: list[str], default: Any = None) -> Any:
    if obj is None:
        return default

    if isinstance(obj, dict):
        for name in names:
            value = obj.get(name)
            if value is not None:
                return value
        return default

    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value

    return default


def set_if_exists(obj: Any, names: list[str], value: Any) -> list[str]:
    changed = []

    if obj is None:
        return changed

    for name in names:
        if hasattr(obj, name):
            setattr(obj, name, value)
            changed.append(name)

    return changed


def iso(value: Any) -> Any:
    if value is not None and hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def normalize_date(value: Any) -> str:
    if value is None:
        return ""
    return str(value)[:10]


def option_mid(option: Any) -> float | None:
    mid = get_any(option, ["mid", "mid_price", "mark", "current_price"])
    if mid is not None:
        return float(mid)

    bid = get_any(option, ["bid", "bid_price"])
    ask = get_any(option, ["ask", "ask_price"])

    if bid is not None and ask is not None:
        return (float(bid) + float(ask)) / 2

    last = get_any(option, ["last", "last_price"])
    if last is not None:
        return float(last)

    return None


def get_provider():
    provider_name = os.getenv("DATA_PROVIDER", "marketdata").lower()

    if provider_name in {"marketdata", "marketdata_app", "market_data"}:
        from app.data_sources.marketdata_provider import MarketDataProvider
        return MarketDataProvider()

    if provider_name in {"mock"}:
        from app.data_sources.mock_provider import MockDataProvider
        return MockDataProvider()

    if provider_name in {"yfinance", "yf"}:
        from app.data_sources.yfinance_provider import YFinanceProvider
        return YFinanceProvider()

    if provider_name in {"alpha", "alpha_vantage", "alphavantage"}:
        from app.data_sources.alpha_vantage_provider import AlphaVantageProvider
        return AlphaVantageProvider()

    if provider_name in {"polygon", "polygonio", "polygon_io"}:
        from app.data_sources.polygon_provider import PolygonProvider
        return PolygonProvider()

    raise HTTPException(status_code=400, detail=f"Unsupported DATA_PROVIDER={provider_name}")


def load_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def save_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


def get_strategy_filters(user_id: int) -> dict[str, Any]:
    all_filters = load_json_file(FILTERS_PATH, {})
    user_filters = all_filters.get(str(user_id), {})
    merged = dict(DEFAULT_FILTERS)
    merged.update(user_filters)
    return merged


def save_strategy_filters(user_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    all_filters = load_json_file(FILTERS_PATH, {})
    current = get_strategy_filters(user_id)
    current.update({k: v for k, v in updates.items() if v is not None})
    all_filters[str(user_id)] = current
    save_json_file(FILTERS_PATH, all_filters)
    return current


async def read_body(request: Request) -> dict[str, Any]:
    try:
        if request.headers.get("content-length") in {None, "0"}:
            return {}
        body = await request.json()
        return body if isinstance(body, dict) else {}
    except Exception:
        return {}


def active_watchlist_symbols(user_id: int) -> list[str]:
    from app.core.database import SessionLocal
    from app.models.database import Watchlist, WatchlistSymbol

    db = SessionLocal()
    try:
        query = db.query(Watchlist)

        if hasattr(Watchlist, "user_id"):
            query = query.filter(Watchlist.user_id == user_id)

        if hasattr(Watchlist, "is_active"):
            query = query.filter(Watchlist.is_active == True)  # noqa: E712

        watchlist = query.first()
        if not watchlist:
            return []

        rows = db.query(WatchlistSymbol).filter(WatchlistSymbol.watchlist_id == watchlist.id).all()
        return sorted({str(row.symbol).upper() for row in rows if getattr(row, "symbol", None)})
    finally:
        db.close()


def count_signals() -> int:
    from app.core.database import SessionLocal
    from app.models.database import Signal

    db = SessionLocal()
    try:
        return db.query(Signal).count()
    finally:
        db.close()


def get_chain(provider: Any, symbol: str, expiration: str | None = None) -> list[Any]:
    if expiration:
        try:
            return provider.get_options_chain(symbol, expiration=expiration)
        except TypeError:
            pass

    return provider.get_options_chain(symbol)


def find_matching_option(chain: list[Any], contract: Any) -> Any | None:
    wanted_strike = get_any(contract, ["strike", "strike_price"])
    wanted_type = str(get_any(contract, ["contract_type", "option_type", "side"], "")).lower()
    wanted_exp = normalize_date(get_any(contract, ["expiration", "expiration_date", "expiry"]))

    if wanted_strike is None:
        return None

    for option in chain:
        strike = get_any(option, ["strike", "strike_price"])
        opt_type = str(get_any(option, ["contract_type", "option_type", "side"], "")).lower()
        opt_exp = normalize_date(get_any(option, ["expiration", "expiration_date", "expiry"]))

        if strike is None:
            continue

        if abs(float(strike) - float(wanted_strike)) > 0.01:
            continue

        if wanted_type and opt_type and wanted_type not in opt_type:
            continue

        if wanted_exp and opt_exp and opt_exp != wanted_exp:
            continue

        return option

    return None


def serialize_trade(db: Any, trade: Any) -> dict[str, Any]:
    from app.models.database import OptionContract, Signal

    signal = None
    contract = None

    signal_id = get_any(trade, ["signal_id"])
    option_contract_id = get_any(trade, ["option_contract_id"])

    if signal_id:
        signal = db.query(Signal).filter(Signal.id == signal_id).first()

    if option_contract_id:
        contract = db.query(OptionContract).filter(OptionContract.id == option_contract_id).first()

    symbol = (
        get_any(signal, ["symbol"]) or
        get_any(contract, ["underlying_symbol", "ticker", "symbol"]) or
        get_any(trade, ["symbol"]) or
        "UNKNOWN"
    )

    strategy_type = (
        get_any(signal, ["strategy_type"]) or
        get_any(trade, ["strategy_type"]) or
        "unknown"
    )

    entry_price = get_any(trade, ["entry_price"])
    current_price = option_mid(contract)
    quantity = int(get_any(trade, ["quantity"], 1) or 1)

    current_pl = None
    current_pl_pct = None

    if entry_price is not None and current_price is not None:
        entry = float(entry_price)
        current = float(current_price)
        strategy_text = str(strategy_type).lower()

        if strategy_text in {"long_call", "long_put", "long_call_put"}:
            current_pl = (current - entry) * 100 * quantity
        else:
            current_pl = (entry - current) * 100 * quantity

        cost_basis = abs(entry * 100 * quantity)
        current_pl_pct = current_pl / cost_basis if cost_basis else 0.0

    return {
        "trade_id": get_any(trade, ["id"]),
        "signal_id": signal_id,
        "option_contract_id": option_contract_id,
        "symbol": symbol,
        "strategy_type": strategy_type,
        "entry_price": entry_price,
        "current_price": current_price,
        "quantity": quantity,
        "status": get_any(trade, ["status"], "open"),
        "order_status": get_any(trade, ["order_status"]),
        "is_paper_trading": get_any(trade, ["is_paper_trading"], True),
        "opened_at": iso(get_any(trade, ["opened_at", "created_at"])),
        "closed_at": iso(get_any(trade, ["closed_at"])),
        "exit_price": get_any(trade, ["exit_price"]),
        "realized_pnl": get_any(trade, ["realized_pnl"]),
        "current_pl": current_pl,
        "current_pl_pct": current_pl_pct,
        "strike": get_any(contract, ["strike", "strike_price"]),
        "expiration": iso(get_any(contract, ["expiration", "expiration_date", "expiry"])),
        "contract_type": get_any(contract, ["contract_type", "option_type", "side"]),
        "bid": get_any(contract, ["bid", "bid_price"]),
        "ask": get_any(contract, ["ask", "ask_price"]),
        "last": get_any(contract, ["last", "last_price"]),
        "volume": get_any(contract, ["volume"]),
        "open_interest": get_any(contract, ["open_interest", "openInterest"]),
        "implied_volatility": get_any(contract, ["implied_volatility", "iv"]),
        "delta": get_any(contract, ["delta"]),
        "gamma": get_any(contract, ["gamma"]),
        "theta": get_any(contract, ["theta"]),
        "vega": get_any(contract, ["vega"]),
        "signal_reason": get_any(signal, ["reason", "analysis", "full_analysis"]),
        "score": get_any(signal, ["score"]),
        "expected_profit": get_any(signal, ["expected_profit"]),
        "max_loss": get_any(signal, ["max_loss"]),
        "exit_rules": get_any(trade, ["exit_rules"]),
    }


def refresh_open_trade_contracts(user_id: int) -> dict[str, Any]:
    from app.core.database import SessionLocal
    from app.models.database import OptionContract, Signal, Trade

    provider = get_provider()
    db = SessionLocal()

    updated = 0
    skipped = 0
    failed = 0
    errors: list[dict[str, Any]] = []

    try:
        query = db.query(Trade)

        if hasattr(Trade, "user_id"):
            query = query.filter(Trade.user_id == user_id)

        if hasattr(Trade, "status"):
            query = query.filter(Trade.status == "open")

        trades = query.all()

        for trade in trades:
            trade_id = get_any(trade, ["id"])
            contract_id = get_any(trade, ["option_contract_id"])
            signal_id = get_any(trade, ["signal_id"])

            contract = db.query(OptionContract).filter(OptionContract.id == contract_id).first() if contract_id else None
            signal = db.query(Signal).filter(Signal.id == signal_id).first() if signal_id else None

            if not contract:
                skipped += 1
                errors.append({"trade_id": trade_id, "error": "missing option contract"})
                continue

            symbol = (
                get_any(signal, ["symbol"]) or
                get_any(contract, ["underlying_symbol", "ticker", "symbol"])
            )
            expiration = normalize_date(get_any(contract, ["expiration", "expiration_date", "expiry"]))

            if not symbol:
                skipped += 1
                errors.append({"trade_id": trade_id, "error": "missing symbol"})
                continue

            try:
                chain = get_chain(provider, str(symbol), expiration or None)
                match = find_matching_option(chain, contract)

                if not match:
                    skipped += 1
                    errors.append({"trade_id": trade_id, "symbol": symbol, "error": "no matching option from provider"})
                    continue

                mid = option_mid(match)

                set_if_exists(contract, ["bid", "bid_price"], get_any(match, ["bid", "bid_price"]))
                set_if_exists(contract, ["ask", "ask_price"], get_any(match, ["ask", "ask_price"]))
                set_if_exists(contract, ["last", "last_price"], get_any(match, ["last", "last_price"]))
                set_if_exists(contract, ["mid", "mid_price", "current_price"], mid)
                set_if_exists(contract, ["volume"], get_any(match, ["volume"]))
                set_if_exists(contract, ["open_interest", "openInterest"], get_any(match, ["open_interest", "openInterest"]))
                set_if_exists(contract, ["implied_volatility", "iv"], get_any(match, ["implied_volatility", "iv"]))
                set_if_exists(contract, ["delta"], get_any(match, ["delta"]))
                set_if_exists(contract, ["gamma"], get_any(match, ["gamma"]))
                set_if_exists(contract, ["theta"], get_any(match, ["theta"]))
                set_if_exists(contract, ["vega"], get_any(match, ["vega"]))
                set_if_exists(contract, ["updated_at", "last_updated"], datetime.utcnow())

                updated += 1

            except Exception as exc:
                failed += 1
                errors.append({"trade_id": trade_id, "symbol": symbol, "error": str(exc)})

        db.commit()

        rows = [serialize_trade(db, trade) for trade in trades]

        return {
            "success": failed == 0,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "errors": errors,
            "trades": rows,
            "open_trades": rows,
            "count": len(rows),
        }
    finally:
        db.close()


def refresh_watchlist_quotes(user_id: int) -> dict[str, Any]:
    from app.core.database import SessionLocal
    from app.models.database import Watchlist, WatchlistSymbol

    provider = get_provider()
    db = SessionLocal()

    updated = 0
    skipped = 0
    failed = 0
    errors: list[dict[str, Any]] = []

    try:
        query = db.query(Watchlist)

        if hasattr(Watchlist, "user_id"):
            query = query.filter(Watchlist.user_id == user_id)

        if hasattr(Watchlist, "is_active"):
            query = query.filter(Watchlist.is_active == True)  # noqa: E712

        watchlist = query.first()
        if not watchlist:
            return {"updated": 0, "skipped": 0, "failed": 0, "errors": [{"error": "no active watchlist"}]}

        rows = db.query(WatchlistSymbol).filter(WatchlistSymbol.watchlist_id == watchlist.id).all()

        for row in rows:
            symbol = str(getattr(row, "symbol", "")).upper().strip()
            if not symbol:
                skipped += 1
                continue

            try:
                quote = provider.get_quote(symbol)
                if not quote:
                    skipped += 1
                    errors.append({"symbol": symbol, "error": "no quote returned"})
                    continue

                price = get_any(quote, ["price", "last", "last_price", "current_price"])
                bid = get_any(quote, ["bid"])
                ask = get_any(quote, ["ask"])
                volume = get_any(quote, ["volume"])

                set_if_exists(row, ["current_price", "last_price", "price"], price)
                set_if_exists(row, ["bid"], bid)
                set_if_exists(row, ["ask"], ask)
                set_if_exists(row, ["volume"], volume)
                set_if_exists(row, ["last_updated", "updated_at"], datetime.utcnow())

                updated += 1

            except Exception as exc:
                failed += 1
                errors.append({"symbol": symbol, "error": str(exc)})

        db.commit()

        return {
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "errors": errors,
        }
    finally:
        db.close()


@router.post("/trades/mark-to-market")
async def mark_trades_to_market(user_id: int = 1):
    return refresh_open_trade_contracts(user_id)


@router.post("/market-data/refresh")
async def refresh_market_data(user_id: int = 1):
    watchlist = refresh_watchlist_quotes(user_id)
    trades = refresh_open_trade_contracts(user_id)

    return {
        "success": trades.get("failed", 0) == 0,
        "watchlist": watchlist,
        "trades": {
            "updated": trades.get("updated", 0),
            "skipped": trades.get("skipped", 0),
            "failed": trades.get("failed", 0),
            "errors": trades.get("errors", []),
            "count": trades.get("count", 0),
        },
    }


@router.post("/watchlist/analyze")
async def analyze_watchlist(request: Request, user_id: int = 1):
    body = await read_body(request)
    settings = get_strategy_filters(user_id)
    settings.update({k: v for k, v in body.items() if v is not None})

    symbols = body.get("symbols") or active_watchlist_symbols(user_id)
    if isinstance(symbols, str):
        symbols = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    else:
        symbols = [str(s).strip().upper() for s in symbols if str(s).strip()]

    if not symbols:
        raise HTTPException(status_code=400, detail="No symbols found. Add symbols to watchlist first.")

    before = count_signals()

    env = os.environ.copy()
    env.update({
        "PYTHONPATH": "/app",
        "DATA_PROVIDER": str(settings.get("data_provider", "marketdata")),
        "SYMBOLS": ",".join(symbols),
        "MARKETDATA_STRIKE_LIMIT": str(settings.get("strike_limit", 10)),
        "MARKETDATA_DTE": str(settings.get("dte", 30)),
        "MAX_SIGNALS_PER_SYMBOL": str(settings.get("max_signals_per_symbol", 2)),
        "CLEAR_OPEN_SIGNALS": "1" if settings.get("clear_open_signals", True) else "0",
        "ENABLED_STRATEGIES": ",".join(settings.get("enabled_strategies", [])),
        "MIN_VOLUME": str(settings.get("min_volume", 50)),
        "MIN_OPEN_INTEREST": str(settings.get("min_open_interest", 250)),
        "MAX_BID_ASK_SPREAD_PCT": str(settings.get("max_bid_ask_spread_pct", 15)),
        "MIN_SCORE": str(settings.get("min_score", 0)),
        "MAX_LOSS_PCT": str(settings.get("max_loss_pct", 2)),
    })

    cwd = "/app" if Path("/app/scripts/dev_ingest_and_recommend.py").exists() else os.getcwd()

    proc = subprocess.run(
        [sys.executable, "scripts/dev_ingest_and_recommend.py"],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )

    after = count_signals()

    return {
        "success": proc.returncode == 0,
        "symbols_analyzed": symbols,
        "signals_before": before,
        "signals_after": after,
        "signals_created_estimate": max(after - before, 0),
        "returncode": proc.returncode,
        "stdout": proc.stdout[-5000:],
        "stderr": proc.stderr[-5000:],
        "settings": settings,
    }


@router.get("/strategy-filters")
async def get_filters(user_id: int = 1):
    return get_strategy_filters(user_id)


@router.post("/strategy-filters/update")
async def update_filters(request: Request, user_id: int = 1):
    body = await read_body(request)
    return save_strategy_filters(user_id, body)


@router.get("/trades/{trade_id}")
async def get_trade_detail(trade_id: int, user_id: int = 1):
    from app.core.database import SessionLocal
    from app.models.database import Trade

    db = SessionLocal()
    try:
        query = db.query(Trade).filter(Trade.id == trade_id)

        if hasattr(Trade, "user_id"):
            query = query.filter(Trade.user_id == user_id)

        trade = query.first()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")

        return serialize_trade(db, trade)
    finally:
        db.close()


def load_backtests() -> list[dict[str, Any]]:
    return load_json_file(BACKTESTS_PATH, [])


def save_backtests(rows: list[dict[str, Any]]) -> None:
    save_json_file(BACKTESTS_PATH, rows)


@router.post("/backtests/run")
async def run_backtest(request: Request, user_id: int = 1):
    body = await read_body(request)

    strategy = body.get("strategy", "covered_call")
    if strategy not in {"covered_call", "cash_secured_put"}:
        raise HTTPException(status_code=400, detail="MVP supports covered_call and cash_secured_put only.")

    backtest = {
        "backtest_id": str(uuid.uuid4()),
        "user_id": user_id,
        "status": "created_mvp",
        "created_at": datetime.utcnow().isoformat(),
        "message": "Backtest UI/API scaffold created. Wire this route to app.backtesting engine next.",
        "request": {
            "symbols": body.get("symbols", []),
            "strategy": strategy,
            "start_date": body.get("start_date"),
            "end_date": body.get("end_date"),
            "initial_cash": body.get("initial_cash"),
            "risk_level": body.get("risk_level", "medium"),
        },
        "results": {
            "total_return": None,
            "win_rate": None,
            "max_drawdown": None,
            "num_trades": None,
        },
    }

    rows = load_backtests()
    rows.insert(0, backtest)
    save_backtests(rows)

    return backtest


@router.get("/backtests")
async def list_backtests(user_id: int = 1):
    rows = [row for row in load_backtests() if int(row.get("user_id", user_id)) == int(user_id)]
    return {"backtests": rows, "count": len(rows)}


@router.get("/backtests/{backtest_id}")
async def get_backtest(backtest_id: str, user_id: int = 1):
    for row in load_backtests():
        if row.get("backtest_id") == backtest_id and int(row.get("user_id", user_id)) == int(user_id):
            return row

    raise HTTPException(status_code=404, detail="Backtest not found")
