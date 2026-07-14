// Portfolio Page JavaScript

const API_BASE = '/api/api/dashboard';
const USER_ID = new URLSearchParams(window.location.search).get('user_id') || '1';

const elements = {
  loading: document.getElementById('loading'),
  error: document.getElementById('error'),
  errorMessage: document.getElementById('error-message'),
  content: document.getElementById('content'),
  refreshBtn: document.getElementById('refresh-btn'),
  totalValue: document.getElementById('total-value'),
  cash: document.getElementById('cash'),
  positionsValue: document.getElementById('positions-value'),
  openPL: document.getElementById('open-pl'),
  openPLPct: document.getElementById('open-pl-pct'),
  numOpenTrades: document.getElementById('num-open-trades'),
  numOpenSignals: document.getElementById('num-open-signals'),
  positionsContent: document.getElementById('positions-content')
};

// Event Listeners
if (elements.refreshBtn) {
  elements.refreshBtn.addEventListener('click', loadPortfolio);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', loadPortfolio);

/**
 * Load portfolio data from API
 */
async function loadPortfolio() {
  showLoading();
  hideError();

  try {
    const url = `${API_BASE}/portfolio?user_id=${encodeURIComponent(USER_ID)}`;
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    const data = result.data || result;

    renderPortfolio(data);
    showContent();
  } catch (error) {
    console.error('Error loading portfolio:', error);
    showError(error.message || 'Failed to load portfolio data');
  }
}

/**
 * Render portfolio data to the page
 */
function renderPortfolio(data) {
  if (!data) {
    showError('No portfolio data received');
    return;
  }

  // Render summary cards
  elements.totalValue.textContent = formatCurrency(data.total_value);
  elements.cash.textContent = formatCurrency(data.cash);
  elements.positionsValue.textContent = formatCurrency(data.positions_value);

  // Render P/L with color coding
  const openPL = data.open_pl;
  const openPLPct = data.open_pl_pct;

  elements.openPL.textContent = formatCurrency(openPL);
  elements.openPL.className = 'card-value ' + (openPL >= 0 ? 'positive' : 'negative');

  elements.openPLPct.textContent = formatPercent(openPLPct);
  elements.openPLPct.className = 'card-value ' + (openPLPct >= 0 ? 'positive' : 'negative');

  // Render trade stats
  elements.numOpenTrades.textContent = data.num_open_trades || 0;
  elements.numOpenSignals.textContent = data.num_open_signals || 0;

  // Render positions
  renderPositions(data);
}

/**
 * Render positions section
 */
function renderPositions(data) {
  const positionsValue = data.positions_value || 0;
  const numOpenTrades = data.num_open_trades || 0;

  if (positionsValue === 0 && numOpenTrades === 0) {
    elements.positionsContent.innerHTML = `
      <div class="empty-positions">
        <p>No open positions yet.</p>
        <p>Approve an opportunity as a paper trade to begin tracking a position.</p>
      </div>
    `;
  } else {
    // Placeholder for future positions table
    // When the backend provides positions array, render it here
    if (data.positions && Array.isArray(data.positions) && data.positions.length > 0) {
      renderPositionsTable(data.positions);
    } else {
      elements.positionsContent.innerHTML = `
        <div class="empty-positions">
          <p>No position details available.</p>
        </div>
      `;
    }
  }
}

/**
 * Render positions table (for future use when positions endpoint is available)
 */
function renderPositionsTable(positions) {
  const rows = positions.map(pos => `
    <tr>
      <td>${escapeHtml(pos.symbol || 'N/A')}</td>
      <td>${escapeHtml(pos.strategy_type || 'N/A')}</td>
      <td>${pos.quantity || 'N/A'}</td>
      <td>${formatCurrency(pos.entry_price)}</td>
      <td>${formatCurrency(pos.current_price)}</td>
      <td>${formatCurrency(pos.market_value)}</td>
      <td class="${(pos.open_pl || 0) >= 0 ? 'positive' : 'negative'}">${formatCurrency(pos.open_pl)}</td>
      <td class="${(pos.open_pl_pct || 0) >= 0 ? 'positive' : 'negative'}">${formatPercent(pos.open_pl_pct)}</td>
    </tr>
  `).join('');

  elements.positionsContent.innerHTML = `
    <table class="positions-table">
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Strategy</th>
          <th>Qty</th>
          <th>Entry Price</th>
          <th>Current Price</th>
          <th>Market Value</th>
          <th>Open P/L</th>
          <th>Open P/L %</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
      </tbody>
    </table>
  `;
}

/**
 * Format currency value
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
 * Format percentage value
 */
function formatPercent(value) {
  if (value === null || value === undefined) {
    return 'N/A';
  }
  return (value * 100).toFixed(2) + '%';
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text) {
  if (!text) return '';
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}

/**
 * Show loading state
 */
function showLoading() {
  if (elements.loading) elements.loading.style.display = 'flex';
  if (elements.error) elements.error.style.display = 'none';
  if (elements.content) elements.content.style.display = 'none';
}

/**
 * Show content
 */
function showContent() {
  if (elements.loading) elements.loading.style.display = 'none';
  if (elements.error) elements.error.style.display = 'none';
  if (elements.content) elements.content.style.display = 'block';
}

/**
 * Show error state
 */
function showError(message) {
  if (elements.loading) elements.loading.style.display = 'none';
  if (elements.error) elements.error.style.display = 'block';
  if (elements.content) elements.content.style.display = 'none';
  if (elements.errorMessage) {
    elements.errorMessage.textContent = message || 'An error occurred while loading portfolio data';
  }
}

/**
 * Hide error state
 */
function hideError() {
  if (elements.error) elements.error.style.display = 'none';
}
