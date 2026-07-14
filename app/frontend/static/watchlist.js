// Watchlist Page JavaScript

const USER_ID = new URLSearchParams(window.location.search).get('user_id') || '1';
const API_BASE = '/api/api/dashboard';

const elements = {
    refreshBtn: document.getElementById('refreshBtn'),
    addSymbolForm: document.getElementById('addSymbolForm'),
    symbolInput: document.getElementById('symbolInput'),
    validationMessage: document.getElementById('validationMessage'),
    symbolCount: document.getElementById('symbolCount'),
    loadingState: document.getElementById('loadingState'),
    errorState: document.getElementById('errorState'),
    errorMessage: document.getElementById('errorMessage'),
    contentState: document.getElementById('contentState'),
    emptyState: document.getElementById('emptyState'),
    watchlistSection: document.getElementById('watchlistSection'),
    watchlistBody: document.getElementById('watchlistBody')
};

let currentWatchlist = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    elements.refreshBtn.addEventListener('click', loadWatchlist);
    elements.addSymbolForm.addEventListener('submit', handleAddSymbol);
    loadWatchlist();
});

// Load watchlist data
async function loadWatchlist() {
    try {
        showLoading(true);
        showError(false);
        
        const response = await fetch(`${API_BASE}/watchlist?user_id=${USER_ID}`);
        if (!response.ok) {
            throw new Error(`Failed to load watchlist: ${response.statusText}`);
        }
        
        const data = await response.json();
        currentWatchlist = data.symbols || [];
        
        renderWatchlist();
        showLoading(false);
    } catch (error) {
        console.error('Error loading watchlist:', error);
        showError(true, error.message);
        showLoading(false);
    }
}

// Render watchlist
function renderWatchlist() {
    const count = currentWatchlist.length;
    elements.symbolCount.textContent = count;
    
    if (count === 0) {
        elements.emptyState.classList.remove('hidden');
        elements.watchlistSection.classList.add('hidden');
        return;
    }
    
    elements.emptyState.classList.add('hidden');
    elements.watchlistSection.classList.remove('hidden');
    
    elements.watchlistBody.innerHTML = currentWatchlist.map(item => `
        <tr>
            <td class="symbol-cell">${escapeHtml(item.symbol)}</td>
            <td class="price-cell">${formatPrice(item.current_price)}</td>
            <td>${formatDate(item.added_at)}</td>
            <td>${formatDate(item.last_updated)}</td>
            <td>${formatFreshness(item.data_freshness_seconds)}</td>
            <td class="actions-cell">
                <button class="btn-remove" onclick="handleRemoveSymbol('${escapeHtml(item.symbol)}')">
                    Remove
                </button>
            </td>
        </tr>
    `).join('');
}

// Handle add symbol
async function handleAddSymbol(e) {
    e.preventDefault();
    
    const symbol = elements.symbolInput.value.trim().toUpperCase();
    if (!symbol) {
        showValidationMessage('Please enter a symbol', 'error');
        return;
    }
    
    // Check for duplicate
    if (currentWatchlist.some(item => item.symbol === symbol)) {
        showValidationMessage(`${symbol} is already in your watchlist`, 'error');
        elements.symbolInput.value = '';
        return;
    }
    
    try {
        // Validate symbol
        const validateResponse = await fetch(`${API_BASE}/watchlist/validate?symbol=${encodeURIComponent(symbol)}`, {
            method: 'POST'
        });
        
        const validateData = await validateResponse.json();
        
        if (!validateData.valid) {
            showValidationMessage(validateData.message || 'Invalid symbol', 'error');
            return;
        }
        
        // Add symbol
        const addResponse = await fetch(
            `${API_BASE}/watchlist/add?user_id=${USER_ID}&symbol=${encodeURIComponent(symbol)}`,
            { method: 'POST' }
        );
        
        if (!addResponse.ok) {
            const errorData = await addResponse.json();
            showValidationMessage(errorData.message || 'Failed to add symbol', 'error');
            return;
        }
        
        showValidationMessage(`${symbol} added successfully!`, 'success');
        elements.symbolInput.value = '';
        
        // Reload watchlist
        setTimeout(loadWatchlist, 500);
    } catch (error) {
        console.error('Error adding symbol:', error);
        showValidationMessage('Error adding symbol: ' + error.message, 'error');
    }
}

// Handle remove symbol
async function handleRemoveSymbol(symbol) {
    if (!confirm(`Are you sure you want to remove ${symbol} from your watchlist?`)) {
        return;
    }
    
    try {
        const response = await fetch(
            `${API_BASE}/watchlist/remove?user_id=${USER_ID}&symbol=${encodeURIComponent(symbol)}`,
            { method: 'POST' }
        );
        
        if (!response.ok) {
            const errorData = await response.json();
            showError(true, errorData.message || 'Failed to remove symbol');
            return;
        }
        
        // Reload watchlist
        loadWatchlist();
    } catch (error) {
        console.error('Error removing symbol:', error);
        showError(true, 'Error removing symbol: ' + error.message);
    }
}

// UI Helpers
function showLoading(show) {
    if (show) {
        elements.loadingState.classList.remove('hidden');
        elements.contentState.classList.add('hidden');
    } else {
        elements.loadingState.classList.add('hidden');
        elements.contentState.classList.remove('hidden');
    }
}

function showError(show, message = '') {
    if (show) {
        elements.errorState.classList.remove('hidden');
        elements.errorMessage.textContent = message;
    } else {
        elements.errorState.classList.add('hidden');
    }
}

function showValidationMessage(message, type) {
    elements.validationMessage.textContent = message;
    elements.validationMessage.className = `validation-message ${type}`;
    
    // Auto-hide success messages after 3 seconds
    if (type === 'success') {
        setTimeout(() => {
            elements.validationMessage.classList.add('hidden');
        }, 3000);
    }
}

// Formatting helpers
function formatPrice(price) {
    if (price === null || price === undefined) {
        return '<span class="unavailable">Price unavailable</span>';
    }
    return `$${parseFloat(price).toFixed(2)}`;
}

function formatDate(dateString) {
    if (!dateString) {
        return '<span class="unavailable">Not yet updated</span>';
    }
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        return '<span class="unavailable">Invalid date</span>';
    }
}

function formatFreshness(seconds) {
    if (seconds === null || seconds === undefined) {
        return '<span class="unavailable">Freshness unavailable</span>';
    }
    if (seconds < 60) {
        return `${seconds}s ago`;
    }
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) {
        return `${minutes}m ago`;
    }
    const hours = Math.floor(minutes / 60);
    if (hours < 24) {
        return `${hours}h ago`;
    }
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}