"""Shared formatting utilities for frontend display.

Provides consistent formatting for currency, percentages, dates, and null values
across all frontend components.
"""

from datetime import datetime
from typing import Any, Optional


def format_currency(value: Optional[float], precision: int = 2) -> str:
    """Format value as currency.
    
    Args:
        value: Numeric value to format
        precision: Number of decimal places
        
    Returns:
        Formatted currency string (e.g., "$1,234.56")
    """
    if value is None:
        return "N/A"
    
    try:
        return f"${value:,.{precision}f}"
    except (TypeError, ValueError):
        return "N/A"


def format_percentage(value: Optional[float], precision: int = 2) -> str:
    """Format value as percentage.
    
    Args:
        value: Numeric value to format (0.05 = 5%)
        precision: Number of decimal places
        
    Returns:
        Formatted percentage string (e.g., "5.00%")
    """
    if value is None:
        return "N/A"
    
    try:
        return f"{value * 100:.{precision}f}%"
    except (TypeError, ValueError):
        return "N/A"


def format_number(value: Optional[float], precision: int = 2) -> str:
    """Format value as number with thousands separator.
    
    Args:
        value: Numeric value to format
        precision: Number of decimal places
        
    Returns:
        Formatted number string (e.g., "1,234.56")
    """
    if value is None:
        return "N/A"
    
    try:
        return f"{value:,.{precision}f}"
    except (TypeError, ValueError):
        return "N/A"


def format_date(value: Optional[str], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format ISO datetime string to readable format.
    
    Args:
        value: ISO datetime string
        format_str: Output format string
        
    Returns:
        Formatted date string
    """
    if value is None:
        return "N/A"
    
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        else:
            dt = value
        return dt.strftime(format_str)
    except (TypeError, ValueError, AttributeError):
        return "N/A"


def format_score(value: Optional[float], precision: int = 2) -> str:
    """Format score value (typically 0-100).
    
    Args:
        value: Score value
        precision: Number of decimal places
        
    Returns:
        Formatted score string (e.g., "85.50")
    """
    if value is None:
        return "N/A"
    
    try:
        return f"{value:.{precision}f}"
    except (TypeError, ValueError):
        return "N/A"


def format_null_value(value: Any, default: str = "N/A") -> str:
    """Format null or empty values.
    
    Args:
        value: Value to check
        default: Default string for null/empty values
        
    Returns:
        Value as string or default
    """
    if value is None or value == "" or value == []:
        return default
    
    return str(value)


def format_change(value: Optional[float], precision: int = 2) -> str:
    """Format change value with +/- indicator.
    
    Args:
        value: Change value
        precision: Number of decimal places
        
    Returns:
        Formatted change string (e.g., "+5.50" or "-2.30")
    """
    if value is None:
        return "N/A"
    
    try:
        if value >= 0:
            return f"+{value:.{precision}f}"
        else:
            return f"{value:.{precision}f}"
    except (TypeError, ValueError):
        return "N/A"
