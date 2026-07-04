"""Shared UI states and utilities for frontend components.

Provides standardized loading, error, and empty states that can be used
across all frontend components for consistent UX.
"""

from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum


class LoadingState(Enum):
    """Loading state enumeration."""
    IDLE = "idle"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class ErrorState:
    """Represents an error state with user-facing message."""
    message: str
    code: Optional[str] = None
    details: Optional[str] = None

    def __str__(self) -> str:
        """Return user-facing error message."""
        return self.message


@dataclass
class EmptyState:
    """Represents an empty state with helpful message."""
    title: str
    message: str
    action_text: Optional[str] = None
    action_handler: Optional[Any] = None

    def __str__(self) -> str:
        """Return empty state message."""
        return f"{self.title}: {self.message}"


class UIStateManager:
    """Manages UI state transitions for components."""

    def __init__(self):
        """Initialize state manager."""
        self.state = LoadingState.IDLE
        self.error: Optional[ErrorState] = None
        self.data: Optional[Any] = None

    def set_loading(self) -> None:
        """Set state to loading."""
        self.state = LoadingState.LOADING
        self.error = None

    def set_success(self, data: Any) -> None:
        """Set state to success with data.
        
        Args:
            data: Data to store
        """
        self.state = LoadingState.SUCCESS
        self.data = data
        self.error = None

    def set_error(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        """Set state to error.
        
        Args:
            message: User-facing error message
            code: Optional error code
            details: Optional error details
        """
        self.state = LoadingState.ERROR
        self.error = ErrorState(message=message, code=code, details=details)
        self.data = None

    def reset(self) -> None:
        """Reset state to idle."""
        self.state = LoadingState.IDLE
        self.error = None
        self.data = None

    def is_loading(self) -> bool:
        """Check if currently loading."""
        return self.state == LoadingState.LOADING

    def is_error(self) -> bool:
        """Check if in error state."""
        return self.state == LoadingState.ERROR

    def is_success(self) -> bool:
        """Check if in success state."""
        return self.state == LoadingState.SUCCESS


def get_user_friendly_error(error_message: str) -> str:
    """Convert technical error message to user-friendly message.
    
    Args:
        error_message: Technical error message
        
    Returns:
        User-friendly error message
    """
    error_map = {
        "Connection refused": "Unable to connect to server. Please check your internet connection.",
        "404": "The requested resource was not found.",
        "500": "Server error. Please try again later.",
        "Timeout": "Request timed out. Please try again.",
        "Invalid symbol": "The stock symbol is invalid. Please check and try again.",
        "Duplicate": "This symbol is already in your watchlist.",
    }
    
    for key, friendly_msg in error_map.items():
        if key.lower() in error_message.lower():
            return friendly_msg
    
    return "An error occurred. Please try again."
