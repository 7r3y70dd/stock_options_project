"""Error handling and exception handlers for FastAPI."""

import logging
from typing import Union

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
    ):
        """Initialize exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code
            error_code: Machine-readable error code
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(AppException):
    """Validation error."""

    def __init__(self, message: str):
        """Initialize validation error."""
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
        )


class NotFoundError(AppException):
    """Resource not found error."""

    def __init__(self, message: str):
        """Initialize not found error."""
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
        )


class UnauthorizedError(AppException):
    """Unauthorized error."""

    def __init__(self, message: str = "Unauthorized"):
        """Initialize unauthorized error."""
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
        )


class ForbiddenError(AppException):
    """Forbidden error."""

    def __init__(self, message: str = "Forbidden"):
        """Initialize forbidden error."""
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
        )


async def app_exception_handler(
    request: Request, exc: AppException
) -> JSONResponse:
    """Handle application exceptions.

    Args:
        request: FastAPI request
        exc: Application exception

    Returns:
        JSON error response
    """
    logger.error(
        f"AppException: {exc.error_code} - {exc.message}",
        extra={"status_code": exc.status_code, "path": request.url.path},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "status_code": exc.status_code,
        },
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle generic exceptions.

    Args:
        request: FastAPI request
        exc: Generic exception

    Returns:
        JSON error response
    """
    logger.exception(
        f"Unhandled exception: {type(exc).__name__}",
        extra={"path": request.url.path},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers with FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
