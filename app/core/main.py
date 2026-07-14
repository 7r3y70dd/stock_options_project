"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import health, dashboard
from app.frontend import setup_frontend
from app.core.config import settings


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Options Tracker",
        description="AI-powered options trading signals and portfolio management",
        version="0.1.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(dashboard.router, prefix="/api/api/dashboard", tags=["dashboard"])

    # Setup frontend routes and static files
    setup_frontend(app)

    return app


app = create_app()
