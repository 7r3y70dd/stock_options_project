"""Frontend module for Options Tracker."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pathlib import Path
import os

router = APIRouter()

# Setup templates and static files
template_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(template_dir))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/opportunities", response_class=HTMLResponse)
async def opportunities(request: Request):
    """Render opportunities list page."""
    return templates.TemplateResponse("opportunities.html", {"request": request})


@router.get("/opportunities/{signal_id}", response_class=HTMLResponse)
async def opportunity_detail(request: Request, signal_id: int):
    """Render opportunity detail page."""
    return templates.TemplateResponse("opportunity_detail.html", {"request": request, "signal_id": signal_id})


def setup_frontend(app):
    """Setup frontend routes and static files."""
    # Mount static files
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Include frontend router
    app.include_router(router)
