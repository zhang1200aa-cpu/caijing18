// ============ caijing18 主页 JavaScript ============

let currentPage = 1;
let currentTag = '';
let currentKeyword = '';
const PER_PAGE = 20;

// ======== 统计数据 ========
async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        if (data.success) {
            const totalEl = document.getElementById('totalCount');
            const todayEl = document.getElementById('todayCount');
            if (totalEl) totalEl.textContent = data.data.total;
            if (todayEl) todayEl.textContent = data.data.today;
        }
    } catch (e) { console.error('loadStats:', e); }
}

// ======== 标签 ========
async function loadTags() {
    try {
        const c = document.getElementById('tagFilter');
        if (!c) return;
        const res = await fetch('/api/tags');
        const data = await res.json();
        if (data.success) {
            c.innerHTML = '<button class="tag-btn active" onclick="filterByTag(\'\')">全部</button>';
            data.data.forEach(tag => {
                c.innerHTML += '<button class="tag-btn" onclick="filterByTag(\'' + tag.name + '\')">' + tag.name + ' (' + tag.count + ')</button>';
            });
        }
    } catch (e) { console.error('loadTags:', e); }
}

// ======== AI 总结卡片加载 ========
async function loadAllSummaries() {
    const summaries = ['today', 'yesterday', '3d', '1w'];
    for (const range of summaries) {
        loadSingleSummary(range);
    }
}

async function loadSingleSummary(range) {
    const bodyEl = document.getElementById('body-' + range);
    const metaEl = document.getElementById('meta-' + range);
    const timeEl = document.getElementById('time-' + range);
    if (!bodyEl) return;
    
    try {
        const endpointMap = {
            'today': '/api/summary/today',
            'yesterday': '/api/summary/yesterday',
            '3d': '/api/summary/3d',
            '1w': '/api/summary/1w'
        };
        const url = endpointMap[range];
        if (!url) return;
        
        const res = await fetch(url);
        const data = await res.json();
        
        if (data.success && data.data) {
            const summary = data.data;
            // 更新时间（generated_at 已是北京时间字符串）
            if (summary.generated_at && timeEl) {
                timeEl.textContent = summary.generated_at;
            }
            // 设置内容
            let html = summary.content
                .replace(/### /g, '<h3>').replace(/#### /g, '<h4>')
                .replace(/- /g, '<li>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>');
            html = html.replace(/<li>/g, '<ul><li>').replace(/<\/li>/g, '</li></ul>').replace(/<\/ul><ul>/g, '');
            bodyEl.innerHTML = html;
            if (metaEl) {
                metaEl.textContent = '📰 ' + (summary.news_count || '?') + ' 条新闻';
            }
        } else {
            bodyEl.innerHTML = '<div class="ai-summary-empty">暂无总结，点击刷新生成</div>';
        }
    } catch (e) {
        console.error('loadSummary ' + range + ':', e);
        bodyEl.innerHTML = '<div class="ai-summary-error">❌ 加载失败</div>';
    }
}

async function refreshSummary(range) {
    const endpointMap = {
        'today': '/api/summary/today',
        'yesterday': '/api/summary/yesterday',
        '3d': '/api/summary/3d',
        '1w': '/api/summary/1w'
    };
    const url = endpointMap[range];
    if (!url) return;
    
    const bodyEl = document.getElementById('body-' + range);
    if (!bodyEl) return;
    bodyEl.innerHTML = '<div class="ai-summary-loading">⏳ 生成中...</div>';
    
    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ force: true })
        });
        const data = await res.json();
        if (data.success && data.data) {
            loadSingleSummary(range);
        } else {
            bodyEl.innerHTML = '<div class="ai-summary-error">❌ ' + (data.message || '生成失败') + '</div>';
        }
    } catch (e) {
        console.error('refreshSummary ' + range + ':', e);
        bodyEl.innerHTML = '<div class="ai-summary-error">❌ 网络错误</div>';
    }
}

async function refreshAllSummaries() {
    const ranges = ['today', 'yesterday', '3d', '1w'];
    for (const range of ranges) {
        const bodyEl = document.getElementById('body-' + range);
        if (bodyEl) bodyEl.innerHTML = '<div class="ai-summary-loading">⏳ 生成中...</div>';
        const endpointMap = {
            'today': '/api/summary/today',
            'yesterday': '/api/summary/yesterday',
            '3d': '/api/summary/3d',
            '1w': '/api/summary/1w'
        };
        const url = endpointMap[range];
        if (!url) continue;
        try {
            await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ force: true })
            });
        } catch (e) {
            console.error('refreshAll ' + range + ':', e);
        }
    }
    // 全部请求完成后重新加载显示
    setTimeout(loadAllSummaries, 1000);
}

// ======== 搜索结果总结弹窗 ========
function openSummaryModal() {
    document.getElementById('searchSummaryModal').style.display = 'block';
    document.getElementById('searchSummaryResult').innerHTML = '';
    document.getElementById('searchSummaryKeyword').value = document.getElementById('searchInput').value || '';
}

function closeSearchSummaryModal() {
    document.getElementById('searchSummaryModal').style.display = 'none';
}

async function generateSearchSummary() {
    const keyword = document.getElementById('searchSummaryKeyword').value.trim();
    if (!keyword) {
        document.getElementById('searchSummaryResult').innerHTML = '<div class="ai-summary-error">请输入搜索关键词</div>';
        return;
    }
    const resultDiv = document.getElementById('searchSummaryResult');
    resultDiv.innerHTML = '<div class="ai-summary-loading">⏳ AI 正在分析...</div>';
    
    try {
        const res = await fetch('/api/summary/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keyword: keyword, force: true })
        });
        const data = await res.json();
        if (data.success && data.data) {
            let html = data.data.content
                .replace(/### /g, '<h3>').replace(/#### /g, '<h4>')
                .replace(/- /g, '<li>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>');
            html = html.replace(/<li>/g, '<ul><li>').replace(/<\/li>/g, '</li></ul>').replace(/<\/ul><ul>/g, '');
            resultDiv.innerHTML = html;
        } else {
            resultDiv.innerHTML = '<div class="ai-summary-error">❌ ' + (data.message || '生成失败') + '</div>';
        }
    } catch (e) {
        console.error('generateSearchSummary:', e);
        resultDiv.innerHTML = '<div class="ai-summary-error">❌ 网络错误</div>';
    }
}

// ======== 新闻加载 ========
async function loadNews(page) {
    if (!page) page = 1;
    const list = document.getElementById('newsList');
    if (!list) return;
    list.innerHTML = '<div class="loading">⏳ 加载中...</div>';
    try {
        const offset = (page - 1) * PER_PAGE;
        let url = '/api/news?limit=' + PER_PAGE + '&offset=' + offset;
        if (currentKeyword) url = '/api/news/search?q=' + encodeURIComponent(currentKeyword) + '&limit=' + PER_PAGE;
        if (currentTag) url += '&tag=' + encodeURIComponent(currentTag);
        const res = await fetch(url);
        const data = await res.json();
        if (!data.success) { list.innerHTML = '<div class="error">❌ 加载失败</div>'; return; }
        const items = data.data || [];
        if (items.length === 0) { list.innerHTML = '<div class="empty">📭 暂无新闻数据</div>'; document.getElementById('pagination').innerHTML = ''; return; }
        if (currentKeyword) {
            document.getElementById('pagination').innerHTML = '';
        } else {
            const total = data.total || 0;
            const tp = Math.ceil(total / PER_PAGE);
            renderPagination(page, tp);
            currentPage = page;
        }
        list.innerHTML = '';
        items.forEach(function(news) {
            var tags = (news.tags || []).map(function(t) { return '<span class="tag">' + t + '</span>'; }).join('');
            var published = news.published_time ? new Date(news.published_time).toLocaleString('zh-CN') : '';
            var source = news.source || 'Telegram';
            var url = news.url || '#';
            list.innerHTML += '<div class="news-card"><div class="news-title"><span class="news-title-text">' + news.title + '</span></div><div class="news-content">' + news.content + '</div><div class="news-meta"><span class="news-source">📰 ' + source + '</span><span class="news-date">🕐 ' + published + '</span><div class="news-tags">' + tags + '</div></div></div>';
        });
    } catch (e) {
        list.innerHTML = '<div class="error">❌ 网络错误: ' + e.message + '</div>';
        console.error(e);
    }
}

// ======== 分页 ========
function renderPagination(page, totalPages) {
    var container = document.getElementById('pagination');
    if (!container) return;
    var html = '<button onclick="changePage(' + (page - 1) + ')" ' + (page <= 1 ? 'disabled' : '') + '>◀ 上一页</button>';
    for (var i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || Math.abs(i - page) <= 2) {
            html += '<button class="' + (i === page ? 'active' : '') + '" onclick="changePage(' + i + ')">' + i + '</button>';
        } else if (i === page - 3 || i === page + 3) {
            html += '<button disabled>...</button>';
        }
    }
    html += '<button onclick="changePage(' + (page + 1) + ')" ' + (page >= totalPages ? 'disabled' : '') + '>下一页 ▶</button>';
    container.innerHTML = html;
}

function changePage(page) {
    if (page < 1) return;
    loadNews(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ======== 搜索 ========
function searchNews() {
    currentKeyword = document.getElementById('searchInput').value.trim();
    currentTag = '';
    document.querySelectorAll('#tagFilter .tag-btn').forEach(function(btn) { btn.classList.remove('active'); });
    var first = document.querySelector('#tagFilter .tag-btn:first-child');
    if (first) first.classList.add('active');
    loadNews(1);
}

function resetSearch() {
    currentKeyword = '';
    currentTag = '';
    document.getElementById('searchInput').value = '';
    document.querySelectorAll('#tagFilter .tag-btn').forEach(function(btn) { btn.classList.remove('active'); });
    var first = document.querySelector('#tagFilter .tag-btn:first-child');
    if (first) first.classList.add('active');
    loadNews(1);
}

function filterByTag(tag) {
    currentTag = tag;
    currentKeyword = '';
    document.getElementById('searchInput').value = '';
    document.querySelectorAll('#tagFilter .tag-btn').forEach(function(btn) { btn.classList.remove('active'); });
    event.target.classList.add('active');
    loadNews(1);
}

// 回车搜索
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') searchNews();
        });
    }
});

// 点击模态框外部关闭
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('searchSummaryModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) closeSearchSummaryModal();
        });
    }
});

// ======== 启动加载 ========
document.addEventListener('DOMContentLoaded', function() {
    // 只在主页加载（通过 id 是否存在判断）
    if (document.getElementById('totalCount')) {
        loadStats();
    }
    if (document.getElementById('tagFilter')) {
        loadTags();
    }
    if (document.getElementById('newsList')) {
        loadNews();
    }
    if (document.getElementById('aiSummaryGrid')) {
        loadAllSummaries();
    }
});