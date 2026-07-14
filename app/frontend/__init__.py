"""Frontend module for Options Tracker."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os

# Get the directory where this file is located
FRONTEND_DIR = Path(__file__).parent
TEMPLATES_DIR = FRONTEND_DIR / "templates"
STATIC_DIR = FRONTEND_DIR / "static"

# Initialize Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def setup_frontend(app: FastAPI) -> None:
    """Setup frontend routes and static file serving.
    
    Args:
        app: FastAPI application instance
    """
    # Mount static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    
    # Dashboard route
    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard():
        """Serve the dashboard page."""
        return templates.get_template("dashboard.html").render()
    
    # Opportunities route
    @app.get("/opportunities", response_class=HTMLResponse)
    async def opportunities():
        """Serve the opportunities page."""
        return templates.get_template("opportunities.html").render()
