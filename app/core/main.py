"""Main application factory and setup."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_config
from app.core.database import init_db


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Stock Options Trading System",
        description="AI-powered options trading strategy analyzer",
        version="1.0.0",
    )

    # Get config
    config = get_config()

    # Initialize database
    init_db()

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and include routers
    from app.api.dashboard import router as dashboard_router
    from app.api.health import router as health_router

    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])

    return app


# Create the app instance
app = create_app()
