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

// ======== 标签图标映射 ========
var TAG_ICON_MAP = {
    '外汇': '💱', '股票': '📈', '科技': '🔬', '加密': '🪙', '加密货币': '🪙',
    '经济': '🏛️', '宏观': '🏛️', '黄金': '🥇', '债券': '📊', '石油': '🛢️',
    '能源': '⚡', '房产': '🏠', '地产': '🏠', '货币': '💵', '基金': '💼',
    '期货': '📉', 'A股': '🇨🇳', '美股': '🇺🇸', '港股': '🇭🇰', '日股': '🇯🇵',
    '欧股': '🇪🇺', '期货': '📉', '商品': '📦', '贸易': '🚢', '政策': '📜',
    '央行': '🏦', '利率': '📐', '通胀': '🔥', 'GDP': '📊', '财报': '📋',
    '企业': '🏢', '公司': '🏢', 'AI': '🤖', '芯片': '💾', '半导体': '💾',
    '新能源': '🔋', '电动车': '🚗', '医药': '💊', '消费': '🛒', '互联网': '🌐',
    '区块链': '⛓️', 'NFT': '🎨', '元宇宙': '🥽', '气候': '🌍', 'ESG': '🌱'
};

// 标签名称到 CSS 颜色类的映射
var TAG_CLASS_MAP = {
    '外汇': 'tag-forex', '股票': 'tag-stock', 'A股': 'tag-stock', '美股': 'tag-stock',
    '港股': 'tag-stock', '日股': 'tag-stock', '欧股': 'tag-stock',
    '科技': 'tag-tech', 'AI': 'tag-tech', '芯片': 'tag-tech', '半导体': 'tag-tech',
    '互联网': 'tag-tech',
    '加密': 'tag-crypto', '加密货币': 'tag-crypto', '区块链': 'tag-crypto',
    '经济': 'tag-economy', '宏观': 'tag-economy', '政策': 'tag-economy',
    '央行': 'tag-economy', 'GDP': 'tag-economy', '通胀': 'tag-economy',
    '黄金': 'tag-gold', '债券': 'tag-bond', '石油': 'tag-oil', '能源': 'tag-oil'
};

function getTagIcon(name) {
    return TAG_ICON_MAP[name] || '📌';
}

function getTagClass(name) {
    return TAG_CLASS_MAP[name] || '';
}

// ======== 标签 ========
async function loadTags() {
    try {
        var c = document.getElementById('tagFilter');
        if (!c) return;
        var res = await fetch('/api/tags');
        var data = await res.json();
        if (data.success) {
            c.innerHTML = '<button class="tag-btn active" onclick="filterByTag(\'\')"><span class="tag-icon">🏷️</span> 全部</button>';
            data.data.forEach(function(tag) {
                var icon = getTagIcon(tag.name);
                c.innerHTML += '<button class="tag-btn" onclick="filterByTag(\'' + tag.name + '\')"><span class="tag-icon">' + icon + '</span> ' + tag.name + ' (' + tag.count + ')</button>';
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

// ======== 新闻内容展开/收起 ========
function toggleContent(el) {
    if (!el.classList.contains('news-content')) return;
    el.classList.toggle('expanded');
}

// ======== 搜索结果总结弹窗 ========
function openSummaryModal() {
    window.location.href = '/summary';
}

function closeSearchSummaryModal() {
    const modal = document.getElementById('searchSummaryModal');
    if (modal) modal.style.display = 'none';
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
            var tags = (news.tags || []).map(function(t) { return '<span class="tag ' + getTagClass(t) + '">' + t + '</span>'; }).join('');
            var published = news.published_time || '';
            var source = news.source || 'Telegram';
            var url = news.url || '#';
            // 去掉微秒后缀 .xxxxxx，只保留到秒
            var publishedClean = published.replace(/\.\d+/, '');
            var showHint = (news.content || '').length > 120 ? '' : ' expanded';
            list.innerHTML += '<div class="news-card"><div class="news-title"><span class="news-title-text">' + news.title + '</span></div><div class="news-content' + showHint + '" onclick="toggleContent(this)">' + news.content + '</div><div class="news-meta"><span class="news-date">🕐 ' + publishedClean + '</span><div class="news-tags">' + tags + '</div></div></div>';
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

// ======== 加载公告 ========
async function loadNotice() {
    const container = document.getElementById('siteNotice');
    if (!container) return;
    try {
        const res = await fetch('/api/admin/site-notice');
        const data = await res.json();
        if (data.success && data.data.notice) {
            container.innerHTML = '<div class="notice-inner">📢 ' + data.data.notice + '</div>';
            container.style.display = 'block';
        } else {
            container.style.display = 'none';
        }
    } catch (e) {
        console.error('loadNotice:', e);
        container.style.display = 'none';
    }
}

// ======== 加载网站名称 ========
async function loadSiteName() {
    const displayEl = document.getElementById('siteNameDisplay');
    const titleEl = document.getElementById('pageTitle');
    try {
        const res = await fetch('/api/admin/site-name');
        const data = await res.json();
        if (data.success && data.data.site_name) {
            var name = data.data.site_name;
            if (displayEl) displayEl.textContent = name;
            if (titleEl) titleEl.textContent = '📈 ' + name;
        }
    } catch (e) {
        console.error('loadSiteName:', e);
    }
}

// ======== 启动加载 ========
document.addEventListener('DOMContentLoaded', function() {
    // 加载网站名称
    if (document.getElementById('siteNameDisplay')) {
        loadSiteName();
    }
    // 只在主页加载（通过 id 是否存在判断）
    if (document.getElementById('totalCount')) {
        loadStats();
    }
    if (document.getElementById('tagFilter')) {
        loadTags();
    }
    if (document.getElementById('siteNotice')) {
        loadNotice();
    }
    if (document.getElementById('newsList')) {
        loadNews();
    }
    if (document.getElementById('summaryGrid')) {
        loadAllSummaries();
    }
});