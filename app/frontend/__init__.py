"""Frontend module for Options Tracker."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os

router = APIRouter()

# Setup templates and static files
template_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(template_dir))


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Render dashboard page."""
    return templates.get_template("dashboard.html").render()


@router.get("/opportunities", response_class=HTMLResponse)
async def opportunities():
    """Render opportunities list page."""
    return templates.get_template("opportunities.html").render()


@router.get("/opportunities/{signal_id}", response_class=HTMLResponse)
async def opportunity_detail(signal_id: int):
    """Render opportunity detail page."""
    return templates.get_template("opportunity_detail.html").render(signal_id=signal_id)


def setup_frontend(app):
    """Setup frontend routes and static files."""
    # Mount static files
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Include frontend router
    app.include_router(router)
