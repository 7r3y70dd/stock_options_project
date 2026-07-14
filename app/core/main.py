import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.core.config import settings
from app.core.database import engine, get_db
from app.models.database import Base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up...")
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="Options Tracker",
    description="AI-powered options trading tracker",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files
import os
static_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Setup Jinja2 templates
templates_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "templates")
if os.path.exists(templates_dir):
    templates = Jinja2Templates(directory=templates_dir)
else:
    templates = None

# Include API routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint redirects to dashboard."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Options Tracker</title>
        <meta http-equiv="refresh" content="0; url=/dashboard" />
    </head>
    <body>
        <p>Redirecting to <a href="/dashboard">dashboard</a>...</p>
    </body>
    </html>
    """


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the dashboard HTML page."""
    if templates is None:
        return "<h1>Templates not configured</h1>"
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/watchlist", response_class=HTMLResponse)
async def watchlist(request: Request):
    """Serve the watchlist HTML page."""
    if templates is None:
        return "<h1>Templates not configured</h1>"
    return templates.TemplateResponse("watchlist.html", {"request": request})


@app.get("/opportunities", response_class=HTMLResponse)
async def opportunities(request: Request):
    """Serve the opportunities HTML page."""
    if templates is None:
        return "<h1>Templates not configured</h1>"
    return templates.TemplateResponse("opportunities.html", {"request": request})


@app.get("/opportunities/{signal_id}", response_class=HTMLResponse)
async def opportunity_detail(request: Request, signal_id: int):
    """Serve the opportunity detail HTML page."""
    if templates is None:
        return "<h1>Templates not configured</h1>"
    return templates.TemplateResponse("opportunity_detail.html", {"request": request, "signal_id": signal_id})


@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio(request: Request):
    """Serve the portfolio HTML page."""
    if templates is None:
        return "<h1>Templates not configured</h1>"
    return templates.TemplateResponse("portfolio.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.core.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
