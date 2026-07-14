import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.core.config import settings
from app.core.database import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up...")
    init_db()
    yield
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(title="Options Tracker", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="app/frontend/static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="app/frontend/templates")

# Include API routers
app.include_router(health_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio(request: Request):
    """Serve portfolio page."""
    return templates.TemplateResponse("portfolio.html", {"request": request})


@app.get("/watchlist", response_class=HTMLResponse)
async def watchlist(request: Request):
    """Serve watchlist page."""
    return templates.TemplateResponse("watchlist.html", {"request": request})


@app.get("/risk-settings", response_class=HTMLResponse)
async def risk_settings(request: Request):
    """Serve risk settings page."""
    return templates.TemplateResponse("risk_settings.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
