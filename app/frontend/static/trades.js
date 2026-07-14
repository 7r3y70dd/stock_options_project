// Trades Page JavaScript

let currentUserId = 1;
let tradesData = [];
let currentTradeForClose = null;

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
  const userIdParam = new URLSearchParams(window.location.search).get('user_id');
  if (userIdParam) {
    currentUserId = parseInt(userIdParam);
  }

  document.getElementById('refresh-btn').addEventListener('click', loadTrades);
  loadTrades();
});

// Load trades data
async function loadTrades() {
  showLoadingState();
  hideErrorState();
  hideEmptyState();
  hideTradesContent();

  try {
    const response = await fetch(`/api/api/dashboard/?user_id=${currentUserId}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const result = await response.json();
    const data = result.data || result;

    tradesData = data.open_trades || [];

    hideLoadingState();

    if (tradesData.length === 0) {
      showEmptyState();
    } else {
      renderTrades();
      showTradesContent();
    }
  } catch (error) {
    hideLoadingState();
    showErrorState(extractErrorMessage(error));
  }
}

// Render trades table
function renderTrades() {
  const tbody = document.getElementById('trades-tbody');
  tbody.innerHTML = '';

  tradesData.forEach(trade => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${escapeHtml(trade.trade_id || 'N/A')}</td>
      <td><strong>${escapeHtml(trade.symbol || 'N/A')}</strong></td>
      <td>${escapeHtml(formatStrategyType(trade.strategy_type))}</td>
      <td>${formatCurrency(trade.entry_price)}</td>
      <td>${formatCurrency(trade.current_price)}</td>
      <td>${trade.quantity || 'N/A'}</td>
      <td>${formatDate(trade.entry_date)}</td>
      <td class="${getPlClass(trade.current_pl)}">${formatCurrency(trade.current_pl)}</td>
      <td class="${getPlClass(trade.current_pl_pct)}">${formatPercent(trade.current_pl_pct)}</td>
      <td><span class="status-badge ${trade.status || 'open'}">${escapeHtml(trade.status || 'open')}</span></td>
      <td>
        <div class="trade-actions">
          <button class="btn-close-trade" onclick="openCloseTradeModal(${trade.trade_id}, '${escapeHtml(trade.symbol)}')" title="Close this trade">Close</button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}

// Format strategy type for display
function formatStrategyType(strategyType) {
  if (!strategyType) return 'N/A';
  return strategyType
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// Get CSS class for P/L display
function getPlClass(value) {
  if (value === null || value === undefined) return 'pl-neutral';
  if (typeof value === 'number') {
    return value > 0 ? 'pl-positive' : value < 0 ? 'pl-negative' : 'pl-neutral';
  }
  return 'pl-neutral';
}

// Format currency
function formatCurrency(value) {
  if (value === null || value === undefined) return 'Not available';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value);
}

// Format percentage
function formatPercent(value) {
  if (value === null || value === undefined) return 'Not available';
  const sign = value > 0 ? '+' : '';
  return sign + value.toFixed(2) + '%';
}

// Format date
function formatDate(dateString) {
  if (!dateString) return 'Not available';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (e) {
    return 'Invalid date';
  }
}

// Escape HTML to prevent XSS
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

// Extract error message from various error formats
function extractErrorMessage(error) {
  if (error.message) return error.message;
  if (typeof error === 'string') return error;
  return 'Failed to load trades. Please try again.';
}

// UI State Management
function showLoadingState() {
  document.getElementById('loading-state').style.display = 'flex';
}

function hideLoadingState() {
  document.getElementById('loading-state').style.display = 'none';
}

function showErrorState(message) {
  const errorDiv = document.getElementById('error-state');
  document.querySelector('.error-message').textContent = message;
  errorDiv.style.display = 'block';
}

function hideErrorState() {
  document.getElementById('error-state').style.display = 'none';
}

function showEmptyState() {
  document.getElementById('empty-state').style.display = 'block';
}

function hideEmptyState() {
  document.getElementById('empty-state').style.display = 'none';
}

function showTradesContent() {
  document.getElementById('trades-content').style.display = 'block';
}

function hideTradesContent() {
  document.getElementById('trades-content').style.display = 'none';
}

// Close Trade Modal
function openCloseTradeModal(tradeId, symbol) {
  currentTradeForClose = { tradeId, symbol };
  document.getElementById('modal-trade-id').textContent = tradeId;
  document.getElementById('modal-symbol').textContent = symbol;
  document.getElementById('exit-price').value = '';
  document.getElementById('close-trade-modal').style.display = 'flex';
}

function closeModal() {
  document.getElementById('close-trade-modal').style.display = 'none';
  currentTradeForClose = null;
}

async function confirmCloseTrade() {
  if (!currentTradeForClose) return;

  const exitPrice = parseFloat(document.getElementById('exit-price').value);
  if (isNaN(exitPrice) || exitPrice <= 0) {
    alert('Please enter a valid exit price.');
    return;
  }

  const confirmBtn = document.getElementById('confirm-close-btn');
  confirmBtn.disabled = true;
  confirmBtn.textContent = 'Closing...';

  try {
    const response = await fetch(
      `/api/api/dashboard/trades/${currentTradeForClose.tradeId}/close?user_id=${currentUserId}&exit_price=${exitPrice}`,
      { method: 'POST' }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }

    closeModal();
    alert('Trade closed successfully!');
    loadTrades();
  } catch (error) {
    alert('Failed to close trade: ' + extractErrorMessage(error));
    confirmBtn.disabled = false;
    confirmBtn.textContent = 'Close Trade';
  }
}

// Close modal when clicking outside
window.addEventListener('click', function(event) {
  const modal = document.getElementById('close-trade-modal');
  if (event.target === modal) {
    closeModal();
  }
});
