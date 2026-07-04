"""Shared UI state classes for consistent loading, error, and empty state handling."""
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class LoadingState:
    """Represents a loading state."""

    is_loading: bool = False
    message: str = "Loading..."

    def start(self, message: str = "Loading...") -> None:
        """Start loading."""
        self.is_loading = True
        self.message = message

    def stop(self) -> None:
        """Stop loading."""
        self.is_loading = False
        self.message = ""


@dataclass
class ErrorState:
    """Represents an error state."""

    has_error: bool = False
    message: str = ""
    details: Optional[Dict[str, Any]] = None
    status_code: Optional[int] = None

    def set_error(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set error state."""
        self.has_error = True
        self.message = message
        self.status_code = status_code
        self.details = details or {}

    def clear(self) -> None:
        """Clear error state."""
        self.has_error = False
        self.message = ""
        self.details = None
        self.status_code = None

    def get_user_message(self) -> str:
        """Get user-friendly error message."""
        if self.status_code == 400:
            return f"Invalid request: {self.message}"
        elif self.status_code == 404:
            return "Resource not found"
        elif self.status_code == 500:
            return "Server error. Please try again later."
        elif self.status_code == 0:
            return f"Network error: {self.message}"
        else:
            return self.message or "An error occurred"


@dataclass
class EmptyState:
    """Represents an empty state."""

    is_empty: bool = False
    message: str = "No data available"
    action_text: Optional[str] = None

    def set_empty(self, message: str = "No data available", action_text: Optional[str] = None) -> None:
        """Set empty state."""
        self.is_empty = True
        self.message = message
        self.action_text = action_text

    def clear(self) -> None:
        """Clear empty state."""
        self.is_empty = False
        self.message = ""
        self.action_text = None


@dataclass
class UIState:
    """Combined UI state for components."""

    loading: LoadingState
    error: ErrorState
    empty: EmptyState

    def __init__(self):
        """Initialize UI state."""
        self.loading = LoadingState()
        self.error = ErrorState()
        self.empty = EmptyState()

    def reset(self) -> None:
        """Reset all states."""
        self.loading.stop()
        self.error.clear()
        self.empty.clear()

    def is_idle(self) -> bool:
        """Check if UI is in idle state (not loading, no error, not empty)."""
        return not self.loading.is_loading and not self.error.has_error and not self.empty.is_empty
