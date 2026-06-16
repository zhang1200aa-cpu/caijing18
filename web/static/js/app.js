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
            document.getElementById('totalCount').textContent = data.data.total;
            document.getElementById('todayCount').textContent = data.data.today;
        }
    } catch (e) { console.error('loadStats:', e); }
}

// ======== 标签 ========
async function loadTags() {
    try {
        const res = await fetch('/api/tags');
        const data = await res.json();
        if (data.success) {
            const c = document.getElementById('tagFilter');
            c.innerHTML = '<button class="tag-btn active" onclick="filterByTag(\'\')">全部</button>';
            data.data.forEach(tag => {
                c.innerHTML += '<button class="tag-btn" onclick="filterByTag(\'' + tag.name + '\')">' + tag.name + ' (' + tag.count + ')</button>';
            });
        }
    } catch (e) { console.error('loadTags:', e); }
}

// ======== AI 总结加载 ========
async function loadAISummary() {
    const section = document.getElementById('aiSummarySection');
    const contentDiv = document.getElementById('aiSummaryContent');
    const meta = document.getElementById('aiSummaryMeta');
    if (!section) return;
    try {
        const res = await fetch('/api/summary/status');
        const data = await res.json();
        if (data.success && data.data) {
            let found = null;
            for (const key of ['1d', '3d', '1w']) {
                if (data.data[key] && data.data[key].content) { found = data.data[key]; break; }
            }
            if (!found) {
                for (const key of Object.keys(data.data)) {
                    if (data.data[key] && data.data[key].content) { found = data.data[key]; break; }
                }
            }
            if (found) {
                let html = found.content
                    .replace(/### /g, '<h3>').replace(/#### /g, '<h4>')
                    .replace(/- /g, '<li>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\n/g, '<br>');
                html = html.replace(/<li>/g, '<ul><li>').replace(/<\/li>/g, '</li></ul>').replace(/<\/ul><ul>/g, '');
                contentDiv.innerHTML = html;
                meta.textContent = '基于 ' + (found.news_count || '?') + ' 条新闻生成';
                section.style.display = 'block';
            } else {
                section.style.display = 'none';
            }
        } else {
            section.style.display = 'none';
        }
    } catch (e) {
        console.error('loadAISummary:', e);
        section.style.display = 'none';
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
            list.innerHTML += '<div class="news-card"><div class="news-title"><a href="' + url + '" target="_blank">' + news.title + '</a> <button class="analysis-btn" onclick="analyzeNews(\'' + news.id + '\')" id="analyzeBtn_' + news.id + '">🤖 AI解读</button></div><div class="news-content">' + news.content + '</div><div class="news-meta"><span class="news-source">📰 ' + source + '</span><span class="news-date">🕐 ' + published + '</span><div class="news-tags">' + tags + '</div></div></div>';
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

// ======== AI 新闻解读 ========
async function analyzeNews(newsId) {
    var modal = document.getElementById('analysisModal');
    var textDiv = document.getElementById('analysisText');
    var btn = document.getElementById('analyzeBtn_' + newsId);
    modal.classList.add('active');
    textDiv.innerHTML = '⏳ AI 正在分析中，请稍候...';
    if (btn) { btn.disabled = true; btn.textContent = '⏳'; }
    try {
        var res = await fetch('/api/ai/analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ news_id: newsId })
        });
        var data = await res.json();
        if (data.success && data.data && data.data.analysis) {
            textDiv.innerHTML = data.data.analysis;
        } else {
            textDiv.innerHTML = '❌ AI 分析失败: ' + (data.error || '未知错误');
        }
    } catch (e) {
        textDiv.innerHTML = '❌ 网络错误: ' + e.message;
        console.error(e);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = '🤖 AI解读'; }
    }
}

function closeAnalysisModal() {
    document.getElementById('analysisModal').classList.remove('active');
}

// 点击模态背景关闭
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('analysisModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) closeAnalysisModal();
        });
    }
});

// ======== 启动加载 ========
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadTags();
    loadAISummary();
    loadNews();
});