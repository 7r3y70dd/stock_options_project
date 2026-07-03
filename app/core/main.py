"""Main application factory and setup."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_config
from app.api.health import router as health_router
from app.api.dashboard import router as dashboard_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = get_config()
    
    app = FastAPI(
        title="Options Tracker",
        description="Real-time options trading tracker and analyzer",
        version="1.0.0",
        debug=config.is_development(),
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, tags=["health"])
    app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])

    return app


app = create_app()
