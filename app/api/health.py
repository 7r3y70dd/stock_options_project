"""Health check endpoint."""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, status

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, Any],
    summary="Health Check",
    description="Returns the health status of the application.",
)
async def health_check() -> Dict[str, Any]:
    """Health check endpoint.

    Returns:
        Health status with timestamp and app info
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Options Tracker API",
        "version": "0.1.0",
    }
