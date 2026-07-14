// Configuration
const API_BASE_URL = '/api/api';
const DASHBOARD_ENDPOINT = '/dashboard';
const USER_ID = 1; // Default demo user

// DOM Elements
const loadingState = document.getElementById('loadingState');
const errorState = document.getElementById('errorState');
const mainContent = document.getElementById('mainContent');
const errorMessage = document.getElementById('errorMessage');
const refreshBtn = document.getElementById('refreshBtn');
const retryBtn = document.getElementById('retryBtn');
const lastRefreshed = document.getElementById('lastRefreshed');

// Formatting utilities
function formatCurrency(value) {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

function formatPercent(value) {
    if (value === null || value === undefined) return 'N/A';
    return (value * 100).toFixed(2) + '%';
}

function formatNumber(value, decimals = 2) {
    if (value === null || value === undefined) return 'N/A';
    return parseFloat(value).toFixed(decimals);
}

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
        return 'N/A';
    }
}

function formatTimestamp(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch (e) {
        return 'N/A';
    }
}

function getValueClass(value) {
    if (value > 0) return 'positive';
    if (value < 0) return 'negative';
    return '';
}

// API calls
async function fetchDashboardData() {
    try {
        showLoading();
        const response = await fetch(`${API_BASE_URL}${DASHBOARD_ENDPOINT}/?user_id=${USER_ID}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        renderDashboard(data);
        hideError();
    } catch (error) {
        console.error('Error fetching dashboard:', error);
        showError(`Failed to load dashboard: ${error.message}`);
    }
}

// UI State Management
function showLoading() {
    loadingState.classList.remove('hidden');
    mainContent.classList.add('hidden');
    errorState.classList.add('hidden');
}

function hideLoading() {
    loadingState.classList.add('hidden');
}

function showError(message) {
    hideLoading();
    errorMessage.textContent = message;
    errorState.classList.remove('hidden');
    mainContent.classList.add('hidden');
}

function hideError() {
    errorState.classList.add('hidden');
}

function showContent() {
    hideLoading();
    mainContent.classList.remove('hidden');
}

// Rendering functions
function renderDashboard(data) {
    renderPortfolioSummary(data.portfolio_summary);
    renderTopOpportunities(data.top_opportunities || []);
    renderWatchlist(data.watchlist || []);
    renderOpenTrades(data.open_trades || []);
    renderRecentNews(data.recent_news || []);
    renderRiskSettings(data.risk_settings || {});
    updateLastRefreshed(data.timestamp);
    showContent();
}

function renderPortfolioSummary(summary) {
    document.getElementById('totalValue').textContent = formatCurrency(summary.total_value);
    document.getElementById('cash').textContent = formatCurrency(summary.cash);
    document.getElementById('positionsValue').textContent = formatCurrency(summary.positions_value);
    
    const openPLElement = document.getElementById('openPL');
    openPLElement.textContent = formatCurrency(summary.open_pl);
    openPLElement.className = 'card-value ' + getValueClass(summary.open_pl);
    
    const openPLPctElement = document.getElementById('openPLPct');
    openPLPctElement.textContent = formatPercent(summary.open_pl_pct);
    openPLPctElement.className = 'card-value ' + getValueClass(summary.open_pl_pct);
    
    document.getElementById('numOpenTrades').textContent = summary.num_open_trades || 0;
    document.getElementById('numOpenSignals').textContent = summary.num_open_signals || 0;
}

function renderTopOpportunities(opportunities) {
    const container = document.getElementById('opportunitiesContainer');
    
    if (!opportunities || opportunities.length === 0) {
        container.innerHTML = '<div class="empty-state">No opportunities available.</div>';
        return;
    }
    
    container.innerHTML = opportunities.slice(0, 5).map(opp => `
        <div class="opportunity-card">
            <div class="opportunity-header">
                <div>
                    <div class="opportunity-title">${escapeHtml(opp.symbol)}</div>
                    <div class="opportunity-symbol">${escapeHtml(opp.strategy_type)}</div>
                </div>
                <div class="opportunity-score">${formatNumber(opp.score, 1)}</div>
            </div>
            
            <div class="opportunity-status ${opp.status}">${opp.status}</div>
            
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
                <div class="detail-item">
                    <div class="detail-label">Created</div>
                    <div class="detail-value">${formatDate(opp.created_at)}</div>
                </div>
            </div>
            
            ${opp.reason ? `<div class="opportunity-reason">${escapeHtml(opp.reason)}</div>` : ''}
            
            ${opp.breakdown ? `
                <div class="opportunity-breakdown">
                    <div class="breakdown-item">
                        <div class="breakdown-label">Expiration</div>
                        <div class="breakdown-value">${escapeHtml(opp.breakdown.expiration || 'N/A')}</div>
                    </div>
                    <div class="breakdown-item">
                        <div class="breakdown-label">Strike</div>
                        <div class="breakdown-value">${formatCurrency(opp.breakdown.strike)}</div>
                    </div>
                    <div class="breakdown-item">
                        <div class="breakdown-label">Type</div>
                        <div class="breakdown-value">${escapeHtml(opp.breakdown.contract_type || 'N/A')}</div>
                    </div>
                    <div class="breakdown-item">
                        <div class="breakdown-label">Bid</div>
                        <div class="breakdown-value">${formatCurrency(opp.breakdown.bid)}</div>
                    </div>
                    <div class="breakdown-item">
                        <div class="breakdown-label">Ask</div>
                        <div class="breakdown-value">${formatCurrency(opp.breakdown.ask)}</div>
                    </div>
                    <div class="breakdown-item">
                        <div class="breakdown-label">Mid</div>
                        <div class="breakdown-value">${formatCurrency(opp.breakdown.mid)}</div>
                    </div>
                    <div class="breakdown-item">
                        <div class="breakdown-label">IV</div>
                        <div class="breakdown-value">${formatPercent(opp.breakdown.implied_volatility)}</div>
                    </div>
                    <div class="breakdown-item">
                        <div class="breakdown-label">Delta</div>
                        <div class="breakdown-value">${formatNumber(opp.breakdown.delta, 2)}</div>
                    </div>
                </div>
            ` : ''}
            
            <a href="/opportunities/${opp.signal_id}" class="opportunity-link">View Details →</a>
        </div>
    `).join('');
}

function renderWatchlist(watchlist) {
    const container = document.getElementById('watchlistContainer');
    
    if (!watchlist || watchlist.length === 0) {
        container.innerHTML = '<div class="empty-state">No watchlist items.</div>';
        return;
    }
    
    container.innerHTML = watchlist.map(item => `
        <div class="watchlist-item">
            <div class="watchlist-symbol">${escapeHtml(item.symbol)}</div>
            <div class="watchlist-detail">
                <div class="watchlist-label">Price</div>
                <div class="watchlist-value">${item.current_price !== null ? formatCurrency(item.current_price) : 'Price unavailable'}</div>
            </div>
            <div class="watchlist-detail">
                <div class="watchlist-label">Added</div>
                <div class="watchlist-value">${formatDate(item.added_at)}</div>
            </div>
            <div class="watchlist-detail">
                <div class="watchlist-label">Last Updated</div>
                <div class="watchlist-value">${item.last_updated !== null ? formatDate(item.last_updated) : 'Not yet updated'}</div>
            </div>
            <div class="watchlist-detail">
                <div class="watchlist-label">Freshness</div>
                <div class="watchlist-value">${item.data_freshness_seconds !== null ? item.data_freshness_seconds + 's ago' : 'Freshness unavailable'}</div>
            </div>
        </div>
    `).join('');
}

function renderOpenTrades(trades) {
    const container = document.getElementById('tradesContainer');
    
    if (!trades || trades.length === 0) {
        container.innerHTML = '<div class="empty-state">No open trades yet.</div>';
        return;
    }
    
    container.innerHTML = trades.map(trade => `
        <div class="trade-item">
            <div>${escapeHtml(trade.symbol)} - ${escapeHtml(trade.strategy_type)}</div>
            <div>Entry: ${formatCurrency(trade.entry_price)}</div>
            <div>Current: ${formatCurrency(trade.current_price)}</div>
            <div>P/L: ${formatCurrency(trade.pl)}</div>
        </div>
    `).join('');
}

function renderRecentNews(news) {
    const container = document.getElementById('newsContainer');
    
    if (!news || news.length === 0) {
        container.innerHTML = '<div class="empty-state">No recent news.</div>';
        return;
    }
    
    container.innerHTML = news.slice(0, 5).map(item => `
        <div class="news-item">
            <div class="news-title">${escapeHtml(item.title || 'Untitled')}</div>
            <div class="news-source">${escapeHtml(item.source || 'Unknown')} - ${formatDate(item.published_at)}</div>
        </div>
    `).join('');
}

function renderRiskSettings(settings) {
    const container = document.getElementById('riskContainer');
    
    let html = `
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
            <div class="risk-item">
                <div class="risk-item-label">Live Trading Approved</div>
                <div class="risk-item-value ${settings.live_trading_approved ? 'enabled' : 'disabled'}">
                    ${settings.live_trading_approved ? 'Yes' : 'No'}
                </div>
            </div>
        </div>
    `;
    
    if (settings.risk_levels_info && settings.risk_levels_info.length > 0) {
        html += '<div class="risk-levels">';
        html += settings.risk_levels_info.map(level => `
            <div class="risk-level-card">
                <div class="risk-level-name">${escapeHtml(level.level)}</div>
                <div class="risk-level-description">${escapeHtml(level.description)}</div>
                <div class="risk-level-detail">
                    <div class="risk-level-detail-label">Max Position Size</div>
                    <div class="risk-level-detail-value">${formatPercent(level.max_position_size_pct / 100)}</div>
                </div>
                <div class="risk-level-detail">
                    <div class="risk-level-detail-label">Max Loss Per Trade</div>
                    <div class="risk-level-detail-value">${formatPercent(level.max_loss_per_trade_pct / 100)}</div>
                </div>
                ${level.allowed_strategies ? `
                    <div class="risk-level-detail">
                        <div class="risk-level-detail-label">Allowed Strategies</div>
                        <div class="risk-level-detail-value">${escapeHtml(level.allowed_strategies.join(', '))}</div>
                    </div>
                ` : ''}
            </div>
        `).join('');
        html += '</div>';
    }
    
    container.innerHTML = html;
}

function updateLastRefreshed(timestamp) {
    lastRefreshed.textContent = `Last refreshed: ${formatTimestamp(timestamp)}`;
}

// Utility functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Event listeners
refreshBtn.addEventListener('click', fetchDashboardData);
retryBtn.addEventListener('click', fetchDashboardData);

// Initialize on page load
document.addEventListener('DOMContentLoaded', fetchDashboardData);
