/**
 * Shared application utilities for the Options Tracker frontend.
 */

// Configuration
const API_BASE_URL = '/api';
const DASHBOARD_PREFIX = '/api/dashboard';
const DEFAULT_USER_ID = 1;

/**
 * Get the current user ID from localStorage or use default.
 * @returns {number} The user ID
 */
function getUserId() {
    const stored = localStorage.getItem('userId');
    return stored ? parseInt(stored, 10) : DEFAULT_USER_ID;
}

/**
 * Set the user ID in localStorage.
 * @param {number} userId - The user ID to store
 */
function setUserId(userId) {
    localStorage.setItem('userId', String(userId));
}

/**
 * Show the loading overlay.
 */
function showLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('hidden');
    }
}

/**
 * Hide the loading overlay.
 */
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
}

/**
 * Show an error message in the error toast.
 * @param {string} message - The error message to display
 * @param {number} duration - Duration to show the toast in milliseconds (0 = indefinite)
 */
function showError(message, duration = 5000) {
    const toast = document.getElementById('error-toast');
    const messageEl = document.getElementById('error-message');
    
    if (toast && messageEl) {
        messageEl.textContent = message;
        toast.classList.remove('hidden');
        
        if (duration > 0) {
            setTimeout(() => {
                toast.classList.add('hidden');
            }, duration);
        }
    }
}

/**
 * Hide the error toast.
 */
function hideError() {
    const toast = document.getElementById('error-toast');
    if (toast) {
        toast.classList.add('hidden');
    }
}

/**
 * Parse an API response and extract error message.
 * Supports multiple error shapes:
 * - { "ok": false, "detail": "..." }
 * - { "detail": "..." }
 * - { "error": "...", "message": "...", "status_code": ... }
 * - Network errors
 * @param {Response|Error} response - The fetch response or error
 * @returns {Promise<string>} The error message
 */
async function extractErrorMessage(response) {
    // Network error
    if (response instanceof Error) {
        return response.message || 'Network error';
    }
    
    // Try to parse JSON
    try {
        const data = await response.json();
        
        // Check for structured error shape
        if (data.error && data.message) {
            return `${data.error}: ${data.message}`;
        }
        
        // Check for detail field
        if (data.detail) {
            return data.detail;
        }
        
        // Check for message field
        if (data.message) {
            return data.message;
        }
        
        // Fallback to status text
        return response.statusText || 'Unknown error';
    } catch (e) {
        // JSON parse failed, use status text
        return response.statusText || 'Unknown error';
    }
}

/**
 * Make an API request with error handling.
 * @param {string} endpoint - The API endpoint (e.g., '/api/health')
 * @param {object} options - Fetch options (method, headers, body, etc.)
 * @returns {Promise<object>} The parsed JSON response
 * @throws {Error} If the request fails
 */
async function apiRequest(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : API_BASE_URL + endpoint;
    
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            const errorMessage = await extractErrorMessage(response);
            throw new Error(`${response.status}: ${errorMessage}`);
        }
        
        return await response.json();
    } catch (error) {
        const errorMessage = await extractErrorMessage(error);
        throw new Error(errorMessage);
    }
}

/**
 * Make an API request with loading and error state management.
 * @param {string} endpoint - The API endpoint
 * @param {object} options - Fetch options
 * @param {boolean} showLoadingOverlay - Whether to show the loading overlay (default: true)
 * @returns {Promise<object|null>} The parsed JSON response or null on error
 */
async function apiRequestWithState(endpoint, options = {}, showLoadingOverlay = true) {
    if (showLoadingOverlay) {
        showLoading();
    }
    
    try {
        const data = await apiRequest(endpoint, options);
        hideLoading();
        hideError();
        return data;
    } catch (error) {
        hideLoading();
        showError(error.message);
        return null;
    }
}

/**
 * Update the footer status with the last refresh time.
 * @param {Date|null} timestamp - The timestamp to display
 */
function updateFooterStatus(timestamp = null) {
    const statusEl = document.getElementById('footer-status');
    if (statusEl) {
        if (timestamp) {
            const formatted = formatDate(timestamp, 'time');
            statusEl.textContent = `Last updated: ${formatted}`;
        } else {
            statusEl.textContent = '';
        }
    }
}

/**
 * Initialize the app on page load.
 * Checks API health and sets up event listeners.
 */
async function initializeApp() {
    try {
        // Check API health
        const health = await apiRequest('/health');
        console.log('API health check passed:', health);
        updateFooterStatus(new Date());
    } catch (error) {
        console.warn('API health check failed:', error.message);
        showError('API connection failed. Some features may not work.');
    }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}
