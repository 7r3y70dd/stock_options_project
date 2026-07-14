"""Main FastAPI application."""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute

from app.api import health, dashboard
from app.core.config import settings

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Options Tracker",
    description="AI-powered options trading tracker and analyzer",
    version="0.1.0",
)

# Include API routers
app.include_router(health.router)
app.include_router(dashboard.router)

# Setup static files
static_dir = Path(__file__).parent.parent / "frontend" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Dashboard HTML route
@app.get("/dashboard")
async def dashboard_page():
    """Serve the dashboard HTML page."""
    template_path = Path(__file__).parent.parent / "frontend" / "templates" / "dashboard.html"
    if template_path.exists():
        return FileResponse(str(template_path), media_type="text/html")
    else:
        return {"error": "Dashboard template not found"}, 404


def use_route_names_as_operation_ids(app: FastAPI) -> None:
    """
    Simplify operation IDs so that generated API clients have simpler function
    names.
    """
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name


use_route_names_as_operation_ids(app)
