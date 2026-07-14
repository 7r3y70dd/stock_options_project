"""Formatting utilities for dashboard display.

Provides functions for formatting currency, percentages, numbers,
and dates with proper null handling.
"""

import logging
from typing import Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def format_currency(value: Any, default: str = "$0.00") -> str:
    """Format value as currency.
    
    Args:
        value: Value to format
        default: Default string if value is None
        
    Returns:
        Formatted currency string
    """
    if value is None:
        return default
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return default


def format_percentage(value: Any, default: str = "0.00%") -> str:
    """Format value as percentage.
    
    Args:
        value: Value to format (0-100 or 0-1)
        default: Default string if value is None
        
    Returns:
        Formatted percentage string
    """
    if value is None:
        return default
    try:
        num = float(value)
        # If value is between 0 and 1, assume it's a decimal
        if -1 <= num <= 1:
            num = num * 100
        return f"{num:.2f}%"
    except (ValueError, TypeError):
        return default


def format_number(value: Any, default: str = "0") -> str:
    """Format value as number.
    
    Args:
        value: Value to format
        default: Default string if value is None
        
    Returns:
        Formatted number string
    """
    if value is None:
        return default
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return default


def format_date(value: Any, default: str = "Not available") -> str:
    """Format value as date.
    
    Args:
        value: Value to format (datetime or string)
        default: Default string if value is None
        
    Returns:
        Formatted date string
    """
    if value is None:
        return default
    try:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(value, str):
            # Try to parse ISO format
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return default
    except (ValueError, TypeError, AttributeError):
        return default


def format_price(value: Any, default: str = "Price unavailable") -> str:
    """Format value as price.
    
    Args:
        value: Value to format
        default: Default string if value is None
        
    Returns:
        Formatted price string
    """
    if value is None:
        return default
    try:
        return f"${float(value):.2f}"
    except (ValueError, TypeError):
        return default
