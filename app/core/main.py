import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.api import health, dashboard
from app.core import config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")


app = FastAPI(
    title="Options Tracker API",
    description="API for options trading strategies",
    version=config.VERSION,
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/frontend/static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="app/frontend/templates")

# Include API routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint redirects to dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/opportunities", response_class=HTMLResponse)
async def opportunities_page(request: Request):
    """Opportunities page."""
    return templates.TemplateResponse("opportunities.html", {"request": request})


@app.get("/opportunities/{signal_id}", response_class=HTMLResponse)
async def opportunity_detail_page(request: Request, signal_id: int):
    """Opportunity detail page."""
    return templates.TemplateResponse(
        "opportunity_detail.html", {"request": request, "signal_id": signal_id}
    )


@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio_page(request: Request):
    """Portfolio page."""
    return templates.TemplateResponse("portfolio.html", {"request": request})


@app.get("/watchlist", response_class=HTMLResponse)
async def watchlist_page(request: Request):
    """Watchlist page."""
    return templates.TemplateResponse("watchlist.html", {"request": request})


@app.get("/risk-settings", response_class=HTMLResponse)
async def risk_settings_page(request: Request):
    """Risk settings page."""
    return templates.TemplateResponse("risk_settings.html", {"request": request})




@app.get("/trades", response_class=HTMLResponse)
async def trades_page(request: Request):
    """Render trades page."""
    return templates.TemplateResponse("trades.html", {"request": request})

@app.get("/news", response_class=HTMLResponse)
async def news_page(request: Request):
    """News page."""
    return templates.TemplateResponse("news.html", {"request": request})


@app.get("/status", response_class=HTMLResponse)
async def status_page(request: Request):
    """System status page."""
    return templates.TemplateResponse("status.html", {"request": request})

@app.get("/api/api/dashboard/risk-settings")
async def dashboard_risk_settings(user_id: int = 1):
    """Return risk settings for frontend risk settings page."""
    from app.core.database import SessionLocal
    from app.models.database import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found", "user_id": user_id}

        risk_level = getattr(user, "risk_level", "medium") or "medium"

        return {
            "user_id": user.id,
            "risk_level": risk_level,
            "current_risk_level": risk_level,
            "paper_trading_enabled": bool(getattr(user, "paper_trading_enabled", True)),
            "live_trading_enabled": bool(getattr(user, "live_trading_enabled", False)),
            "live_trading_approved": bool(getattr(user, "live_trading_approved", False)),
            "initial_portfolio_value": float(getattr(user, "initial_portfolio_value", 10000.0) or 10000.0),
            "risk_profiles": {
                "low": {
                    "label": "Low Risk",
                    "description": "Conservative strategies with lower potential loss.",
                },
                "medium": {
                    "label": "Medium Risk",
                    "description": "Balanced strategies with moderate risk and return.",
                },
                "high": {
                    "label": "High Risk",
                    "description": "Aggressive strategies with higher potential loss.",
                },
            },
        }
    finally:
        db.close()


@app.post("/api/api/dashboard/risk-settings/update")
async def update_dashboard_risk_settings(
    user_id: int = 1,
    risk_level: str = "medium",
    confirmed: bool = False,
):
    """Update risk settings for frontend risk settings page."""
    from app.core.database import SessionLocal
    from app.models.database import User

    risk_level = risk_level.lower().strip()
    if risk_level not in {"low", "medium", "high"}:
        return {
            "success": False,
            "error": f"Invalid risk_level: {risk_level}",
            "allowed": ["low", "medium", "high"],
        }

    if risk_level == "high" and not confirmed:
        return {
            "success": False,
            "requires_confirmation": True,
            "message": "High risk requires confirmation.",
        }

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found", "user_id": user_id}

        user.risk_level = risk_level
        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "user_id": user.id,
            "risk_level": user.risk_level,
            "current_risk_level": user.risk_level,
            "message": f"Risk level updated to {user.risk_level}.",
        }
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}
    finally:
        db.close()

@app.get("/api/api/dashboard/trades/open-marked")
async def get_open_trades_marked(user_id: int = 1):
    """Return open trades with computed current option mark and paper P/L."""
    from app.core.database import SessionLocal
    from app.models.database import Trade, OptionContract, Signal

    def get_any(obj, names, default=None):
        if obj is None:
            return default
        for name in names:
            if hasattr(obj, name):
                value = getattr(obj, name)
                if value is not None:
                    return value
        return default

    def option_mid(contract):
        mid = get_any(contract, ["mid", "mid_price", "mark", "current_price"])
        if mid is not None:
            return float(mid)

        bid = get_any(contract, ["bid", "bid_price"])
        ask = get_any(contract, ["ask", "ask_price"])
        if bid is not None and ask is not None:
            return (float(bid) + float(ask)) / 2

        last = get_any(contract, ["last", "last_price"])
        if last is not None:
            return float(last)

        return None

    def iso(value):
        return value.isoformat() if value is not None and hasattr(value, "isoformat") else value

    db = SessionLocal()
    try:
        query = db.query(Trade)

        if hasattr(Trade, "user_id"):
            query = query.filter(Trade.user_id == user_id)

        if hasattr(Trade, "status"):
            query = query.filter(Trade.status == "open")

        trades = query.order_by(Trade.id.desc()).all()
        rows = []

        for trade in trades:
            contract = None
            signal = None

            option_contract_id = get_any(trade, ["option_contract_id"])
            signal_id = get_any(trade, ["signal_id"])

            if option_contract_id:
                contract = db.query(OptionContract).filter(OptionContract.id == option_contract_id).first()

            if signal_id:
                signal = db.query(Signal).filter(Signal.id == signal_id).first()

            symbol = (
                get_any(contract, ["symbol", "underlying_symbol", "ticker"]) or
                get_any(signal, ["symbol"]) or
                "UNKNOWN"
            )

            strategy_type = (
                get_any(signal, ["strategy_type"]) or
                get_any(trade, ["strategy_type"]) or
                "unknown"
            )

            entry_price = get_any(trade, ["entry_price"])
            quantity = int(get_any(trade, ["quantity"], 1) or 1)
            current_price = option_mid(contract)

            current_pl = None
            current_pl_pct = None

            if entry_price is not None and current_price is not None:
                entry = float(entry_price)
                current = float(current_price)

                # These paper trades are short-premium strategies:
                # covered_call and cash_secured_put profit when option value falls.
                if str(strategy_type).lower() in {"long_call", "long_put", "long_call_put"}:
                    current_pl = (current - entry) * 100 * quantity
                else:
                    current_pl = (entry - current) * 100 * quantity

                cost_basis = abs(entry * 100 * quantity)
                current_pl_pct = current_pl / cost_basis if cost_basis else 0.0

            rows.append({
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
            })

        return {
            "trades": rows,
            "open_trades": rows,
            "count": len(rows),
        }
    finally:
        db.close()

# --- dev workflow router/pages ---
from fastapi import Request as _DevRequest
from fastapi.responses import HTMLResponse as _DevHTMLResponse
from fastapi.templating import Jinja2Templates as _DevJinja2Templates

try:
    from app.api.dev_workflows import router as dev_workflows_router
    app.include_router(dev_workflows_router)
except Exception as exc:
    import logging as _dev_logging
    _dev_logging.getLogger(__name__).exception("Failed to include dev workflow router: %s", exc)

_dev_templates = _DevJinja2Templates(directory="app/frontend/templates")

@app.get("/trades/{trade_id}", response_class=_DevHTMLResponse)
async def trade_detail_page(request: _DevRequest, trade_id: int):
    return _dev_templates.TemplateResponse(
        "trade_detail.html",
        {"request": request, "trade_id": trade_id},
    )

@app.get("/backtests", response_class=_DevHTMLResponse)
async def backtests_page(request: _DevRequest):
    return _dev_templates.TemplateResponse(
        "backtests.html",
        {"request": request},
    )
