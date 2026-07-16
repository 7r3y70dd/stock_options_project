// Dashboard Page JavaScript

const API_BASE = '/api/api/dashboard';
const USER_ID = new URLSearchParams(window.location.search).get('user_id') || '1';

const containers = {
  portfolio: document.getElementById('portfolio-cards'),
  opportunities: document.getElementById('opportunities-container'),
  watchlist: document.getElementById('watchlist-container'),
  trades: document.getElementById('trades-container'),
  news: document.getElementById('news-container'),
  risk: document.getElementById('risk-container')
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', loadDashboard);
} else {
  loadDashboard();
}

async function refreshDashboard() {
  await loadDashboard();
}

async function loadDashboard() {
  setLoading();

  try {
    const response = await fetch(`${API_BASE}/?user_id=${encodeURIComponent(USER_ID)}`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    renderPortfolio(data.portfolio_summary || {});
    renderOpportunities(data.top_opportunities || []);
    renderWatchlist(data.watchlist || []);
    renderTrades(data.open_trades || []);
    renderNews(data.recent_news || []);
    renderRisk(data.risk_settings || {});
  } catch (error) {
    console.error('Dashboard load failed:', error);
    showError(`Failed to load dashboard: ${error.message}`);
  }
}

function setLoading() {
  if (containers.portfolio) containers.portfolio.innerHTML = loadingText('Loading portfolio data...');
  if (containers.opportunities) containers.opportunities.innerHTML = loadingText('Loading opportunities...');
  if (containers.watchlist) containers.watchlist.innerHTML = loadingText('Loading watchlist...');
  if (containers.trades) containers.trades.innerHTML = loadingText('Loading trades...');
  if (containers.news) containers.news.innerHTML = loadingText('Loading news...');
  if (containers.risk) containers.risk.innerHTML = loadingText('Loading risk settings...');
}

function loadingText(message) {
  return `<div class="empty-state"><p class="empty-state-text">${escapeHtml(message)}</p></div>`;
}

function showError(message) {
  const html = `<div class="empty-state error-state"><p>${escapeHtml(message)}</p></div>`;
  Object.values(containers).forEach((container) => {
    if (container) container.innerHTML = html;
  });
}

function renderPortfolio(summary) {
  if (!containers.portfolio) return;

  containers.portfolio.innerHTML = `
    <div class="card">
      <div class="card-label">Total Value</div>
      <div class="card-value">${formatCurrency(summary.total_value)}</div>
    </div>
    <div class="card">
      <div class="card-label">Cash</div>
      <div class="card-value">${formatCurrency(summary.cash)}</div>
    </div>
    <div class="card">
      <div class="card-label">Positions Value</div>
      <div class="card-value">${formatCurrency(summary.positions_value)}</div>
    </div>
    <div class="card">
      <div class="card-label">Open P/L</div>
      <div class="card-value ${valueClass(summary.open_pl)}">${formatCurrency(summary.open_pl)}</div>
    </div>
    <div class="card">
      <div class="card-label">Open P/L %</div>
      <div class="card-value ${valueClass(summary.open_pl_pct)}">${formatPercent(summary.open_pl_pct)}</div>
    </div>
    <div class="card">
      <div class="card-label">Open Signals</div>
      <div class="card-value">${summary.num_open_signals || 0}</div>
    </div>
  `;
}

function renderOpportunities(opportunities) {
  if (!containers.opportunities) return;

  if (!opportunities.length) {
    containers.opportunities.innerHTML = `<div class="empty-state">No opportunities available.</div>`;
    return;
  }

  containers.opportunities.innerHTML = opportunities.slice(0, 5).map((opp) => `
    <div class="opportunity-card">
      <div class="opportunity-header">
        <div>
          <div class="opportunity-title">${escapeHtml(opp.symbol || 'N/A')}</div>
          <div class="opportunity-symbol">${escapeHtml(opp.strategy_type || 'N/A')}</div>
        </div>
        <div class="opportunity-score">${formatNumber(opp.score, 1)}</div>
      </div>

      <div class="opportunity-details">
        <div class="detail-item">
          <div class="detail-label">Expected Profit</div>
          <div class="detail-value">${formatCurrency(opp.expected_profit)}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">Max Loss</div>
          <div class="detail-value">${formatCurrency(opp.max_loss)}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">Probability</div>
          <div class="detail-value">${formatPercent(opp.probability_estimate)}</div>
        </div>
      </div>

      ${opp.reason ? `<div class="opportunity-reason">${escapeHtml(opp.reason)}</div>` : ''}
      ${opp.signal_id ? `<a class="opportunity-link" href="/opportunities/${opp.signal_id}">View Details →</a>` : ''}
    </div>
  `).join('');
}

function renderWatchlist(watchlist) {
  if (!containers.watchlist) return;

  if (!watchlist.length) {
    containers.watchlist.innerHTML = `<div class="empty-state">No watchlist items.</div>`;
    return;
  }

  containers.watchlist.innerHTML = watchlist.map((item) => `
    <div class="watchlist-item">
      <div class="watchlist-symbol">${escapeHtml(item.symbol || 'N/A')}</div>
      <div class="watchlist-detail">
        <span class="watchlist-label">Price:</span>
        <span class="watchlist-value">${formatCurrency(item.current_price)}</span>
      </div>
      <div class="watchlist-detail">
        <span class="watchlist-label">Added:</span>
        <span class="watchlist-value">${formatDate(item.added_at)}</span>
      </div>
    </div>
  `).join('');
}

function renderTrades(trades) {
  if (!containers.trades) return;

  if (!trades.length) {
    containers.trades.innerHTML = `<div class="empty-state">No open trades yet.</div>`;
    return;
  }

  containers.trades.innerHTML = trades.map((trade) => `
    <div class="trade-item">
      <strong>${escapeHtml(trade.symbol || 'N/A')}</strong>
      <div>${escapeHtml(trade.strategy_type || 'N/A')}</div>
      <div>P/L: ${formatCurrency(trade.open_pl || trade.pl)}</div>
    </div>
  `).join('');
}

function renderNews(news) {
  if (!containers.news) return;

  if (!news.length) {
    containers.news.innerHTML = `<div class="empty-state">No recent news.</div>`;
    return;
  }

  containers.news.innerHTML = news.slice(0, 5).map((item) => `
    <div class="news-item">
      <div class="news-title">${escapeHtml(item.title || 'Untitled')}</div>
      <div class="news-source">${escapeHtml(item.source || 'Unknown')} - ${formatDate(item.published_at)}</div>
    </div>
  `).join('');
}

function renderRisk(settings) {
  if (!containers.risk) return;

  containers.risk.innerHTML = `
    <div class="risk-summary">
      <div class="risk-item">
        <div class="risk-item-label">Risk Level</div>
        <div class="risk-item-value">${escapeHtml(settings.risk_level || 'N/A')}</div>
      </div>
      <div class="risk-item">
        <div class="risk-item-label">Paper Trading</div>
        <div class="risk-item-value ${settings.paper_trading_enabled ? 'enabled' : 'disabled'}">
          ${settings.paper_trading_enabled ? 'Enabled' : 'Disabled'}
        </div>
      </div>
      <div class="risk-item">
        <div class="risk-item-label">Live Trading</div>
        <div class="risk-item-value ${settings.live_trading_enabled ? 'enabled' : 'disabled'}">
          ${settings.live_trading_enabled ? 'Enabled' : 'Disabled'}
        </div>
      </div>
    </div>
  `;
}

function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(Number(value));
}

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
  return `${Number(value).toFixed(2)}%`;
}

function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
  return Number(value).toFixed(decimals);
}

function formatDate(value) {
  if (!value) return 'N/A';

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'N/A';

  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

function valueClass(value) {
  const number = Number(value || 0);
  if (number > 0) return 'positive';
  if (number < 0) return 'negative';
  return '';
}

function escapeHtml(value) {
  if (value === null || value === undefined) return '';

  const div = document.createElement('div');
  div.textContent = String(value);
  return div.innerHTML;
}
