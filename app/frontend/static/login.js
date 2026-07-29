/**
 * Login page functionality for Options Tracker.
 */

const API_BASE_URL = '/api';
const DASHBOARD_PREFIX = '/api/dashboard';

/**
 * Show error message on login form.
 * @param {string} message - Error message to display
 */
function showLoginError(message) {
    const errorEl = document.getElementById('error-message');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.add('show');
    }
}

/**
 * Hide error message on login form.
 */
function hideLoginError() {
    const errorEl = document.getElementById('error-message');
    if (errorEl) {
        errorEl.classList.remove('show');
    }
}

/**
 * Disable login button during submission.
 * @param {boolean} disabled - Whether to disable the button
 */
function setLoginButtonDisabled(disabled) {
    const button = document.getElementById('login-button');
    if (button) {
        button.disabled = disabled;
        button.textContent = disabled ? 'Logging in...' : 'Login';
    }
}

/**
 * Handle login form submission.
 * @param {Event} event - Form submit event
 */
async function handleLogin(event) {
    event.preventDefault();
    hideLoginError();
    setLoginButtonDisabled(true);
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    
    if (!username || !password) {
        showLoginError('Please enter both username and password');
        setLoginButtonDisabled(false);
        return;
    }
    
    try {
        const response = await fetch(`${DASHBOARD_PREFIX}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Login failed');
        }
        
        if (data.success && data.token && data.user) {
            // Store session token and user info
            localStorage.setItem('sessionToken', data.token);
            localStorage.setItem('userId', String(data.user.id));
            localStorage.setItem('username', data.user.username);
            localStorage.setItem('userEmail', data.user.email);
            
            // Redirect to dashboard
            window.location.href = '/dashboard';
        } else {
            throw new Error('Invalid response from server');
        }
    } catch (error) {
        console.error('Login error:', error);
        showLoginError(error.message || 'Login failed. Please try again.');
        setLoginButtonDisabled(false);
    }
}

/**
 * Initialize login page.
 */
function initLoginPage() {
    // Check if already logged in
    const token = localStorage.getItem('sessionToken');
    if (token) {
        // Verify token is still valid
        fetch(`${DASHBOARD_PREFIX}/auth/verify?token=${encodeURIComponent(token)}`)
            .then(response => {
                if (response.ok) {
                    // Already logged in, redirect to dashboard
                    window.location.href = '/dashboard';
                } else {
                    // Token invalid, clear storage
                    localStorage.removeItem('sessionToken');
                    localStorage.removeItem('userId');
                    localStorage.removeItem('username');
                    localStorage.removeItem('userEmail');
                }
            })
            .catch(() => {
                // Network error, stay on login page
            });
    }
    
    // Setup form submission
    const form = document.getElementById('login-form');
    if (form) {
        form.addEventListener('submit', handleLogin);
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLoginPage);
} else {
    initLoginPage();
}
