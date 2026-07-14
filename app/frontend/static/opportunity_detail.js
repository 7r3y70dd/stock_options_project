/**
 * Opportunity Detail Page
 * Fetches and displays a single opportunity by signal_id
 */

const API_BASE = window.API_BASE || '/api/api';
const DEMO_USER_ID = window.DEMO_USER_ID || '1';

/**
 * Extract signal_id from URL path
 */
function getSignalIdFromUrl() {
  const match = window.location.pathname.match(/\/opportunities\/(\d+)/);
  return match ? match[1] : null;
}

/**
 * Format currency value
 */
function formatCurrency(value) {
  if (value === null || value === undefined) return 'N/A';
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
  if (value === null || value === undefined) return 'N/A';
  return (value * 100).toFixed(2) + '%';
}

/**
 * Format date
 */
function formatDate(dateString) {
  if (!dateString) return 'N/A';
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
    return dateString;
  }
}

/**
 * Format score with color
 */
function formatScore(score) {
  if (score === null || score === undefined) return 'N/A';
  return score.toFixed(2);
}

/**
 * Format strategy type for display
 */
function formatStrategyType(strategy) {
  const map = {
    'cash_secured_put': 'Cash Secured Put',
    'covered_call': 'Covered Call',
    'credit_spread': 'Credit Spread',
    'debit_spread': 'Debit Spread',
    'long_call_put': 'Long Call/Put'
  };
  return map[strategy] || strategy;
}

/**
 * Format status for display
 */
function formatStatus(status) {
  const map = {
    'pending': 'Pending',
    'active': 'Active',
    'closed': 'Closed'
  };
  return map[status] || status;
}

/**
 * Get status badge class
 */
function getStatusBadgeClass(status) {
  const map = {
    'pending': 'pending',
    'active': 'active',
    'closed': 'closed'
  };
  return map[status] || '';
}

/**
 * Format null/undefined values
 */
function formatValue(value) {
  if (value === null || value === undefined) return 'N/A';
  if (typeof value === 'number') return value.toString();
  return value.toString();
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Show loading state
 */
function showLoadingState() {
  document.getElementById('loading-state').style.display = 'flex';
  document.getElementById('detail-content').style.display = 'none';
  document.getElementById('error-state').style.display = 'none';
  document.getElementById('not-found-state').style.display = 'none';
}

/**
 * Show error state
 */
function showErrorState(message) {
  document.getElementById('error-message').textContent = message || 'Failed to load opportunity';
  document.getElementById('error-state').style.display = 'block';
  document.getElementById('loading-state').style.display = 'none';
  document.getElementById('detail-content').style.display = 'none';
  document.getElementById('not-found-state').style.display = 'none';
}

/**
 * Show not found state
 */
function showNotFoundState() {
  document.getElementById('not-found-state').style.display = 'block';
  document.getElementById('loading-state').style.display = 'none';
  document.getElementById('error-state').style.display = 'none';
  document.getElementById('detail-content').style.display = 'none';
}

/**
 * Show detail content
 */
function showDetailContent() {
  document.getElementById('detail-content').style.display = 'block';
  document.getElementById('loading-state').style.display = 'none';
  document.getElementById('error-state').style.display = 'none';
  document.getElementById('not-found-state').style.display = 'none';
}

/**
 * Extract error message from various error formats
 */
function extractErrorMessage(error) {
  if (error.message) return error.message;
  if (error.detail) return error.detail;
  if (typeof error === 'string') return error;
  return 'An unknown error occurred';
}

/**
 * Render opportunity detail
 */
function renderOpportunityDetail(opportunity) {
  const breakdown = opportunity.breakdown || {};

  // Header
  document.getElementById('symbol-header').textContent = escapeHtml(opportunity.symbol || 'N/A');
  document.getElementById('strategy-badge').textContent = formatStrategyType(opportunity.strategy_type);
  const statusBadge = document.getElementById('status-badge');
  statusBadge.textContent = formatStatus(opportunity.status);
  statusBadge.className = 'badge badge-status ' + getStatusBadgeClass(opportunity.status);
  document.getElementById('reason-text').textContent = escapeHtml(opportunity.reason || 'N/A');

  // Metrics
  document.getElementById('score-value').textContent = formatScore(opportunity.score);
  document.getElementById('probability-value').textContent = formatPercent(opportunity.probability_estimate);
  document.getElementById('profit-value').textContent = formatCurrency(opportunity.expected_profit);
  document.getElementById('loss-value').textContent = formatCurrency(opportunity.max_loss);

  // Contract details
  document.getElementById('provider-value').textContent = escapeHtml(breakdown.provider || 'N/A');
  document.getElementById('quote-value').textContent = formatCurrency(breakdown.quote);
  document.getElementById('expiration-value').textContent = escapeHtml(breakdown.expiration || 'N/A');
  document.getElementById('strike-value').textContent = formatCurrency(breakdown.strike);
  document.getElementById('contract-type-value').textContent = escapeHtml(breakdown.contract_type || 'N/A');
  document.getElementById('bid-value').textContent = formatCurrency(breakdown.bid);
  document.getElementById('ask-value').textContent = formatCurrency(breakdown.ask);
  document.getElementById('mid-value').textContent = formatCurrency(breakdown.mid);
  document.getElementById('iv-value').textContent = formatPercent(breakdown.implied_volatility);
  document.getElementById('delta-value').textContent = formatValue(breakdown.delta);

  // Liquidity
  document.getElementById('volume-value').textContent = formatValue(breakdown.volume);
  document.getElementById('open-interest-value').textContent = formatValue(breakdown.open_interest);
  
  // Calculate bid/ask spread
  let spreadText = 'N/A';
  if (breakdown.bid !== null && breakdown.bid !== undefined && breakdown.ask !== null && breakdown.ask !== undefined) {
    const spread = breakdown.ask - breakdown.bid;
    const spreadPct = breakdown.mid && breakdown.mid > 0 ? (spread / breakdown.mid * 100).toFixed(2) : 'N/A';
    spreadText = formatCurrency(spread) + (spreadPct !== 'N/A' ? ` (${spreadPct}%)` : '');
  }
  document.getElementById('spread-value').textContent = spreadText;

  // Scoring
  document.getElementById('sentiment-value').textContent = formatValue(breakdown.sentiment_score);
  document.getElementById('scoring-note-value').textContent = escapeHtml(breakdown.scoring_note || 'N/A');
  document.getElementById('full-reason-value').textContent = escapeHtml(opportunity.reason || 'N/A');

  // Metadata
  document.getElementById('signal-id-value').textContent = formatValue(opportunity.signal_id);
  document.getElementById('created-at-value').textContent = formatDate(opportunity.created_at);

  // Check if paper-trade endpoint exists (we'll try to call it)
  const paperTradeBtn = document.getElementById('paper-trade-btn');
  paperTradeBtn.style.display = 'block';
}

/**
 * Load opportunity detail by signal_id
 */
async function loadOpportunityDetail() {
  const signalId = getSignalIdFromUrl();
  if (!signalId) {
    showErrorState('Invalid opportunity ID');
    return;
  }

  showLoadingState();

  try {
    // Fetch opportunities list and find the matching one
    const response = await fetch(
      `${API_BASE}/dashboard/opportunities?user_id=${DEMO_USER_ID}&limit=100`
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const opportunities = data.opportunities || [];
    const opportunity = opportunities.find(o => o.signal_id === parseInt(signalId));

    if (!opportunity) {
      showNotFoundState();
      return;
    }

    renderOpportunityDetail(opportunity);
    showDetailContent();
  } catch (error) {
    console.error('Error loading opportunity:', error);
    showErrorState(extractErrorMessage(error));
  }
}

/**
 * Execute paper trade action
 */
async function executePaperTrade() {
  const signalId = getSignalIdFromUrl();
  if (!signalId) {
    showPaperTradeStatus('Invalid opportunity ID', 'error');
    return;
  }

  const btn = document.getElementById('paper-trade-btn');
  const statusDiv = document.getElementById('paper-trade-status');

  btn.disabled = true;
  showPaperTradeStatus('Processing...', 'loading');

  try {
    const response = await fetch(
      `${API_BASE}/dashboard/signals/${signalId}/paper-trade?user_id=${DEMO_USER_ID}&quantity=1`,
      { method: 'POST' }
    );

    const data = await response.json();

    if (!response.ok) {
      const errorMsg = extractErrorMessage(data);
      showPaperTradeStatus(`Error: ${errorMsg}`, 'error');
      btn.disabled = false;
      return;
    }

    showPaperTradeStatus('✓ Paper trade approved successfully', 'success');
    btn.disabled = true;
  } catch (error) {
    console.error('Error executing paper trade:', error);
    showPaperTradeStatus(`Error: ${extractErrorMessage(error)}`, 'error');
    btn.disabled = false;
  }
}

/**
 * Show paper trade status message
 */
function showPaperTradeStatus(message, type) {
  const statusDiv = document.getElementById('paper-trade-status');
  statusDiv.textContent = message;
  statusDiv.className = `paper-trade-status ${type}`;
  statusDiv.style.display = 'flex';
}

/**
 * Initialize page
 */
function initOpportunityDetailPage() {
  loadOpportunityDetail();
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initOpportunityDetailPage);
} else {
  initOpportunityDetailPage();
}
