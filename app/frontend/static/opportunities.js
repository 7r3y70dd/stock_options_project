/**
 * Opportunities page JavaScript
 * Fetches, filters, sorts, and renders opportunities data
 */

const OPPORTUNITIES_API_URL = '/api/api/dashboard/opportunities';
const USER_ID = window.APP_USER_ID || '1';
const LIMIT = 100;

let allOpportunities = [];
let filteredOpportunities = [];

/**
 * Initialize the opportunities page
 */
function initOpportunitiesPage() {
  setupEventListeners();
  loadOpportunities();
}

/**
 * Setup event listeners for filters, sort, and refresh
 */
function setupEventListeners() {
  document.getElementById('refresh-btn').addEventListener('click', loadOpportunities);
  document.getElementById('retry-btn').addEventListener('click', loadOpportunities);
  
  document.getElementById('filter-symbol').addEventListener('input', applyFiltersAndSort);
  document.getElementById('filter-strategy').addEventListener('change', applyFiltersAndSort);
  document.getElementById('filter-status').addEventListener('change', applyFiltersAndSort);
  document.getElementById('filter-contract').addEventListener('change', applyFiltersAndSort);
  document.getElementById('sort-by').addEventListener('change', applyFiltersAndSort);
}

/**
 * Load opportunities from API
 */
async function loadOpportunities() {
  showLoadingState();
  hideErrorState();
  
  try {
    const url = `${OPPORTUNITIES_API_URL}?user_id=${USER_ID}&limit=${LIMIT}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    // Handle both wrapped and unwrapped responses
    const opportunities = data.opportunities || data.data?.opportunities || [];
    allOpportunities = Array.isArray(opportunities) ? opportunities : [];
    
    applyFiltersAndSort();
    hideLoadingState();
  } catch (error) {
    console.error('Error loading opportunities:', error);
    showErrorState(extractErrorMessage(error));
    hideLoadingState();
  }
}

/**
 * Apply filters and sorting to opportunities
 */
function applyFiltersAndSort() {
  // Get filter values
  const symbolFilter = document.getElementById('filter-symbol').value.toUpperCase();
  const strategyFilter = document.getElementById('filter-strategy').value;
  const statusFilter = document.getElementById('filter-status').value;
  const contractFilter = document.getElementById('filter-contract').value;
  const sortBy = document.getElementById('sort-by').value;
  
  // Filter opportunities
  filteredOpportunities = allOpportunities.filter(opp => {
    const symbol = (opp.symbol || '').toUpperCase();
    const strategy = opp.strategy_type || '';
    const status = opp.status || '';
    const contractType = (opp.breakdown?.contract_type || '').toLowerCase();
    
    if (symbolFilter && !symbol.includes(symbolFilter)) return false;
    if (strategyFilter && strategy !== strategyFilter) return false;
    if (statusFilter && status !== statusFilter) return false;
    if (contractFilter && contractType !== contractFilter) return false;
    
    return true;
  });
  
  // Sort opportunities
  sortOpportunities(sortBy);
  
  // Render
  renderOpportunities();
}

/**
 * Sort opportunities by selected criteria
 */
function sortOpportunities(sortBy) {
  const [field, direction] = sortBy.split('-');
  const isAsc = direction === 'asc';
  
  filteredOpportunities.sort((a, b) => {
    let aVal, bVal;
    
    switch (field) {
      case 'score':
        aVal = a.score || 0;
        bVal = b.score || 0;
        break;
      case 'profit':
        aVal = a.expected_profit || 0;
        bVal = b.expected_profit || 0;
        break;
      case 'loss':
        aVal = a.max_loss || 0;
        bVal = b.max_loss || 0;
        break;
      case 'probability':
        aVal = a.probability_estimate || 0;
        bVal = b.probability_estimate || 0;
        break;
      case 'date':
        aVal = new Date(a.created_at || 0).getTime();
        bVal = new Date(b.created_at || 0).getTime();
        break;
      default:
        return 0;
    }
    
    if (aVal < bVal) return isAsc ? -1 : 1;
    if (aVal > bVal) return isAsc ? 1 : -1;
    return 0;
  });
}

/**
 * Render opportunities to the table
 */
function renderOpportunities() {
  const tbody = document.getElementById('opportunities-tbody');
  const countDisplay = document.getElementById('count-display');
  const tableContainer = document.getElementById('opportunities-table-container');
  const emptyState = document.getElementById('empty-state');
  
  countDisplay.textContent = `${filteredOpportunities.length} opportunity(ies)`;
  
  if (filteredOpportunities.length === 0) {
    tableContainer.style.display = 'none';
    emptyState.style.display = 'block';
    return;
  }
  
  tbody.innerHTML = '';
  
  filteredOpportunities.forEach(opp => {
    const row = createOpportunityRow(opp);
    tbody.appendChild(row);
  });
  
  tableContainer.style.display = 'block';
  emptyState.style.display = 'none';
}

/**
 * Create a table row for an opportunity
 */
function createOpportunityRow(opp) {
  const row = document.createElement('tr');
  const breakdown = opp.breakdown || {};
  
  const signalId = opp.signal_id || 'N/A';
  const symbol = opp.symbol || 'N/A';
  const strategy = formatStrategyType(opp.strategy_type || 'N/A');
  const score = formatScore(opp.score);
  const expectedProfit = formatCurrency(opp.expected_profit);
  const maxLoss = formatCurrency(opp.max_loss);
  const probability = formatPercentage(opp.probability_estimate * 100);
  const status = formatStatus(opp.status || 'N/A');
  const createdAt = formatDate(opp.created_at);
  const expiration = formatDate(breakdown.expiration);
  const strike = breakdown.strike ? `$${breakdown.strike.toFixed(2)}` : 'N/A';
  const contractType = breakdown.contract_type || 'N/A';
  const bid = breakdown.bid ? breakdown.bid.toFixed(2) : 'N/A';
  const mid = breakdown.mid ? breakdown.mid.toFixed(2) : 'N/A';
  const ask = breakdown.ask ? breakdown.ask.toFixed(2) : 'N/A';
  const volume = breakdown.volume ? breakdown.volume.toLocaleString() : 'N/A';
  const openInterest = breakdown.open_interest ? breakdown.open_interest.toLocaleString() : 'N/A';
  
  row.innerHTML = `
    <td><strong>${escapeHtml(symbol)}</strong></td>
    <td>${escapeHtml(strategy)}</td>
    <td><span class="score-badge">${score}</span></td>
    <td class="text-right">${expectedProfit}</td>
    <td class="text-right">${maxLoss}</td>
    <td class="text-right">${probability}</td>
    <td><span class="status-badge status-${opp.status}">${escapeHtml(status)}</span></td>
    <td>${createdAt}</td>
    <td>${expiration}</td>
    <td class="text-right">${strike}</td>
    <td>${escapeHtml(contractType)}</td>
    <td class="text-right"><small>${bid} / ${mid} / ${ask}</small></td>
    <td class="text-right">${volume}</td>
    <td class="text-right">${openInterest}</td>
    <td><a href="/opportunities/${signalId}" class="btn btn-sm btn-link">View</a></td>
  `;
  
  return row;
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
 * Show loading state
 */
function showLoadingState() {
  document.getElementById('loading-state').style.display = 'block';
  document.getElementById('opportunities-table-container').style.display = 'none';
  document.getElementById('empty-state').style.display = 'none';
}

/**
 * Hide loading state
 */
function hideLoadingState() {
  document.getElementById('loading-state').style.display = 'none';
}

/**
 * Show error state
 */
function showErrorState(message) {
  document.getElementById('error-message').textContent = message || 'Failed to load opportunities';
  document.getElementById('error-state').style.display = 'block';
  document.getElementById('opportunities-table-container').style.display = 'none';
  document.getElementById('empty-state').style.display = 'none';
}

/**
 * Hide error state
 */
function hideErrorState() {
  document.getElementById('error-state').style.display = 'none';
}

/**
 * Extract error message from various error formats
 */
function extractErrorMessage(error) {
  if (error.message) return error.message;
  if (typeof error === 'string') return error;
  return 'An unknown error occurred';
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

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initOpportunitiesPage);
} else {
  initOpportunitiesPage();
}


// --- analyze watchlist from opportunities ---
(function () {
  async function analyzeWatchlistFromOpportunities() {
    const btn = document.getElementById('analyze-opportunities-btn');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Analyzing...';
    }

    try {
      const response = await fetch('/api/api/dashboard/watchlist/analyze?user_id=1', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({})
      });

      const data = await response.json();

      if (!response.ok || data.success === false) {
        throw new Error(data.detail || data.stderr || 'Analyze failed');
      }

      alert(`Analyzed ${data.symbols_analyzed.length} symbols. Created about ${data.signals_created_estimate} new signals.`);

      if (typeof loadOpportunities === 'function') {
        loadOpportunities();
      } else {
        window.location.reload();
      }
    } catch (error) {
      alert(`Analyze Watchlist failed: ${error.message}`);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Analyze Watchlist';
      }
    }
  }

  function installAnalyzeButton() {
    if (document.getElementById('analyze-opportunities-btn')) return;

    const refresh = document.getElementById('refresh-btn');
    if (!refresh || !refresh.parentElement) return;

    const btn = document.createElement('button');
    btn.id = 'analyze-opportunities-btn';
    btn.className = 'btn btn-secondary';
    btn.textContent = 'Analyze Watchlist';
    btn.addEventListener('click', analyzeWatchlistFromOpportunities);

    refresh.parentElement.appendChild(btn);
  }

  document.addEventListener('DOMContentLoaded', installAnalyzeButton);
})();
