let currentRiskSettings = null;
let pendingRiskLevel = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  loadRiskSettings();
  document.getElementById('refreshBtn').addEventListener('click', loadRiskSettings);
});

async function loadRiskSettings() {
  showLoadingState();
  hideErrorState();
  hideContentArea();

  try {
    const riskSettings = await fetchRiskSettings();
    currentRiskSettings = riskSettings;
    renderRiskSettings(riskSettings);
    showContentArea();
  } catch (error) {
    showErrorState(error.message);
  }
}

async function fetchRiskSettings() {
  const userId = new URLSearchParams(window.location.search).get('user_id') || '1';

  // Try standalone endpoint first
  try {
    const response = await fetch(`/api/api/dashboard/risk-settings?user_id=${userId}`);
    if (response.ok) {
      const data = await response.json();
      return extractRiskSettings(data);
    }
    if (response.status === 404) {
      throw new Error('Standalone endpoint not found, trying fallback...');
    }
    throw new Error(`HTTP ${response.status}`);
  } catch (standaloneError) {
    // Fallback to full dashboard
    try {
      const response = await fetch(`/api/api/dashboard/?user_id=${userId}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      if (!data.risk_settings) {
        throw new Error('Risk settings not found in dashboard response');
      }
      return extractRiskSettings(data.risk_settings);
    } catch (fallbackError) {
      throw new Error('Failed to load risk settings from both endpoints');
    }
  }
}

function extractRiskSettings(data) {
  // Handle both direct risk settings and wrapped response
  const settings = data.data || data;

  return {
    risk_level: settings.risk_level || 'unknown',
    paper_trading_enabled: settings.paper_trading_enabled !== false,
    live_trading_enabled: settings.live_trading_enabled === true,
    live_trading_approved: settings.live_trading_approved === true,
    risk_levels_info: Array.isArray(settings.risk_levels_info) ? settings.risk_levels_info : []
  };
}

function renderRiskSettings(settings) {
  renderCurrentSettings(settings);
  renderRiskLevelButtons(settings);
  renderRiskLevelDetails(settings);
}

function renderCurrentSettings(settings) {
  const riskLevelEl = document.getElementById('currentRiskLevel');
  riskLevelEl.textContent = formatRiskLevel(settings.risk_level);
  riskLevelEl.className = `setting-value risk-level-badge ${settings.risk_level}`;

  document.getElementById('paperTradingStatus').textContent = formatBoolean(settings.paper_trading_enabled);
  document.getElementById('liveTradingStatus').textContent = formatBoolean(settings.live_trading_enabled);
  document.getElementById('liveApprovedStatus').textContent = formatBoolean(settings.live_trading_approved);
}

function renderRiskLevelButtons(settings) {
  const container = document.getElementById('riskLevelButtons');
  container.innerHTML = '';

  const levels = ['low', 'medium', 'high'];
  levels.forEach(level => {
    const btn = document.createElement('button');
    btn.className = `risk-level-btn ${level}`;
    if (level === settings.risk_level) {
      btn.classList.add('active');
    }
    btn.textContent = formatRiskLevel(level);
    btn.addEventListener('click', () => selectRiskLevel(level, settings));
    container.appendChild(btn);
  });
}

function selectRiskLevel(level, settings) {
  if (level === settings.risk_level) {
    return; // Already selected
  }

  // Check if confirmation is required
  const levelInfo = settings.risk_levels_info.find(info => info.level === level);
  if (levelInfo && levelInfo.requires_confirmation) {
    showConfirmationPrompt(level, levelInfo);
  } else {
    updateRiskLevel(level);
  }
}

function showConfirmationPrompt(level, levelInfo) {
  pendingRiskLevel = level;
  const prompt = document.getElementById('confirmationPrompt');
  const message = document.getElementById('confirmationMessage');
  message.textContent = `Changing to ${formatRiskLevel(level)} risk level requires confirmation. This level allows higher-risk strategies. Are you sure?`;
  prompt.style.display = 'block';

  document.getElementById('confirmBtn').onclick = () => {
    updateRiskLevel(level);
    prompt.style.display = 'none';
  };

  document.getElementById('cancelBtn').onclick = () => {
    pendingRiskLevel = null;
    prompt.style.display = 'none';
  };
}

async function updateRiskLevel(level) {
  const userId = new URLSearchParams(window.location.search).get('user_id') || '1';
  const statusEl = document.getElementById('updateStatus');
  const confirmed = level === 'high' ? 'true' : 'false';

  statusEl.className = 'update-status loading';
  statusEl.textContent = 'Updating risk level...';
  statusEl.style.display = 'block';

  try {
    const response = await fetch(
      `/api/api/dashboard/risk-settings/update?user_id=${userId}&risk_level=${level}&confirmed=${confirmed}`,
      { method: 'POST' }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMsg = errorData.detail || errorData.message || `HTTP ${response.status}`;
      throw new Error(errorMsg);
    }

    statusEl.className = 'update-status success';
    statusEl.textContent = `✓ Risk level updated to ${formatRiskLevel(level)}`;

    // Reload settings after a short delay
    setTimeout(() => {
      loadRiskSettings();
    }, 1500);
  } catch (error) {
    statusEl.className = 'update-status error';
    statusEl.textContent = `✗ Failed to update: ${error.message}`;
  }
}

function renderRiskLevelDetails(settings) {
  const container = document.getElementById('riskLevelDetails');

  if (!settings.risk_levels_info || settings.risk_levels_info.length === 0) {
    container.innerHTML = '<div class="empty-state"><p>Risk level details are unavailable.</p></div>';
    return;
  }

  container.innerHTML = '';
  settings.risk_levels_info.forEach(levelInfo => {
    const card = createRiskLevelCard(levelInfo);
    container.appendChild(card);
  });
}

function createRiskLevelCard(levelInfo) {
  const card = document.createElement('div');
  card.className = `risk-level-card ${levelInfo.level}`;

  const title = document.createElement('h3');
  title.textContent = formatRiskLevel(levelInfo.level);
  card.appendChild(title);

  if (levelInfo.description) {
    const desc = document.createElement('p');
    desc.className = 'risk-level-description';
    desc.textContent = levelInfo.description;
    card.appendChild(desc);
  }

  const list = document.createElement('ul');
  list.className = 'risk-level-details-list';

  // Max position size
  if (levelInfo.max_position_size_pct !== null && levelInfo.max_position_size_pct !== undefined) {
    const li = document.createElement('li');
    li.innerHTML = `<span class="detail-label">Max Position Size:</span><span class="detail-value">${formatPercentage(levelInfo.max_position_size_pct)}</span>`;
    list.appendChild(li);
  }

  // Max loss per trade
  if (levelInfo.max_loss_per_trade_pct !== null && levelInfo.max_loss_per_trade_pct !== undefined) {
    const li = document.createElement('li');
    li.innerHTML = `<span class="detail-label">Max Loss Per Trade:</span><span class="detail-value">${formatPercentage(levelInfo.max_loss_per_trade_pct)}</span>`;
    list.appendChild(li);
  }

  // Allowed strategies
  if (levelInfo.allowed_strategies && levelInfo.allowed_strategies.length > 0) {
    const li = document.createElement('li');
    const strategiesHtml = levelInfo.allowed_strategies
      .map(s => `<span class="strategy-badge">${formatStrategyName(s)}</span>`)
      .join('');
    li.innerHTML = `<span class="detail-label">Allowed Strategies:</span><div class="strategies-list">${strategiesHtml}</div>`;
    list.appendChild(li);
  }

  // Requires confirmation
  if (levelInfo.requires_confirmation) {
    const li = document.createElement('li');
    li.innerHTML = '<span class="confirmation-badge">⚠ Requires Confirmation</span>';
    list.appendChild(li);
  }

  card.appendChild(list);
  return card;
}

// UI State Management
function showLoadingState() {
  document.getElementById('loadingState').style.display = 'flex';
}

function hideLoadingState() {
  document.getElementById('loadingState').style.display = 'none';
}

function showErrorState(message) {
  const errorEl = document.getElementById('errorState');
  errorEl.querySelector('.error-message').textContent = message || 'Failed to load risk settings';
  errorEl.style.display = 'block';
  hideLoadingState();
}

function hideErrorState() {
  document.getElementById('errorState').style.display = 'none';
}

function showContentArea() {
  document.getElementById('contentArea').style.display = 'block';
  hideLoadingState();
}

function hideContentArea() {
  document.getElementById('contentArea').style.display = 'none';
}

// Formatting helpers (using shared formatters if available, with fallbacks)
function formatRiskLevel(level) {
  if (!level) return 'Unknown';
  return level.charAt(0).toUpperCase() + level.slice(1);
}

function formatBoolean(value) {
  return value ? '✓ Enabled' : '✗ Disabled';
}

function formatPercentage(value) {
  if (value === null || value === undefined) return 'N/A';
  return `${value}%`;
}

function formatStrategyName(strategy) {
  if (!strategy) return 'Unknown';
  return strategy
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
