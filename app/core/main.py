import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import dashboard, health
from app.core.config import settings
from app.core.database import init_db

# Initialize database
init_db()

# Setup templates and static files
template_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "templates")
static_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "static")

templates = Jinja2Templates(directory=template_dir)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(title="Options Tracker", lifespan=lifespan)

# Mount static files
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include API routers
app.include_router(health.router)
app.include_router(dashboard.router)


# Frontend Routes
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, user_id: int = 1):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user_id": user_id},
    )


@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio_page(request: Request, user_id: int = 1):
    return templates.TemplateResponse(
        "portfolio.html",
        {"request": request, "user_id": user_id},
    )


@app.get("/opportunities", response_class=HTMLResponse)
async def opportunities_page(request: Request, user_id: int = 1):
    return templates.TemplateResponse(
        "opportunities.html",
        {"request": request, "user_id": user_id},
    )


@app.get("/opportunities/{signal_id}", response_class=HTMLResponse)
async def opportunity_detail_page(request: Request, signal_id: int, user_id: int = 1):
    return templates.TemplateResponse(
        "opportunity_detail.html",
        {"request": request, "signal_id": signal_id, "user_id": user_id},
    )


@app.get("/trades", response_class=HTMLResponse)
async def trades_page(request: Request, user_id: int = 1):
    return templates.TemplateResponse(
        "trades.html",
        {"request": request, "user_id": user_id},
    )


@app.get("/watchlist", response_class=HTMLResponse)
async def watchlist_page(request: Request, user_id: int = 1):
    return templates.TemplateResponse(
        "watchlist.html",
        {"request": request, "user_id": user_id},
    )


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user_id": 1},
    )
