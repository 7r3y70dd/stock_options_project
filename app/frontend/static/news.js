const userId = new URLSearchParams(window.location.search).get('user_id') || '1';

const elements = {
    loadingState: document.getElementById('loading-state'),
    errorState: document.getElementById('error-state'),
    emptyState: document.getElementById('empty-state'),
    newsContainer: document.getElementById('news-container'),
    errorText: document.getElementById('error-text'),
    refreshBtn: document.getElementById('refresh-btn')
};

function showLoading() {
    elements.loadingState.style.display = 'flex';
    elements.errorState.style.display = 'none';
    elements.emptyState.style.display = 'none';
    elements.newsContainer.innerHTML = '';
}

function showError(message) {
    elements.loadingState.style.display = 'none';
    elements.errorState.style.display = 'block';
    elements.emptyState.style.display = 'none';
    elements.newsContainer.innerHTML = '';
    elements.errorText.textContent = message || 'Failed to load news. Please try again.';
}

function showEmpty() {
    elements.loadingState.style.display = 'none';
    elements.errorState.style.display = 'none';
    elements.emptyState.style.display = 'block';
    elements.newsContainer.innerHTML = '';
}

function showNews(newsItems) {
    elements.loadingState.style.display = 'none';
    elements.errorState.style.display = 'none';
    elements.emptyState.style.display = 'none';
    elements.newsContainer.innerHTML = '';

    if (!newsItems || newsItems.length === 0) {
        showEmpty();
        return;
    }

    newsItems.forEach(item => {
        const card = createNewsCard(item);
        elements.newsContainer.appendChild(card);
    });
}

function createNewsCard(item) {
    const card = document.createElement('div');
    card.className = 'news-card';

    const symbol = item.symbol || 'N/A';
    const title = item.title || 'Untitled news item';
    const description = item.description || 'No description available';
    const source = item.source || 'Unknown source';
    const url = item.url || null;
    const publishedAt = item.published_at ? formatDate(item.published_at) : 'Date unavailable';
    const sentiment = item.sentiment || 'Sentiment unavailable';
    const sentimentScore = item.sentiment_score !== null && item.sentiment_score !== undefined ? item.sentiment_score : null;
    const eventType = item.event_type || null;

    const sentimentClass = getSentimentClass(sentiment);
    const eventTypeHtml = eventType ? `<span class="news-card-event-type">${escapeHtml(eventType)}</span>` : '';

    const titleHtml = url
        ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(title)}</a>`
        : escapeHtml(title);

    const sentimentScoreHtml = sentimentScore !== null
        ? `<span class="sentiment-score">(${sentimentScore.toFixed(2)})</span>`
        : '';

    const linkHtml = url
        ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" class="news-card-link">Read more →</a>`
        : '';

    card.innerHTML = `
        <div class="news-card-header">
            <span class="news-card-symbol">${escapeHtml(symbol)}</span>
            ${eventTypeHtml}
        </div>
        <h3 class="news-card-title">${titleHtml}</h3>
        <p class="news-card-description">${escapeHtml(description)}</p>
        <div class="news-card-meta">
            <div class="news-card-meta-item">
                <span class="news-card-meta-label">Source</span>
                <span class="news-card-source">${escapeHtml(source)}</span>
            </div>
            <div class="news-card-meta-item">
                <span class="news-card-meta-label">Published</span>
                <span class="news-card-date">${escapeHtml(publishedAt)}</span>
            </div>
            <div class="news-card-meta-item">
                <span class="news-card-meta-label">Sentiment</span>
                <span class="news-card-sentiment">
                    <span class="sentiment-badge ${sentimentClass}">${escapeHtml(sentiment)}</span>
                    ${sentimentScoreHtml}
                </span>
            </div>
        </div>
        ${linkHtml ? `<div class="news-card-footer">${linkHtml}</div>` : ''}
    `;

    return card;
}

function getSentimentClass(sentiment) {
    if (!sentiment) return 'sentiment-neutral';
    const lower = sentiment.toLowerCase();
    if (lower.includes('positive') || lower.includes('bullish')) return 'sentiment-positive';
    if (lower.includes('negative') || lower.includes('bearish')) return 'sentiment-negative';
    return 'sentiment-neutral';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return 'Date unavailable';
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return 'Date unavailable';
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return 'Date unavailable';
    }
}

async function fetchNews() {
    showLoading();
    try {
        const response = await fetch(`/api/api/dashboard/?user_id=${encodeURIComponent(userId)}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        const newsItems = data.recent_news || [];
        showNews(newsItems);
    } catch (error) {
        console.error('Error fetching news:', error);
        showError(`Failed to load news: ${error.message}`);
    }
}

elements.refreshBtn.addEventListener('click', fetchNews);

// Load news on page load
fetchNews();