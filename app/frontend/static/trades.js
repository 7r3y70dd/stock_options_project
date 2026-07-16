// Trades Page JavaScript

let currentUserId = 1;
let tradesData = [];
let currentTradeForClose = null;

function el(id) {
  return document.getElementById(id);
}

function setDisplay(id, value) {
  const node = el(id);
  if (node) node.style.display = value;
}

document.addEventListener('DOMContentLoaded', function() {
  console.log('[trades.js] loaded');

  const userIdParam = new URLSearchParams(window.location.search).get('user_id');
  if (userIdParam) {
    currentUserId = parseInt(userIdParam, 10);
  }

  const refreshBtn = el('refresh-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', refreshTrades);
  } else {
    console.error('[trades.js] Missing #refresh-btn');
  }

  loadTrades();
});

async function refreshTrades() {
  showLoadingState();
  hideErrorState();

  try {
    const response = await fetch(`/api/api/dashboard/trades/mark-to-market?user_id=${currentUserId}`, {
      method: 'POST'
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Mark-to-market failed: HTTP ${response.status}: ${text.slice(0, 300)}`);
    }

    await loadTrades();
  } catch (error) {
    hideLoadingState();
    showErrorState(extractErrorMessage(error));
  }
}

async function loadTrades() {
  console.log('[trades.js] loading trades for user', currentUserId);

  showLoadingState();
  hideErrorState();
  hideEmptyState();
  hideTradesContent();

  try {
    const url = `/api/api/dashboard/trades/open-marked?user_id=${currentUserId}`;
    console.log('[trades.js] fetch', url);

    const response = await fetch(url, { cache: 'no-store' });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`HTTP ${response.status}: ${text.slice(0, 300)}`);
    }

    const result = await response.json();
    console.log('[trades.js] API result', result);

    tradesData =
      result.trades ||
      result.open_trades ||
      result.data?.trades ||
      result.data?.open_trades ||
      [];

    console.log('[trades.js] parsed trades count', tradesData.length);

    hideLoadingState();

    if (!Array.isArray(tradesData) || tradesData.length === 0) {
      showEmptyState();
      return;
    }

    renderTrades();
    showTradesContent();
  } catch (error) {
    console.error('[trades.js] load failed', error);
    hideLoadingState();
    showErrorState(extractErrorMessage(error));
  }
}

function renderTrades() {
  const tbody = el('trades-tbody');

  if (!tbody) {
    console.error('[trades.js] Missing #trades-tbody');
    showErrorState('Trades table body is missing from the page.');
    return;
  }

  tbody.innerHTML = '';

  tradesData.forEach(trade => {
    const tradeId = trade.trade_id || trade.id || 'N/A';
    const pl = firstDefined(trade.current_pl, trade.open_pl, trade.unrealized_pl);
    const plPct = firstDefined(trade.current_pl_pct, trade.open_pl_pct, trade.unrealized_pl_pct);
    const currentPrice = firstDefined(
      trade.current_price,
      trade.current_option_price,
      trade.mark_price
    );

    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${escapeHtml(tradeId)}</td>
      <td><strong>${escapeHtml(trade.symbol || 'N/A')}</strong></td>
      <td>${escapeHtml(formatStrategyType(trade.strategy_type))}</td>
      <td>${formatCurrency(trade.entry_price)}</td>
      <td>${formatCurrency(currentPrice)}</td>
      <td>${escapeHtml(trade.quantity || 'N/A')}</td>
      <td>${formatDate(trade.entry_date || trade.opened_at)}</td>
      <td class="${getPlClass(pl)}">${formatCurrency(pl)}</td>
      <td class="${getPlClass(plPct)}">${formatPercent(plPct)}</td>
      <td><span class="status-badge ${escapeHtml(trade.status || 'open')}">${escapeHtml(trade.status || 'open')}</span></td>
      <td>
        <div class="trade-actions">
          <a class="btn btn-secondary" href="/trades/${Number(tradeId) || 0}" title="View this trade">View</a>\n          <button class="btn-close-trade" onclick="openCloseTradeModal(${Number(tradeId) || 0}, '${escapeHtml(trade.symbol || '')}')" title="Close this trade">Close</button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}

function firstDefined(...values) {
  for (const value of values) {
    if (value !== null && value !== undefined) return value;
  }
  return null;
}

function formatStrategyType(strategyType) {
  if (!strategyType) return 'N/A';
  return String(strategyType)
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function getPlClass(value) {
  const n = Number(value);
  if (value === null || value === undefined || Number.isNaN(n)) return 'pl-neutral';
  return n > 0 ? 'pl-positive' : n < 0 ? 'pl-negative' : 'pl-neutral';
}

function formatCurrency(value) {
  const n = Number(value);
  if (value === null || value === undefined || Number.isNaN(n)) return 'Not available';

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(n);
}

function formatPercent(value) {
  const n = Number(value);
  if (value === null || value === undefined || Number.isNaN(n)) return 'Not available';

  // Backend may return decimal like -0.004 or percent-like value like -0.4.
  const pct = Math.abs(n) <= 1 ? n * 100 : n;
  const sign = pct > 0 ? '+' : '';
  return sign + pct.toFixed(2) + '%';
}

function formatDate(dateString) {
  if (!dateString) return 'Not available';

  try {
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return 'Invalid date';

    return date.toLocaleString('en-US', {
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

function escapeHtml(text) {
  if (text === null || text === undefined) return '';

  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };

  return String(text).replace(/[&<>"']/g, m => map[m]);
}

function extractErrorMessage(error) {
  if (error && error.message) return error.message;
  if (typeof error === 'string') return error;
  return 'Failed to load trades. Please try again.';
}

function showLoadingState() {
  setDisplay('loading-state', 'flex');
}

function hideLoadingState() {
  setDisplay('loading-state', 'none');
}

function showErrorState(message) {
  const errorDiv = el('error-state');
  const errorMessage = document.querySelector('.error-message') || el('error-message');

  if (errorMessage) {
    errorMessage.textContent = message;
  }

  if (errorDiv) {
    errorDiv.style.display = 'block';
  } else {
    alert(message);
  }
}

function hideErrorState() {
  setDisplay('error-state', 'none');
}

function showEmptyState() {
  setDisplay('empty-state', 'block');
}

function hideEmptyState() {
  setDisplay('empty-state', 'none');
}

function showTradesContent() {
  setDisplay('trades-content', 'block');
}

function hideTradesContent() {
  setDisplay('trades-content', 'none');
}

function openCloseTradeModal(tradeId, symbol) {
  currentTradeForClose = { tradeId, symbol };

  const modalTradeId = el('modal-trade-id');
  const modalSymbol = el('modal-symbol');
  const exitPrice = el('exit-price');
  const modal = el('close-trade-modal');

  if (modalTradeId) modalTradeId.textContent = tradeId;
  if (modalSymbol) modalSymbol.textContent = symbol;
  if (exitPrice) exitPrice.value = '';
  if (modal) modal.style.display = 'flex';
}

function closeModal() {
  setDisplay('close-trade-modal', 'none');
  currentTradeForClose = null;
}

async function confirmCloseTrade() {
  if (!currentTradeForClose) return;

  const exitPriceInput = el('exit-price');
  const exitPrice = parseFloat(exitPriceInput?.value);

  if (Number.isNaN(exitPrice) || exitPrice <= 0) {
    alert('Please enter a valid exit price.');
    return;
  }

  const confirmBtn = el('confirm-close-btn');
  if (confirmBtn) {
    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Closing...';
  }

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

    if (confirmBtn) {
      confirmBtn.disabled = false;
      confirmBtn.textContent = 'Close Trade';
    }
  }
}

window.addEventListener('click', function(event) {
  const modal = el('close-trade-modal');
  if (event.target === modal) {
    closeModal();
  }
});
