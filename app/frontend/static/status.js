document.addEventListener('DOMContentLoaded', function() {
  const refreshBtn = document.getElementById('refresh-btn');
  const loadingEl = document.getElementById('loading');
  const errorEl = document.getElementById('error');
  const contentEl = document.getElementById('content');

  refreshBtn.addEventListener('click', fetchStatus);

  // Initial load
  fetchStatus();
});

function fetchStatus() {
  const loadingEl = document.getElementById('loading');
  const errorEl = document.getElementById('error');
  const contentEl = document.getElementById('content');
  const refreshBtn = document.getElementById('refresh-btn');

  // Show loading state
  loadingEl.style.display = 'flex';
  errorEl.style.display = 'none';
  contentEl.style.display = 'none';
  refreshBtn.disabled = true;

  fetch('/api/health')
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      // Handle both direct health response and wrapped response
      const healthData = data.data || data;

      // Validate required fields
      if (!healthData.service || !healthData.status) {
        throw new Error('Invalid health response format');
      }

      renderStatus(healthData);
      loadingEl.style.display = 'none';
      contentEl.style.display = 'block';
      refreshBtn.disabled = false;
    })
    .catch(error => {
      console.error('Error fetching status:', error);
      showError(error.message);
      loadingEl.style.display = 'none';
      refreshBtn.disabled = false;
    });
}

function renderStatus(healthData) {
  const serviceName = document.getElementById('service-name');
  const version = document.getElementById('version');
  const backendTimestamp = document.getElementById('backend-timestamp');
  const frontendTimestamp = document.getElementById('frontend-timestamp');
  const statusBadge = document.getElementById('status-badge');

  // Set service name
  serviceName.textContent = healthData.service || '—';

  // Set version
  version.textContent = healthData.version || '—';

  // Set backend timestamp
  if (healthData.timestamp) {
    backendTimestamp.textContent = formatDateTime(healthData.timestamp);
  } else {
    backendTimestamp.textContent = '—';
  }

  // Set frontend timestamp (current time)
  frontendTimestamp.textContent = formatDateTime(new Date().toISOString());

  // Set status badge
  const isHealthy = healthData.status === 'healthy';
  statusBadge.className = 'badge ' + (isHealthy ? 'badge-healthy' : 'badge-unhealthy');
  statusBadge.textContent = isHealthy ? 'Healthy' : 'Unhealthy';
}

function showError(message) {
  const errorEl = document.getElementById('error');
  const errorMessage = document.getElementById('error-message');
  const contentEl = document.getElementById('content');

  errorMessage.textContent = message || 'Failed to load system status. Please try again.';
  errorEl.style.display = 'flex';
  contentEl.style.display = 'none';
}

function formatDateTime(isoString) {
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) {
      return isoString;
    }
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    });
  } catch (e) {
    return isoString;
  }
}
