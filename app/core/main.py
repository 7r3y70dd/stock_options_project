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


@app.get("/news", response_class=HTMLResponse)
async def news_page(request: Request):
    """News page."""
    return templates.TemplateResponse("news.html", {"request": request})


@app.get("/status", response_class=HTMLResponse)
async def status_page(request: Request):
    """System status page."""
    return templates.TemplateResponse("status.html", {"request": request})
