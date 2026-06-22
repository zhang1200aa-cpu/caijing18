let currentRange = 'today';
let isLoggedIn = false;
let firstRunChannelsAdded = [];

// ======== 认证相关 ========
async function checkLogin() {
    try {
        const res = await fetch('/api/admin/check');
        const data = await res.json();
        if (data.is_admin) {
            isLoggedIn = true;
            document.getElementById('loginModal').classList.remove('active');
            document.getElementById('mainContent').style.display = 'block';
            document.getElementById('headerUser').textContent = '👤 admin';
            document.getElementById('logoutLink').style.display = 'inline';
            initAdmin();
        } else {
            isLoggedIn = false;
            document.getElementById('loginModal').classList.add('active');
            document.getElementById('mainContent').style.display = 'none';
        }
    } catch (e) {
        document.getElementById('loginModal').classList.add('active');
    }
}

async function doLogin() {
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;
    const btn = document.getElementById('loginBtn');
    btn.disabled = true;
    btn.textContent = '⏳ 登录中...';
    try {
        const res = await fetch('/api/admin/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ 登录成功', 'success');
            document.getElementById('loginModal').classList.remove('active');
            document.getElementById('mainContent').style.display = 'block';
            document.getElementById('headerUser').textContent = '👤 ' + username;
            document.getElementById('logoutLink').style.display = 'inline';
            isLoggedIn = true;
            initAdmin();
        } else {
            showToast('❌ ' + (data.message || '登录失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '登录';
    }
}

async function doLogout() {
    try {
        await fetch('/api/admin/logout');
    } catch (e) {}
    isLoggedIn = false;
    document.getElementById('mainContent').style.display = 'none';
    document.getElementById('headerUser').textContent = '';
    document.getElementById('logoutLink').style.display = 'none';
    document.getElementById('loginModal').classList.add('active');
    document.getElementById('loginPassword').value = '';
    showToast('已退出登录', 'info');
}

// ======== 首次启动引导 ========
async function checkFirstRun() {
    try {
        const res = await fetch('/api/admin/system/config');
        const data = await res.json();
        if (data.success) {
            const config = data.data;
            if (config.first_run && config.needs_channel) {
                setTimeout(function() {
                    document.getElementById('firstRunModal').classList.add('active');
                }, 500);
            } else if (config.needs_channel) {
                document.getElementById('channelWarningBanner').style.display = 'block';
            }
        }
    } catch (e) {
        console.error('首次启动检查失败:', e);
    }
}

async function addFirstRunChannel() {
    const input = document.getElementById('firstRunChannelUrl');
    const url = input.value.trim();
    if (!url) { showToast('❌ 请输入频道 URL', 'error'); return; }
    if (!url.startsWith('https://t.me/s/')) { showToast('❌ URL 格式错误，应为 https://t.me/s/频道名', 'error'); return; }

    try {
        const res = await fetch('/api/admin/channels/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
        const data = await res.json();
        if (data.success) {
            const name = data.data && data.data.name || url.split('/').pop();
            firstRunChannelsAdded.push({ url: url, name: name });
            showToast('✅ 已添加频道: ' + name, 'success');
            input.value = '';
            updateFirstRunAddedList();
        } else {
            showToast('❌ ' + (data.message || '添加失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    }
}

function updateFirstRunAddedList() {
    const container = document.getElementById('firstRunAddedList');
    if (firstRunChannelsAdded.length === 0) {
        container.innerHTML = '';
        return;
    }
    var html = '<div style="background:#f6ffed;padding:10px;border-radius:6px;border:1px solid #b7eb8f;">';
    html += '<div style="font-size:13px;font-weight:600;margin-bottom:6px;">✅ 已添加的频道：</div>';
    for (var i = 0; i < firstRunChannelsAdded.length; i++) {
        html += '<div style="font-size:12px;padding:2px 0;">' + (i+1) + '. ' + firstRunChannelsAdded[i].name + '</div>';
    }
    html += '</div>';
    container.innerHTML = html;
}

function closeFirstRun() {
    document.getElementById('firstRunModal').classList.remove('active');
    checkChannelWarning();
    showToast('🎉 欢迎使用！可以开始抓取新闻了', 'success');
}

function skipFirstRun() {
    document.getElementById('firstRunModal').classList.remove('active');
    document.getElementById('channelWarningBanner').style.display = 'block';
    showToast('⏭️ 已跳过，可在频道管理中随时添加', 'info');
}

async function checkChannelWarning() {
    try {
        const res = await fetch('/api/admin/check-channels');
        const data = await res.json();
        if (data.success && data.data && !data.data.has_channels) {
            document.getElementById('channelWarningBanner').style.display = 'block';
        }
    } catch (e) {}
}

function dismissWarning() {
    document.getElementById('channelWarningBanner').style.display = 'none';
}

// ======== Tab 切换 ========
function switchTab(tab, btn) {
    document.querySelectorAll('.tabs .tab').forEach(function(t) { t.classList.remove('active'); });
    document.querySelectorAll('.tab-content').forEach(function(t) { t.classList.remove('active'); });
    btn.classList.add('active');
    document.getElementById('tab-' + tab).classList.add('active');
    if (tab === 'channels') {
        loadChannels();
        loadScrapeIntervalBar();
    }
    if (tab === 'settings') {
        loadScrapeInterval();
        loadSiteName();
        loadNotice();
        loadAISettings();
        loadSummaryPrompts();
        loadSummarySchedule();
    }
}

// ======== 初始化管理后台 ========
async function initAdmin() {
    loadStats();
    loadConfig();
    loadTags();
    loadChannels();
    loadOverviewChannels();
    loadScrapeInterval();
    loadSiteName();
    checkFirstRun();
    checkChannelWarning();
}

// ======== 概览页加载频道概要 ========
async function loadOverviewChannels() {
    const container = document.getElementById('overviewChannels');
    try {
        const res = await fetch('/api/admin/channels');
        const data = await res.json();
        if (!data.success) {
            container.innerHTML = '<div class="empty">暂无频道数据</div>';
            return;
        }
        const channels = data.data || [];
        if (channels.length === 0) {
            container.innerHTML = '<div class="empty">暂无订阅频道，请前往 <a href="javascript:void(0)" onclick="switchTab(\'channels\', document.querySelector(\'.tabs .tab:nth-child(2)\'))" style="color:#0f3460;text-decoration:underline;">频道管理</a> 添加</div>';
            return;
        }
        var html = '<div class="table-wrap"><table><thead><tr><th>状态</th><th>频道名</th><th>URL</th></tr></thead><tbody>';
        for (var i = 0; i < channels.length; i++) {
            var c = channels[i];
            var status = c.enabled ? '<span class="status-dot on"></span>正常' : '<span class="status-dot off"></span>已停用';
            html += '<tr><td>' + status + '</td><td><strong>' + (c.name || c.url) + '</strong></td>';
            html += '<td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">';
            html += '<a href="' + c.url + '" target="_blank" style="color:#0f3460;font-size:12px;">' + c.url + '</a></td></tr>';
        }
        html += '</tbody></table></div>';
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 加载失败</div>';
    }
}

// ======== 统计 ========
async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        if (data.success) {
            document.getElementById('totalNews').textContent = data.data.total || 0;
            document.getElementById('todayNews').textContent = data.data.today || 0;
            document.getElementById('totalSources').textContent = data.data.channels || 0;
        }
    } catch (e) { console.error(e); }
}

// ======== 系统配置 ========
async function loadConfig() {
    const container = document.getElementById('configStatus');
    try {
        const res = await fetch('/api/ai/status');
        const data = await res.json();
        if (data.success) {
            var d = data.data;
            var html = '';
            html += '<div class="config-row"><span class="config-label">📡 Web 服务</span><span class="config-value ok">🟢 运行中</span></div>';
            html += '<div class="config-row"><span class="config-label">🔑 AI API Key</span><span class="config-value ' + (d.configured ? 'ok' : 'err') + '">' + (d.configured ? '✅ 已配置' : '❌ 未配置') + '</span></div>';
            html += '<div class="config-row"><span class="config-label">🔗 AI Base URL</span><span class="config-value">' + (d.base_url || '-') + '</span></div>';
            html += '<div class="config-row"><span class="config-label">🤖 AI 模型</span><span class="config-value">' + (d.model || '-') + '</span></div>';
            html += '<div class="config-row"><span class="config-label">🌐 API 连接</span><span class="config-value ' + (d.connected ? 'ok' : 'err') + '">' + (d.connected ? '✅ 正常' : '❌ 失败') + '</span></div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="error">❌ 加载失败</div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 网络错误</div>';
    }
}

// ======== 标签 ========
async function loadTags() {
    const container = document.getElementById('tagManagement');
    try {
        const res = await fetch('/api/tags');
        const data = await res.json();
        if (data.success) {
            const tags = data.data || [];
            document.getElementById('totalTags').textContent = tags.length;
            if (tags.length === 0) {
                container.innerHTML = '<div class="empty">暂无标签</div>';
                return;
            }
            var html = '<div class="tag-list">';
            for (var i = 0; i < tags.length; i++) {
                var tag = tags[i];
                var name = tag.name || tag;
                var count = tag.count ? ' <span class="count">(' + tag.count + ')</span>' : '';
                html += '<span class="tag-item">' + name + count + '</span>';
            }
            html += '</div><p style="margin-top:10px;font-size:12px;color:#999;">共 ' + tags.length + ' 个标签</p>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="error">❌ 加载失败</div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 网络错误</div>';
    }
}

// ======== 频道管理 ========
var _channelPollTimer = null;

async function loadChannels() {
    const container = document.getElementById('channelList');
    container.innerHTML = '<div class="loading">⏳ 加载频道列表...</div>';
    try {
        const res = await fetch('/api/admin/channels');
        const data = await res.json();
        if (!data.success) {
            container.innerHTML = '<div class="error">❌ ' + (data.message || '加载失败') + '</div>';
            return;
        }
        const channels = data.data || [];
        if (channels.length === 0) {
            container.innerHTML = '<div class="empty" style="text-align:center;padding:30px 0;">📡 暂无订阅频道，在上方输入频道 URL 添加</div>';
            return;
        }

        // 检测是否有运行中的回填任务，自动轮询
        var hasRunning = channels.some(function(c) {
            var s = c.history_scrape_status || 'none';
            return s === 'running' || s === 'pending';
        });
        if (hasRunning) {
            if (!_channelPollTimer) {
                _channelPollTimer = setInterval(function() { loadChannels(); }, 3000);
            }
        } else {
            if (_channelPollTimer) {
                clearInterval(_channelPollTimer);
                _channelPollTimer = null;
            }
        }

        var html = '<div class="table-wrap"><table><thead><tr><th>状态</th><th>频道名称</th><th>URL</th><th>历史回填</th><th>操作</th></tr></thead><tbody>';
        for (var i = 0; i < channels.length; i++) {
            var c = channels[i];
            var statusHtml = c.enabled
                ? '<span class="badge badge-success">🟢 启用</span>'
                : '<span class="badge badge-secondary">🔴 停用</span>';

            // 历史回填状态显示（回填中显示进度条）
            var histStatus = c.history_scrape_status || 'none';
            var histCellHtml = '';
            if (histStatus === 'running') {
                var current = c.history_scrape_count || 0;
                var maxDepth = c.scrape_depth || 1000;
                var pct = Math.min(100, Math.round((current / maxDepth) * 100));
                if (pct < 0) pct = 0;
                histCellHtml = '<div class="progress-bar-wrap">'
                    + '<div class="progress-bar-fill" style="width:' + pct + '%;"></div>'
                    + '<div class="progress-bar-text">' + current + '/' + maxDepth + ' (' + pct + '%)</div>'
                    + '</div>';
            } else if (histStatus === 'pending') {
                histCellHtml = '<span class="badge badge-warning">⏳ 等待中</span>';
            } else if (histStatus === 'done') {
                var count = c.history_scrape_count || 0;
                var maxDepth = c.scrape_depth || 1000;
                histCellHtml = '<span class="badge badge-success">✅ ' + count + '/' + maxDepth + ' 条</span>';
            } else if (histStatus === 'failed') {
                histCellHtml = '<span class="badge badge-danger">❌ 失败</span>';
            } else {
                histCellHtml = '<span class="badge badge-secondary">未回填</span>';
            }

            html += '<tr><td>' + statusHtml + '</td>';
            html += '<td><strong>' + (c.name || c.url.split('/').pop()) + '</strong></td>';
            html += '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;">' + c.url + '</td>';
            html += '<td>' + histCellHtml + '</td>';
            html += '<td style="white-space:nowrap;">';
            if (c.enabled) {
                html += '<button class="btn btn-sm btn-warning" onclick="toggleChannel(\'' + (c.id || '') + '\', false)">停用</button> ';
            } else {
                html += '<button class="btn btn-sm btn-success" onclick="toggleChannel(\'' + (c.id || '') + '\', true)">启用</button> ';
            }
            // 只有非运行中状态才显示重新回填按钮
            if (histStatus !== 'running' && histStatus !== 'pending') {
                html += '<button class="btn btn-sm btn-outline" onclick="reScrapeChannel(\'' + (c.id || '') + '\')">📥 回填</button> ';
            }
            html += '<button class="btn btn-sm btn-danger" onclick="removeChannel(\'' + (c.id || '') + '\')">删除</button>';
            html += '</td></tr>';
        }
        html += '</tbody></table></div>';
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 网络错误: ' + e.message + '</div>';
    }
}

async function addChannel() {
    var url = document.getElementById('channelUrl').value.trim();
    if (!url) {
        showToast('❌ 请输入频道 URL', 'error');
        return;
    }
    if (!url.startsWith('https://t.me/s/')) {
        showToast('❌ URL 格式错误，应为 https://t.me/s/频道名', 'error');
        return;
    }
    var depthInput = document.getElementById('channelScrapeDepth');
    var scrapeDepth = parseInt(depthInput.value) || 1000;
    if (scrapeDepth < 0) scrapeDepth = 0;
    var btn = document.querySelector('#tab-channels .btn-success');
    btn.disabled = true;
    btn.textContent = '⏳ 添加中...';
    showToast('⏳ 正在添加频道并回填历史消息 (约 ' + scrapeDepth + ' 条)...', 'info');
    try {
        const res = await fetch('/api/admin/channels/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url, scrape_depth: scrapeDepth })
        });
        const data = await res.json();
        if (data.success) {
            var msg = '✅ 频道添加成功';
            if (data.history_status === 'running') {
                msg += '，历史消息正在后台回填中';
            } else if (data.history_async) {
                msg += '，历史消息后台回填已启动';
            }
            showToast(msg, 'success');
            document.getElementById('channelUrl').value = '';
            loadChannels();
        } else {
            showToast('❌ ' + (data.message || '添加失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '➕ 添加频道';
    }
}

async function reScrapeChannel(id) {
    if (!confirm('确定要重新回填此频道的历史消息吗？')) {
        return;
    }
    try {
        const res = await fetch('/api/admin/channels/re-scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ ' + (data.message || '已开始回填'), 'success');
            loadChannels();
            // 每5秒刷新一次状态
            var checkInterval = setInterval(function() {
                loadChannels();
            }, 5000);
            // 120秒后停止自动刷新
            setTimeout(function() {
                clearInterval(checkInterval);
            }, 120000);
        } else {
            showToast('❌ ' + (data.message || '操作失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    }
}

async function removeChannel(id) {
    if (!confirm('确定要删除此频道吗？相关的新闻数据也会被清除。')) {
        return;
    }
    try {
        const res = await fetch('/api/admin/channels/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ ' + (data.message || '频道已删除'), 'success');
            loadChannels();
            loadOverviewChannels();
        } else {
            showToast('❌ ' + (data.message || '删除失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    }
}

async function toggleChannel(id, enabled) {
    try {
        const res = await fetch('/api/admin/channels/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id, enabled: enabled })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ ' + (data.message || (enabled ? '已启用' : '已停用')), 'success');
            loadChannels();
            loadOverviewChannels();
        } else {
            showToast('❌ ' + (data.message || '操作失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    }
}

// ======== 抓取任务控制 ========
async function manualScrape() {
    var btn = document.getElementById('scrapeBtn');
    var logBox = document.getElementById('operationLog');
    logBox.style.display = 'block';
    logBox.innerHTML = '<div class="log-line">⏳ 正在抓取...</div>';
    btn.disabled = true;
    btn.textContent = '⏳ 抓取中...';
    try {
        const res = await fetch('/api/admin/scrape/trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        if (data.success) {
            logBox.innerHTML = '<div class="log-line success">✅ ' + (data.message || '抓取完成') + '</div>';
            showToast('✅ 抓取完成，新增 ' + (data.count || 0) + ' 条', 'success');
            loadStats();
            loadOverviewChannels();
        } else {
            logBox.innerHTML = '<div class="log-line error">❌ ' + (data.message || '抓取失败') + '</div>';
            if (data.need_channel) {
                showToast('⚠️ ' + data.message, 'warning');
                switchTab('channels', document.querySelector('.tabs .tab:nth-child(2)'));
            } else {
                showToast('❌ ' + (data.message || '抓取失败'), 'error');
            }
        }
    } catch (e) {
        logBox.innerHTML = '<div class="log-line error">❌ 网络错误: ' + e.message + '</div>';
        showToast('❌ 网络错误', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🔍 手动抓取 Telegram';
    }
}

async function manualCleanup() {
    if (!confirm('确定要清理重复/旧数据吗？')) {
        return;
    }
    var btn = document.getElementById('cleanupBtn');
    var logBox = document.getElementById('operationLog');
    logBox.style.display = 'block';
    logBox.innerHTML = '<div class="log-line">⏳ 正在清理...</div>';
    btn.disabled = true;
    btn.textContent = '⏳ 清理中...';
    try {
        const res = await fetch('/api/admin/cleanup', {
            method: 'POST'
        });
        const data = await res.json();
        if (data.success) {
            logBox.innerHTML = '<div class="log-line success">✅ 清理完成，删除了 ' + (data.count || 0) + ' 条数据</div>';
            showToast('✅ 清理完成，删除了 ' + (data.count || 0) + ' 条', 'success');
            loadStats();
        } else {
            logBox.innerHTML = '<div class="log-line error">❌ ' + (data.message || '清理失败') + '</div>';
            showToast('❌ ' + (data.message || '清理失败'), 'error');
        }
    } catch (e) {
        logBox.innerHTML = '<div class="log-line error">❌ 网络错误: ' + e.message + '</div>';
        showToast('❌ 网络错误', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🧹 清理旧数据';
    }
}

// ======== 抓取间隔设置 ========
async function loadScrapeInterval() {
    const container = document.getElementById('scrapeSettings');
    try {
        const res = await fetch('/api/admin/settings');
        const data = await res.json();
        if (data.success) {
            var settings = data.data || {};
            var interval = settings.scrape_interval_minutes || '30';
            var html = '<div class="config-row"><span class="config-label">⏱️ 抓取间隔</span>';
            html += '<span class="config-value">每隔 ' + interval + ' 分钟自动抓取</span>';
            html += '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="error">❌ 加载失败</div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 网络错误</div>';
    }
}

async function loadScrapeIntervalBar() {
    const container = document.getElementById('scrapeIntervalBar');
    try {
        const res = await fetch('/api/admin/settings');
        const data = await res.json();
        if (data.success) {
            var settings = data.data || {};
            var interval = settings.scrape_interval_minutes || '30';
            var html = '<div style="display:flex;align-items:center;gap:12px;">';
            html += '<span>当前间隔：每隔 <strong>' + interval + '</strong> 分钟</span>';
            html += '<button class="btn btn-sm btn-outline" onclick="showIntervalModal()">⚙️ 修改</button>';
            html += '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="error">加载失败</div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="error">网络错误</div>';
    }
}

function showIntervalModal() {
    document.getElementById('intervalModal').classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

function setIntervalPreset(minutes) {
    document.getElementById('intervalInput').value = minutes;
}

async function saveInterval() {
    var interval = parseInt(document.getElementById('intervalInput').value);
    if (!interval || interval < 1) {
        showToast('❌ 请输入有效的分钟数（至少 1 分钟）', 'error');
        return;
    }
    try {
        const res = await fetch('/api/admin/settings/interval', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ interval: interval })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ ' + (data.message || '间隔已更新'), 'success');
            closeModal('intervalModal');
            loadScrapeInterval();
            loadScrapeIntervalBar();
        } else {
            showToast('❌ ' + (data.message || '更新失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    }
}

// ======== 网站名称设置 ========
async function loadSiteName() {
    const container = document.getElementById('siteNameSetting');
    try {
        const res = await fetch('/api/admin/site-name');
        const data = await res.json();
        if (data.success) {
            document.getElementById('siteNameInput').value = data.data.site_name;
            var html = '<div class="config-row"><span class="config-label">🌐 当前网站名称</span><span class="config-value ok" id="currentSiteNameDisplay">' + data.data.site_name + '</span></div>';
            container.innerHTML = html;
        }
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 加载失败</div>';
    }
}

async function saveSiteName() {
    var name = document.getElementById('siteNameInput').value.trim();
    if (!name) {
        showToast('❌ 网站名称不能为空', 'error');
        return;
    }
    var btn = document.getElementById('saveSiteNameBtn');
    btn.disabled = true;
    btn.textContent = '⏳ 保存中...';
    try {
        const res = await fetch('/api/admin/site-name', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ site_name: name })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ 网站名称已更新', 'success');
            document.title = name + ' - 系统管理';
            // 更新管理后台标题
            document.querySelector('.header h1').textContent = '⚙️ ' + name;
        } else {
            showToast('❌ ' + (data.message || '保存失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '💾 保存';
    }
}

// ======== 网站公告 ========
async function loadNotice() {
    const input = document.getElementById('noticeInput');
    const status = document.getElementById('noticeStatus');
    try {
        const res = await fetch('/api/admin/site-notice');
        const data = await res.json();
        if (data.success) {
            input.value = data.data.notice || '';
            status.textContent = '已加载';
        } else {
            status.textContent = '❌ 加载失败';
        }
    } catch (e) {
        status.textContent = '❌ 网络错误';
    }
}

async function saveNotice() {
    const notice = document.getElementById('noticeInput').value.trim();
    const btn = document.getElementById('saveNoticeBtn');
    const status = document.getElementById('noticeStatus');
    btn.disabled = true;
    btn.textContent = '⏳ 保存中...';
    status.textContent = '';
    try {
        const res = await fetch('/api/admin/site-notice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notice: notice })
        });
        const data = await res.json();
        if (data.success) {
            status.textContent = '✅ 公告已保存';
            setTimeout(function() { status.textContent = ''; }, 3000);
        } else {
            status.textContent = '❌ ' + (data.message || '保存失败');
        }
    } catch (e) {
        status.textContent = '❌ 网络错误';
    } finally {
        btn.disabled = false;
        btn.textContent = '💾 保存公告';
    }
}

// ======== AI 设置 ========
async function loadAISettings() {
    const container = document.getElementById('aiSettings');
    try {
        const res = await fetch('/api/ai/status');
        const data = await res.json();
        if (data.success) {
            var d = data.data;
            var html = '<div class="config-row"><span class="config-label">🔑 API Key</span><span class="config-value ' + (d.configured ? 'ok' : 'err') + '">' + (d.configured ? '✅ 已配置' : '❌ 未配置') + '</span></div>';
            html += '<div class="config-row"><span class="config-label">🔗 Base URL</span><span class="config-value">' + (d.base_url || '未设置') + '</span></div>';
            html += '<div class="config-row"><span class="config-label">🤖 模型</span><span class="config-value">' + (d.model || '未设置') + '</span></div>';
            html += '<div class="config-row"><span class="config-label">🌐 连接测试</span><span class="config-value ' + (d.connected ? 'ok' : 'err') + '">' + (d.connected ? '✅ 连接正常' : '❌ 连接失败') + '</span></div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="error">❌ 加载失败</div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 网络错误</div>';
    }
}

// ======== 修改密码 ========
async function changePwd() {
    var oldPwd = document.getElementById('oldPassword').value;
    var newPwd = document.getElementById('newPassword').value;
    if (!oldPwd || !newPwd) {
        showToast('❌ 请填写原密码和新密码', 'error');
        return;
    }
    if (newPwd.length < 4) {
        showToast('❌ 新密码至少 4 位', 'error');
        return;
    }
    var btn = document.getElementById('changePwdBtn');
    btn.disabled = true;
    btn.textContent = '⏳ 修改中...';
    try {
        const res = await fetch('/api/admin/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_password: oldPwd, new_password: newPwd })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ ' + (data.message || '密码修改成功'), 'success');
            document.getElementById('oldPassword').value = '';
            document.getElementById('newPassword').value = '';
        } else {
            showToast('❌ ' + (data.message || '修改失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '修改密码';
    }
}

// ======== AI 总结提示词管理 ========
async function loadSummaryPrompts() {
    const dailyInput = document.getElementById('promptDailyInput');
    const compositeInput = document.getElementById('promptCompositeInput');
    const todayQAInput = document.getElementById('promptTodayQAInput');
    const status = document.getElementById('promptStatus');
    const todayQAStatus = document.getElementById('promptTodayQAStatus');
    if (!dailyInput || !compositeInput) return;
    try {
        dailyInput.placeholder = '⏳ 加载中...';
        compositeInput.placeholder = '⏳ 加载中...';
        if (todayQAInput) todayQAInput.placeholder = '⏳ 加载中...';
        const res = await fetch('/api/admin/summary-prompts');
        const data = await res.json();
        if (data.success) {
            dailyInput.value = data.data.daily || '';
            compositeInput.value = data.data.composite || '';
            if (todayQAInput) todayQAInput.value = data.data.todayqa || '';
            status.textContent = '✅ 已加载';
            if (todayQAStatus) todayQAStatus.textContent = '✅ 已加载';
        } else {
            status.textContent = '❌ 加载失败';
        }
    } catch (e) {
        status.textContent = '❌ 网络错误';
    }
}

async function saveSummaryPrompts() {
    const daily = document.getElementById('promptDailyInput').value;
    const composite = document.getElementById('promptCompositeInput').value;
    const btn = document.getElementById('savePromptsBtn');
    const status = document.getElementById('promptStatus');
    btn.disabled = true;
    btn.textContent = '⏳ 保存中...';
    status.textContent = '';
    try {
        const res = await fetch('/api/admin/summary-prompts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ daily: daily, composite: composite })
        });
        const data = await res.json();
        if (data.success) {
            status.textContent = '✅ ' + (data.message || '提示词已保存');
            setTimeout(function() { status.textContent = ''; }, 3000);
        } else {
            status.textContent = '❌ ' + (data.message || '保存失败');
        }
    } catch (e) {
        status.textContent = '❌ 网络错误: ' + e.message;
    } finally {
        btn.disabled = false;
        btn.textContent = '💾 保存提示词';
    }
}

async function saveTodayQAPrompt() {
    const input = document.getElementById('promptTodayQAInput');
    const status = document.getElementById('promptTodayQAStatus');
    const parent = status.parentNode;
    const btn = parent ? parent.querySelector('.btn-primary') : null;
    if (btn) { btn.disabled = true; btn.textContent = '⏳ 保存中...'; }
    status.textContent = '';
    try {
        const res = await fetch('/api/admin/summary-prompts/todayqa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ today_qa_prompt: input.value })
        });
        const data = await res.json();
        if (data.success) {
            status.textContent = '✅ 当日财经分析提示词已保存';
            setTimeout(function() { status.textContent = ''; }, 3000);
        } else {
            status.textContent = '❌ ' + (data.message || '保存失败');
        }
    } catch (e) {
        status.textContent = '❌ 网络错误';
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = '💾 保存提示词'; }
    }
}

async function resetSummaryPrompt(type) {
    if (!confirm('确定要恢复 ' + (type === 'daily' ? '每日/昨日' : type === 'composite' ? '三日/一周' : '当日财经分析') + ' 总结提示词为默认值吗？')) {
        return;
    }
    const isTodayQA = type === 'todayqa';
    const status = document.getElementById(isTodayQA ? 'promptTodayQAStatus' : 'promptStatus');
    status.textContent = '⏳ 重置中...';
    try {
        const res = await fetch('/api/admin/summary-prompts/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: type })
        });
        const data = await res.json();
        if (data.success) {
            status.textContent = '✅ ' + (data.message || '已重置为默认值');
            // 重新加载提示词
            loadSummaryPrompts();
        } else {
            status.textContent = '❌ ' + (data.message || '重置失败');
        }
    } catch (e) {
        status.textContent = '❌ 网络错误: ' + e.message;
    }
}

// ======== AI 总结定时设置 ========
async function loadSummarySchedule() {
    const container = document.getElementById('summaryScheduleSettings');
    if (!container) return;
    try {
        const res = await fetch('/api/admin/summary-schedule');
        const data = await res.json();
        if (!data.success) {
            container.innerHTML = '<div class="error">❌ ' + (data.message || '加载失败') + '</div>';
            return;
        }
        var s = data.data;
        var html = '<div class="schedule-card">';

        // 每日总结
        html += '<div class="schedule-item" style="border-bottom:1px solid #eee;padding:14px 0;">';
        html += '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">';
        html += '<div><strong>📅 每日总结</strong><br><span style="font-size:12px;color:#999;">每天执行一次</span></div>';
        html += '<div style="display:flex;align-items:center;gap:8px;">';
        html += '<label style="font-size:13px;display:flex;align-items:center;gap:4px;"><input type="checkbox" class="schedule-enabled" data-type="today" ' + (s.today.enabled ? 'checked' : '') + '> 启用</label>';
        html += '<input type="time" class="schedule-time input-text" data-type="today" value="' + s.today.time + '" style="width:130px;">';
        html += '</div></div></div>';

        // 近3天总结
        html += '<div class="schedule-item" style="border-bottom:1px solid #eee;padding:14px 0;">';
        html += '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">';
        html += '<div><strong>📊 近3天总结</strong><br><span style="font-size:12px;color:#999;">每天执行一次</span></div>';
        html += '<div style="display:flex;align-items:center;gap:8px;">';
        html += '<label style="font-size:13px;display:flex;align-items:center;gap:4px;"><input type="checkbox" class="schedule-enabled" data-type="3d" ' + (s['3d'].enabled ? 'checked' : '') + '> 启用</label>';
        html += '<input type="time" class="schedule-time input-text" data-type="3d" value="' + s['3d'].time + '" style="width:130px;">';
        html += '</div></div></div>';

        // 近1周总结
        html += '<div class="schedule-item" style="padding:14px 0;">';
        html += '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">';
        html += '<div><strong>📈 近1周总结</strong><br><span style="font-size:12px;color:#999;">每周执行一次</span></div>';
        html += '<div style="display:flex;align-items:center;gap:8px;">';
        html += '<label style="font-size:13px;display:flex;align-items:center;gap:4px;"><input type="checkbox" class="schedule-enabled" data-type="1w" ' + (s['1w'].enabled ? 'checked' : '') + '> 启用</label>';
        html += '<select class="schedule-day input-text" data-type="1w" style="width:100px;">';
        var days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
        var dayNames = {'mon':'周一','tue':'周二','wed':'周三','thu':'周四','fri':'周五','sat':'周六','sun':'周日'};
        for (var i = 0; i < days.length; i++) {
            var sel = (s['1w'].day === days[i]) ? ' selected' : '';
            html += '<option value="' + days[i] + '"' + sel + '>' + dayNames[days[i]] + '</option>';
        }
        html += '</select>';
        html += '<input type="time" class="schedule-time input-text" data-type="1w" value="' + s['1w'].time + '" style="width:130px;">';
        html += '</div></div></div>';

        html += '<div style="margin-top:12px;display:flex;gap:8px;">';
        html += '<button class="btn btn-primary" onclick="saveSummarySchedule()">💾 保存定时设置</button>';
        html += '<span id="scheduleSaveStatus" style="font-size:12px;color:#999;align-self:center;"></span>';
        html += '</div></div>';

        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 网络错误: ' + e.message + '</div>';
    }
}

async function saveSummarySchedule() {
    var status = document.getElementById('scheduleSaveStatus');
    if (!status) return;
    status.textContent = '⏳ 保存中...';
    try {
        var types = ['today', '3d', '1w'];
        var settings = {};
        for (var i = 0; i < types.length; i++) {
            var t = types[i];
            var enabledEl = document.querySelector('.schedule-enabled[data-type="' + t + '"]');
            var timeEl = document.querySelector('.schedule-time[data-type="' + t + '"]');
            var dayEl = document.querySelector('.schedule-day[data-type="' + t + '"]');
            var setting = {
                enabled: enabledEl ? enabledEl.checked : true,
                time: timeEl ? timeEl.value : '09:00'
            };
            if (dayEl) {
                setting.day = dayEl.value;
            }
            settings[t] = setting;
        }
        const res = await fetch('/api/admin/summary-schedule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'all', settings: settings })
        });
        const data = await res.json();
        if (data.success) {
            status.textContent = '✅ ' + (data.message || '保存成功');
            setTimeout(function() { status.textContent = ''; }, 3000);
        } else {
            status.textContent = '❌ ' + (data.message || '保存失败');
        }
    } catch (e) {
        status.textContent = '❌ 网络错误: ' + e.message;
    }
}

// ======== Toast 通知 ========
function showToast(message, type) {
    var existing = document.querySelector('.toast-container');
    if (!existing) {
        var container = document.createElement('div');
        container.className = 'toast-container';
        container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
        document.body.appendChild(container);
    }
    var container = document.querySelector('.toast-container');
    var toast = document.createElement('div');
    toast.className = 'toast toast-' + (type || 'info');
    toast.style.cssText = 'padding:12px 18px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);font-size:14px;animation:slideIn 0.3s ease;max-width:400px;word-break:break-word;';
    if (type === 'success') { toast.style.background = '#f6ffed'; toast.style.border = '1px solid #b7eb8f'; toast.style.color = '#135200'; }
    else if (type === 'error') { toast.style.background = '#fff2f0'; toast.style.border = '1px solid #ffccc7'; toast.style.color = '#820014'; }
    else if (type === 'warning') { toast.style.background = '#fffbe6'; toast.style.border = '1px solid #ffe58f'; toast.style.color = '#613400'; }
    else { toast.style.background = '#e6f7ff'; toast.style.border = '1px solid #91d5ff'; toast.style.color = '#003a8c'; }
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function() {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(function() {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 300);
    }, 3500);
}

// 样式注入 - 动画
(function() {
    var style = document.createElement('style');
    style.textContent = '@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }';
    document.head.appendChild(style);
})();

// ======== 页面初始化 ========
document.addEventListener('DOMContentLoaded', function() {
    checkLogin();
});
