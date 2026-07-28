#!/usr/bin/env python3
"""Fast local loop for MarketData.app opportunity screening.

Usage inside Docker:
  python scripts/dev_marketdata_cycle.py --cheap --cash 75000 --risk medium
  python scripts/dev_marketdata_cycle.py --symbols "F,SOFI,NU,BB,NIO" --cash 75000 --risk medium
  python scripts/dev_marketdata_cycle.py --cheap --reset-db
"""

from __future__ import annotations

import argparse
import importlib
import os
import subprocess
import sys
import time
from typing import Any

import requests

CHEAP_SYMBOLS = [
    "SNAP",
    "OPEN",
    "LCID",
    "NIO",
    "BB",
    "MARA",
    "F",
    "NU",
    "VALE",
    "AAL",
    "SOFI",
    "RIVN",
    "JOBY",
    "PALL",
]

DEFAULT_API_BASE = os.getenv("APP_BASE_URL", "http://localhost:8000")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a fast MarketData opportunity cycle.")
    parser.add_argument("--symbols", default="", help="Comma-separated symbols.")
    parser.add_argument("--cheap", action="store_true", help="Use cheap/guardrail-friendly preset.")
    parser.add_argument("--cash", type=float, default=75_000.0)
    parser.add_argument("--risk", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--max-signals", type=int, default=3)
    parser.add_argument("--strike-limit", type=int, default=12)
    parser.add_argument("--dte", type=int, default=30)
    parser.add_argument("--limit", type=int, default=50, help="Dashboard opportunity display limit.")
    parser.add_argument("--reset-db", action="store_true", help="Reset DB/watchlist before ingest.")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear pending/open signals before ingest.")
    return parser.parse_args()


def selected_symbols(args: argparse.Namespace) -> list[str]:
    if args.symbols.strip():
        return [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    if args.cheap:
        return CHEAP_SYMBOLS

    return ["F", "SOFI", "NU", "BB", "NIO", "SNAP", "OPEN", "LCID"]


def require_marketdata_token() -> None:
    if not os.getenv("MARKETDATA_TOKEN"):
        raise SystemExit("MARKETDATA_TOKEN is missing. Source .env or pass it into docker compose exec.")


def set_user_cash_and_risk(user_id: int, cash: float, risk: str) -> None:
    from app.core.database import SessionLocal
    from app.models.database import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise SystemExit(f"No user found with id={user_id}")

        changed: list[str] = []

        for field in [
            "initial_portfolio_value",
            "cash",
            "cash_balance",
            "portfolio_value",
            "buying_power",
        ]:
            if hasattr(user, field):
                setattr(user, field, cash)
                changed.append(field)

        if hasattr(user, "risk_level"):
            user.risk_level = risk
            changed.append("risk_level")

        db.commit()

        print(f"Configured user_id={user_id}: cash=USD {cash:,.2f}, risk={risk}")
        print("Changed fields:", ", ".join(changed) if changed else "none")
    finally:
        db.close()


def reset_database(symbols: list[str], args: argparse.Namespace) -> None:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": "/app",
            "DATA_PROVIDER": "marketdata",
            "SYMBOLS": ",".join(symbols),
            "MARKETDATA_STRIKE_LIMIT": str(args.strike_limit),
            "MARKETDATA_DTE": str(args.dte),
            # Try to prevent the reset script from doing an extra recommendation pass.
            # If the script ignores this, the later ingest pass still clears/replaces signals.
            "GENERATE_MOCK_SIGNALS": "0",
        }
    )

    print("\nResetting local/dev DB and watchlist...")
    subprocess.run(
        [sys.executable, "scripts/dev_reseed_database.py"],
        check=True,
        env=env,
    )


def run_ingest(symbols: list[str], args: argparse.Namespace) -> None:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": "/app",
            "DATA_PROVIDER": "marketdata",
            "SYMBOLS": ",".join(symbols),
            "MARKETDATA_STRIKE_LIMIT": str(args.strike_limit),
            "MARKETDATA_DTE": str(args.dte),
            "MAX_SIGNALS_PER_SYMBOL": str(args.max_signals),
            "CLEAR_OPEN_SIGNALS": "0" if args.no_clear else "1",
        }
    )

    print("\nRunning MarketData ingest/recommend...")
    print("Symbols:", ",".join(symbols))
    print(
        f"max_signals={args.max_signals}, strike_limit={args.strike_limit}, "
        f"dte={args.dte}, clear={not args.no_clear}"
    )

    subprocess.run(
        [sys.executable, "scripts/dev_ingest_and_recommend.py"],
        check=True,
        env=env,
    )


def fetch_json(path: str) -> dict[str, Any]:
    url = f"{DEFAULT_API_BASE}{path}"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()


def render_dashboard_text(data: dict[str, Any]) -> str:
    # Prefer the uploaded/existing AppShell renderer.
    for module_name in [
        "app.frontend.app_shell",
        "app.frontend.dashboard_shell",
        "app.frontend.shell",
    ]:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, "render_dashboard"):
                return module.render_dashboard(data)
        except Exception:
            continue

    # Fallback renderer if AppShell is not importable.
    portfolio = data.get("portfolio_summary", {})
    opportunities = data.get("top_opportunities", [])

    lines = [
        "\n=== Dashboard Summary ===",
        f"Cash: ${portfolio.get('cash', 0):,.2f}",
        f"Total value: ${portfolio.get('total_value', 0):,.2f}",
        f"Pending signals: {portfolio.get('num_open_signals', 0)}",
        "",
        "Top opportunities:",
    ]

    for opp in opportunities[:10]:
        lines.append(
            f"  {opp.get('symbol')} {opp.get('strategy_type')} "
            f"score={opp.get('score')} "
            f"profit=${opp.get('expected_profit', 0):,.2f} "
            f"loss=${opp.get('max_loss', 0):,.2f}"
        )

    return "\n".join(lines)


def print_rejection_hint(args: argparse.Namespace) -> None:
    max_loss_pct = {"low": 1.0, "medium": 2.0, "high": 5.0}[args.risk]
    max_loss = args.cash * max_loss_pct / 100

    print("\nGuardrail budget:")
    print(f"  Risk level: {args.risk}")
    print(f"  Max loss percent: {max_loss_pct:.1f}%")
    print(f"  Max loss per trade: USD {max_loss:,.2f}")
    print("  Liquidity guardrails still apply, usually volume >= 50 and open interest >= 250.")


def main() -> None:
    args = parse_args()
    require_marketdata_token()

    symbols = selected_symbols(args)

    if args.reset_db:
        reset_database(symbols, args)

    set_user_cash_and_risk(args.user_id, args.cash, args.risk)
    run_ingest(symbols, args)

    # Give uvicorn/DB session a moment after ingest.
    time.sleep(0.5)

    dashboard = fetch_json(f"/api/api/dashboard/?user_id={args.user_id}")
    print(render_dashboard_text(dashboard))
    print_rejection_hint(args)

    print("\nOpen:")
    print("  http://localhost:8000/opportunities")
    print("  http://localhost:8000/dashboard")


if __name__ == "__main__":
    main()
