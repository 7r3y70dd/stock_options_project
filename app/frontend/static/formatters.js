/**
 * Shared formatting utilities for the Options Tracker frontend.
 */

/**
 * Format a number as USD currency.
 * @param {number|null|undefined} value - The value to format
 * @returns {string} Formatted currency string
 */
function formatCurrency(value) {
    if (value === null || value === undefined) {
        return 'N/A';
    }
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

/**
 * Format a number as a percentage.
 * @param {number|null|undefined} value - The value to format (0-1 or 0-100)
 * @param {number} decimals - Number of decimal places (default: 2)
 * @param {boolean} isDecimal - Whether value is in decimal form (0-1) or percent form (0-100)
 * @returns {string} Formatted percentage string
 */
function formatPercentage(value, decimals = 2, isDecimal = true) {
    if (value === null || value === undefined) {
        return 'N/A';
    }
    const numValue = isDecimal ? value * 100 : value;
    return numValue.toFixed(decimals) + '%';
}

/**
 * Format a number with thousand separators.
 * @param {number|null|undefined} value - The value to format
 * @param {number} decimals - Number of decimal places (default: 0)
 * @returns {string} Formatted number string
 */
function formatNumber(value, decimals = 0) {
    if (value === null || value === undefined) {
        return 'N/A';
    }
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(value);
}

/**
 * Format a date string or Date object.
 * @param {string|Date|null|undefined} value - The date to format
 * @param {string} format - Format type: 'short', 'long', 'time' (default: 'short')
 * @returns {string} Formatted date string
 */
function formatDate(value, format = 'short') {
    if (value === null || value === undefined) {
        return 'N/A';
    }
    
    const date = typeof value === 'string' ? new Date(value) : value;
    
    if (isNaN(date.getTime())) {
        return 'Invalid date';
    }
    
    const options = {
        short: { year: 'numeric', month: 'short', day: 'numeric' },
        long: { year: 'numeric', month: 'long', day: 'numeric' },
        time: { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }
    };
    
    return new Intl.DateTimeFormat('en-US', options[format] || options.short).format(date);
}

/**
 * Format a score value (0-100).
 * @param {number|null|undefined} value - The score to format
 * @returns {string} Formatted score string
 */
function formatScore(value) {
    if (value === null || value === undefined) {
        return 'N/A';
    }
    return value.toFixed(2);
}

/**
 * Format a null or undefined value as user-friendly text.
 * @param {any} value - The value to check
 * @param {string} fallback - Fallback text if value is null/undefined (default: 'N/A')
 * @returns {string} The value or fallback text
 */
function formatNullValue(value, fallback = 'N/A') {
    if (value === null || value === undefined) {
        return fallback;
    }
    return String(value);
}

/**
 * Format a boolean value as readable text.
 * @param {boolean|null|undefined} value - The boolean to format
 * @returns {string} 'Yes', 'No', or 'N/A'
 */
function formatBoolean(value) {
    if (value === null || value === undefined) {
        return 'N/A';
    }
    return value ? 'Yes' : 'No';
}
