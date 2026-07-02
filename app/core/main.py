"""FastAPI application factory and startup logic."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.dashboard import router as dashboard_router
from app.core.config import config
from app.core.database import init_db
from app.core.error_handling import register_exception_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle (startup and shutdown).

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info(
        f"Starting {config.APP_NAME} v{config.APP_VERSION} in {config.ENVIRONMENT} mode"
    )
    logger.info(f"Debug mode: {config.DEBUG}")
    logger.info(f"Database: {config.DATABASE_URL}")
    logger.info(f"Redis: {config.REDIS_URL}")
    logger.info(f"Celery Broker: {config.CELERY_BROKER_URL}")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Initialize Celery
    try:
        from app.core.celery import celery_app
        logger.info("Celery initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Celery: {e}")
        raise

    yield

    # Shutdown
    logger.info(f"Shutting down {config.APP_NAME}")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=config.APP_NAME,
        version=config.APP_VERSION,
        description="Stock options research and paper-trading application",
        debug=config.DEBUG,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.ALLOWED_HOSTS if not config.DEBUG else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    register_exception_handlers(app)

    # Routes
    app.include_router(health_router)
    app.include_router(dashboard_router)

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.core.main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower(),
    )
