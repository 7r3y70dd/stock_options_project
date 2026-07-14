import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
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
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting up...")
    init_db()
    yield
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="Options Tracker",
    description="AI-powered options trading tracker and analyzer",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/frontend/static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="app/frontend/templates")

# Include API routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root route redirects to dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio(request: Request):
    """Portfolio page."""
    return templates.TemplateResponse("portfolio.html", {"request": request})


@app.get("/opportunities", response_class=HTMLResponse)
async def opportunities(request: Request):
    """Opportunities page."""
    return templates.TemplateResponse("opportunities.html", {"request": request})


@app.get("/opportunities/{signal_id}", response_class=HTMLResponse)
async def opportunity_detail(request: Request, signal_id: int):
    """Opportunity detail page."""
    return templates.TemplateResponse(
        "opportunity_detail.html",
        {"request": request, "signal_id": signal_id},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.core.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
