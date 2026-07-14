"""
Full local dev DB reseed.

Use this after pytest or destructive fixtures wipe your dev DB.

Default behavior:
- Refuses to run unless DB URL looks local/dev, unless ALLOW_DESTRUCTIVE_RESEED=1.
- Creates missing tables.
- Deletes all rows from all app tables in FK-safe order.
- Seeds demo user id=1.
- Seeds Default watchlist.
- Adds watchlist symbols from SYMBOLS, default AAPL,MSFT.
- Runs scripts/dev_ingest_and_recommend.py by default to create opportunities.

Usage:
    python scripts/dev_reseed_database.py

Useful env vars:
    USER_ID=1
    SYMBOLS="AAPL,MSFT"
    GENERATE_MOCK_SIGNALS=1
    DATA_PROVIDER=mock
    ALLOW_DESTRUCTIVE_RESEED=1
"""

import os
import runpy
from pathlib import Path

from app.core.database import Base, engine, SessionLocal

# Import models so SQLAlchemy metadata is fully populated.
from app.models.database import User, Watchlist, WatchlistSymbol  # noqa: F401


USER_ID = int(os.getenv("USER_ID", os.getenv("DEMO_USER_ID", "1")))
SYMBOLS = [
    symbol.strip().upper()
    for symbol in os.getenv("SYMBOLS", "AAPL,MSFT").split(",")
    if symbol.strip()
]
GENERATE_MOCK_SIGNALS = os.getenv("GENERATE_MOCK_SIGNALS", "1") == "1"


def guard_against_accidental_prod_wipe() -> None:
    db_url = str(engine.url)

    allow = os.getenv("ALLOW_DESTRUCTIVE_RESEED", "0") == "1"

    local_markers = [
        "localhost",
        "127.0.0.1",
        "options_tracker",
        "options_tracker_test",
        "sqlite",
    ]

    bad_markers = [
        "prod",
        "production",
        "amazonaws.com",
        "rds.amazonaws.com",
    ]

    looks_local = any(marker in db_url for marker in local_markers)
    looks_bad = any(marker in db_url.lower() for marker in bad_markers)

    print(f"DATABASE_URL/engine={db_url}")

    if allow:
        print("ALLOW_DESTRUCTIVE_RESEED=1 set; continuing.")
        return

    if looks_local and not looks_bad:
        print("DB looks local/dev; continuing.")
        return

    raise SystemExit(
        "Refusing destructive reseed because DB does not look local/dev. "
        "Set ALLOW_DESTRUCTIVE_RESEED=1 if you are absolutely sure."
    )


def wipe_all_rows(db) -> None:
    """
    Delete all rows in dependency-safe order.

    This keeps the schema but clears data.
    """
    print("\nWiping all app table rows...")

    for table in reversed(Base.metadata.sorted_tables):
        print(f"  deleting {table.name}")
        db.execute(table.delete())


def seed_demo_user_and_watchlist(db) -> None:
    print("\nSeeding demo user and watchlist...")

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

    watchlist = Watchlist(
        user_id=user.id,
        name="Default",
        description="Default demo watchlist",
        is_active=True,
    )
    db.add(watchlist)
    db.flush()

    for symbol in SYMBOLS:
        db.add(
            WatchlistSymbol(
                watchlist_id=watchlist.id,
                symbol=symbol,
            )
        )

    db.flush()

    print(f"Seeded user id={user.id}")
    print(f"Seeded watchlist id={watchlist.id}")
    print(f"Seeded symbols={','.join(SYMBOLS)}")


def print_counts(db) -> None:
    print("\nTable counts:")

    for table in Base.metadata.sorted_tables:
        count = db.execute(
            table.select().with_only_columns(table.c.id).limit(100000)
        ).fetchall()
        print(f"  {table.name}: {len(count)}")


def run_signal_generator() -> None:
    script = Path("scripts/dev_ingest_and_recommend.py")

    if not script.exists():
        print("\nSkipping mock signal generation; script missing:")
        print(f"  {script}")
        return

    print("\nGenerating mock recommendations...")

    os.environ.setdefault("DATA_PROVIDER", "mock")
    os.environ.setdefault("SYMBOLS", ",".join(SYMBOLS))
    os.environ.setdefault("MAX_SIGNALS_PER_SYMBOL", "5")
    os.environ.setdefault("CLEAR_OPEN_SIGNALS", "1")
    os.environ.setdefault("DEMO_USER_ID", str(USER_ID))

    runpy.run_path(str(script), run_name="__main__")


def main() -> None:
    guard_against_accidental_prod_wipe()

    print("\nCreating missing tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        wipe_all_rows(db)
        seed_demo_user_and_watchlist(db)
        db.commit()
        print_counts(db)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    if GENERATE_MOCK_SIGNALS:
        run_signal_generator()

    print("\nReseed complete.")
    print("")
    print("Useful checks:")
    print('  curl -s "http://localhost:8000/api/api/dashboard/?user_id=1" | python -m json.tool')
    print('  curl -s "http://localhost:8000/api/api/dashboard/opportunities?user_id=1&limit=10" | python -m json.tool')


if __name__ == "__main__":
    main()
