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
        const res = await fetch('/api/admin/check-channels');
        const data = await res.json();
        if (data.success) {
            const info = data.data;
            if (!info.has_channels) {
                setTimeout(function() {
                    document.getElementById('firstRunModal').classList.add('active');
                }, 500);
            } else if (!info.any_enabled) {
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
        loadTodayQAHours();
    }
    if (tab === 'backup') {
        loadBackups();
        loadBackupSchedule();
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

// ======== AI 设置（可编辑表单）========
async function loadAISettings() {
    const container = document.getElementById('aiSettings');
    try {
        const res = await fetch('/api/ai/status');
        const data = await res.json();
        if (data.success) {
            var d = data.data;
            // 脱敏处理：只显示后4位
            var maskedKey = d.api_key || '';
            var keyDisplay = d.configured ? ('****' + maskedKey.slice(-4)) : '';
            var html = '<div style="max-width:600px;">';
            html += '<div class="form-group">';
            html += '<label style="font-size:13px;font-weight:600;display:block;margin-bottom:4px;">🔑 API Key</label>';
            html += '<input type="password" class="input-text" id="aiApiKey" value="' + escapeHtml(keyDisplay) + '" placeholder="输入 AI API Key" style="width:100%;font-family:monospace;">';
            html += '</div>';
            html += '<div class="form-group" style="margin-top:12px;">';
            html += '<label style="font-size:13px;font-weight:600;display:block;margin-bottom:4px;">🔗 Base URL</label>';
            html += '<input type="text" class="input-text" id="aiBaseUrl" value="' + escapeHtml(d.base_url || '') + '" placeholder="例如：https://api.openai.com/v1" style="width:100%;font-family:monospace;">';
            html += '<div style="font-size:11px;color:#aaa;margin-top:2px;">留空使用默认值</div>';
            html += '</div>';
            html += '<div class="form-group" style="margin-top:12px;">';
            html += '<label style="font-size:13px;font-weight:600;display:block;margin-bottom:4px;">🤖 模型</label>';
            html += '<input type="text" class="input-text" id="aiModel" value="' + escapeHtml(d.model || '') + '" placeholder="例如：gpt-3.5-turbo" style="width:100%;font-family:monospace;">';
            html += '<div style="font-size:11px;color:#aaa;margin-top:2px;">留空使用默认值</div>';
            html += '</div>';
            html += '<div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">';
            html += '<button class="btn btn-primary" onclick="saveAISettings()" id="saveAiBtn">💾 保存</button>';
            html += '<button class="btn btn-outline" onclick="testAIConnection()" id="testAiBtn">🔌 测试连接</button>';
            html += '<span id="aiStatus" style="font-size:13px;"></span>';
            html += '</div>';
            html += '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="error">❌ 加载失败</div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 网络错误</div>';
    }
}

async function saveAISettings() {
    var apiKey = document.getElementById('aiApiKey').value.trim();
    var baseUrl = document.getElementById('aiBaseUrl').value.trim();
    var model = document.getElementById('aiModel').value.trim();
    var statusEl = document.getElementById('aiStatus');
    var btn = document.getElementById('saveAiBtn');
    btn.disabled = true;
    btn.textContent = '⏳ 保存中...';
    statusEl.textContent = '';
    try {
        // 如果 key 是脱敏格式（以 **** 开头），则不发送 key
        var body = {};
        if (apiKey && !apiKey.startsWith('****')) {
            body.api_key = apiKey;
        }
        body.base_url = baseUrl;
        body.model = model;
        const res = await fetch('/api/admin/ai/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await res.json();
        if (data.success) {
            statusEl.textContent = '✅ 已保存';
            statusEl.style.color = '#52c41a';
            setTimeout(function() { statusEl.textContent = ''; }, 3000);
            loadAISettings();
        } else {
            statusEl.textContent = '❌ ' + (data.message || '保存失败');
            statusEl.style.color = '#ff4d4f';
        }
    } catch (e) {
        statusEl.textContent = '❌ 网络错误: ' + e.message;
        statusEl.style.color = '#ff4d4f';
    } finally {
        btn.disabled = false;
        btn.textContent = '💾 保存';
    }
}

async function testAIConnection() {
    var statusEl = document.getElementById('aiStatus');
    var btn = document.getElementById('testAiBtn');
    btn.disabled = true;
    btn.textContent = '⏳ 测试中...';
    statusEl.textContent = '';
    try {
        const res = await fetch('/api/admin/ai/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        if (data.success && data.connected) {
            statusEl.textContent = '✅ ' + (data.message || '连接测试成功');
            statusEl.style.color = '#52c41a';
        } else {
            statusEl.textContent = '❌ ' + (data.message || '连接测试失败');
            statusEl.style.color = '#ff4d4f';
        }
    } catch (e) {
        statusEl.textContent = '❌ 网络错误: ' + e.message;
        statusEl.style.color = '#ff4d4f';
    } finally {
        btn.disabled = false;
        btn.textContent = '🔌 测试连接';
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

async function loadTodayQAHours() {
    const input = document.getElementById('todayQAHoursInput');
    const status = document.getElementById('todayQAHoursStatus');
    if (!input) return;
    try {
        const res = await fetch('/api/admin/settings');
        const data = await res.json();
        if (data.success && data.data) {
            const key = 'today_qa_hours';
            let hours = 24;
            if (Array.isArray(data.data)) {
                const found = data.data.find(function(s) { return s.key === key; });
                if (found) hours = parseInt(found.value) || 24;
            } else if (typeof data.data === 'object') {
                hours = parseInt(data.data[key]) || 24;
            }
            input.value = hours;
            if (status) status.textContent = '⏱️ 当前: ' + hours + ' 小时';
        }
    } catch (e) {
        if (status) status.textContent = '❌ 加载失败';
    }
}

async function saveTodayQAHours() {
    const input = document.getElementById('todayQAHoursInput');
    const status = document.getElementById('todayQAHoursStatus');
    if (!input) return;
    const hours = parseInt(input.value);
    if (!hours || hours < 1 || hours > 720) {
        showToast('⚠️ 请设置 1~720 小时', 'warning');
        if (status) status.textContent = '⚠️ 请输入 1~720';
        return;
    }
    const btn = status ? status.parentNode.querySelector('.btn-primary') : null;
    if (btn) { btn.disabled = true; btn.textContent = '⏳ 保存中...'; }
    if (status) status.textContent = '';
    try {
        const res = await fetch('/api/admin/settings/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: 'today_qa_hours', value: String(hours) })
        });
        const data = await res.json();
        if (data.success) {
            if (status) status.textContent = '✅ 已保存为 ' + hours + ' 小时';
            showToast('✅ 时间范围已更新为 ' + hours + ' 小时', 'success');
        } else {
            if (status) status.textContent = '❌ ' + (data.message || '保存失败');
            showToast('❌ 保存失败', 'error');
        }
    } catch (e) {
        if (status) status.textContent = '❌ 网络错误';
        showToast('❌ 网络错误: ' + e.message, 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = '💾 保存设置'; }
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

        // 昨日总结
        html += '<div class="schedule-item" style="border-bottom:1px solid #eee;padding:14px 0;">';
        html += '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">';
        html += '<div><strong>📅 昨日总结</strong><br><span style="font-size:12px;color:#999;">每天执行一次，总结昨天的新闻</span></div>';
        html += '<div style="display:flex;align-items:center;gap:8px;">';
        html += '<label style="font-size:13px;display:flex;align-items:center;gap:4px;"><input type="checkbox" class="schedule-enabled" data-type="yesterday" ' + (s.yesterday.enabled ? 'checked' : '') + '> 启用</label>';
        html += '<input type="time" class="schedule-time input-text" data-type="yesterday" value="' + s.yesterday.time + '" style="width:130px;">';
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
        var types = ['today', 'yesterday', '3d', '1w'];
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

// ======== 每日自动备份调度配置 ========

async function loadBackupSchedule() {
    var container = document.getElementById('backupScheduleConfig');
    if (!container) return;
    container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
    try {
        var res = await fetch('/api/admin/backup-schedule');
        var data = await res.json();
        if (!data.success) {
            container.innerHTML = '<div class="error">❌ ' + (data.message || '加载失败') + '</div>';
            return;
        }
        var s = data.data || {};
        var html = '<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">';
        html += '<label style="font-size:14px;">每日备份时间：</label>';
        html += '<input type="time" id="backupScheduleTime" class="input-text" value="' + (s.time || '03:00') + '" style="width:130px;">';
        html += '<label style="font-size:13px;display:flex;align-items:center;gap:4px;">';
        html += '<input type="checkbox" id="backupScheduleEnabled" ' + (s.enabled !== false ? 'checked' : '') + '> 启用每日自动备份';
        html += '</label>';
        html += '<button class="btn btn-primary" onclick="saveBackupSchedule()">💾 保存</button>';
        html += '<span id="backupScheduleStatus" style="font-size:12px;color:#999;"></span>';
        html += '</div>';
        html += '<div style="margin-top:8px;font-size:12px;color:#999;">';
        html += '💡 系统将在每天指定时间自动创建 <strong>.db</strong>（SQLite 数据库文件）和 <strong>.json</strong>（数据导出文件）两个备份。';
        html += '备份文件只保留最近 <strong>7 天</strong>，超期的文件会自动清理。';
        html += '</div>';
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 网络错误: ' + e.message + '</div>';
    }
}

async function saveBackupSchedule() {
    var timeEl = document.getElementById('backupScheduleTime');
    var enabledEl = document.getElementById('backupScheduleEnabled');
    var status = document.getElementById('backupScheduleStatus');
    if (!timeEl || !status) return;
    status.textContent = '⏳ 保存中...';
    try {
        var res = await fetch('/api/admin/backup-schedule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                enabled: enabledEl ? enabledEl.checked : true,
                time: timeEl.value
            })
        });
        var data = await res.json();
        if (data.success) {
            status.textContent = '✅ ' + (data.message || '保存成功');
            setTimeout(function() { if (status) status.textContent = ''; }, 3000);
        } else {
            status.textContent = '❌ ' + (data.message || '保存失败');
        }
    } catch (e) {
        status.textContent = '❌ 网络错误: ' + e.message;
    }
}

// ======== 备份恢复功能 ========

async function loadBackups() {
    var container = document.getElementById('backupList');
    var status = document.getElementById('backupOperationStatus');
    if (!container) return;
    container.innerHTML = '<div class="loading">⏳ 加载备份列表...</div>';
    if (status) status.textContent = '';
    try {
        var res = await fetch('/api/admin/backup/list');
        var data = await res.json();
        if (!data.success) {
            container.innerHTML = '<div class="error">❌ ' + (data.message || '加载失败') + '</div>';
            return;
        }
        var backups = data.data || [];
        if (backups.length === 0) {
            container.innerHTML = '<div style="text-align:center;padding:30px;color:#999;">📭 暂无备份文件</div>';
            updateRestoreSelect([]);
            return;
        }
        var html = '<table class="data-table"><thead><tr><th>文件名</th><th>类型</th><th>大小</th><th>创建时间</th><th>操作</th></tr></thead><tbody>';
        for (var i = 0; i < backups.length; i++) {
            var b = backups[i];
            var isDb = b.filename.endsWith('.db');
            var icon = isDb ? '💿' : '📋';
            html += '<tr>';
            html += '<td style="word-break:break-all;max-width:360px;">' + escapeHtml(b.filename) + '</td>';
            html += '<td>' + (b.type || (isDb ? '数据库备份' : 'JSON 导出')) + '</td>';
            html += '<td>' + b.size_mb + ' MB</td>';
            html += '<td>' + b.created_at + '</td>';
            html += '<td>';
            html += '<button class="btn btn-sm btn-outline" onclick="downloadBackup(\'' + escapeHtml(b.filename) + '\')" title="下载">⬇️</button> ';
            html += '<button class="btn btn-sm btn-danger" onclick="deleteBackup(\'' + escapeHtml(b.filename) + '\')" title="删除">🗑️</button>';
            html += '</td>';
            html += '</tr>';
        }
        html += '</tbody></table>';
        container.innerHTML = html;
        updateRestoreSelect(backups);
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 网络错误: ' + e.message + '</div>';
    }
}

function updateRestoreSelect(backups) {
    var select = document.getElementById('restoreFileSelect');
    if (!select) return;
    select.innerHTML = '<option value="">请选择备份文件...</option>';
    for (var i = 0; i < backups.length; i++) {
        var opt = document.createElement('option');
        opt.value = backups[i].filename;
        opt.textContent = backups[i].filename + ' (' + backups[i].size_mb + ' MB)';
        select.appendChild(opt);
    }
}

async function createDbBackup() {
    var status = document.getElementById('backupOperationStatus');
    if (!status) return;
    status.innerHTML = '⏳ 正在创建备份...';
    try {
        var res = await fetch('/api/admin/backup/create-db', { method: 'POST' });
        var data = await res.json();
        status.innerHTML = data.success ? '✅ ' + data.message : '❌ ' + data.message;
        if (data.success) loadBackups();
    } catch (e) {
        status.innerHTML = '❌ 网络错误: ' + e.message;
    }
}

async function exportJsonData() {
    var status = document.getElementById('backupOperationStatus');
    if (!status) return;
    status.innerHTML = '⏳ 正在导出 JSON...';
    try {
        var res = await fetch('/api/admin/backup/export-json', { method: 'POST' });
        var data = await res.json();
        if (data.success && data.data) {
            var stats = data.data.stats || {};
            status.innerHTML = '✅ ' + data.message + ' （新闻:' + stats.news_count + ' 总结:' + stats.summaries_count + ' 频道:' + stats.channels_count + '）';
        } else {
            status.innerHTML = data.success ? '✅ ' + data.message : '❌ ' + data.message;
        }
        if (data.success) loadBackups();
    } catch (e) {
        status.innerHTML = '❌ 网络错误: ' + e.message;
    }
}

async function restoreFromDb() {
    var select = document.getElementById('restoreFileSelect');
    var status = document.getElementById('restoreStatus');
    if (!select || !status) return;
    var filename = select.value;
    if (!filename) {
        status.innerHTML = '⚠️ 请先选择一个备份文件';
        return;
    }
    if (!filename.endsWith('.db')) {
        status.innerHTML = '⚠️ 请选择 .db 数据库备份文件进行恢复';
        return;
    }
    if (!confirm('⚠️ 确定要从 ' + filename + ' 恢复数据库吗？\n\n当前数据将被覆盖，但系统会自动备份当前数据库以防万一。')) {
        return;
    }
    status.innerHTML = '⏳ 正在恢复...';
    try {
        var res = await fetch('/api/admin/backup/restore-db', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
        });
        var data = await res.json();
        status.innerHTML = data.success ? '✅ ' + data.message : '❌ ' + data.message;
        if (data.success) loadBackups();
    } catch (e) {
        status.innerHTML = '❌ 网络错误: ' + e.message;
    }
}

async function importFromJson() {
    var select = document.getElementById('restoreFileSelect');
    var status = document.getElementById('restoreStatus');
    if (!select || !status) return;
    var filename = select.value;
    if (!filename) {
        status.innerHTML = '⚠️ 请先选择一个备份文件';
        return;
    }
    if (!filename.endsWith('.json')) {
        status.innerHTML = '⚠️ 请选择 .json 文件进行导入';
        return;
    }
    if (!confirm('⚠️ 确定要从 ' + filename + ' 导入数据吗？\n\n将导入新闻、总结、频道等数据（已存在的记录将被跳过）。')) {
        return;
    }
    status.innerHTML = '⏳ 正在导入...';
    try {
        var res = await fetch('/api/admin/backup/import-json', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
        });
        var data = await res.json();
        if (data.success && data.data) {
            var parts = [];
            for (var key in data.data) {
                parts.push(data.data[key]);
            }
            status.innerHTML = '✅ ' + data.message + '<br><div style="margin-top:4px;font-size:12px;">' + parts.join('<br>') + '</div>';
        } else {
            status.innerHTML = data.success ? '✅ ' + data.message : '❌ ' + data.message;
        }
        if (data.success) loadBackups();
    } catch (e) {
        status.innerHTML = '❌ 网络错误: ' + e.message;
    }
}

async function deleteBackup(filename) {
    if (!confirm('确定要删除 ' + filename + ' 吗？')) return;
    try {
        var res = await fetch('/api/admin/backup/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
        });
        var data = await res.json();
        showToast(data.message, data.success ? 'success' : 'error');
        if (data.success) loadBackups();
    } catch (e) {
        showToast('网络错误: ' + e.message, 'error');
    }
}

function downloadBackup(filename) {
    window.open('/api/admin/backup/download/' + encodeURIComponent(filename), '_blank');
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>').replace(/"/g, '"').replace(/'/g, '&#039;');
}

// ======== 页面初始化 ========
document.addEventListener('DOMContentLoaded', function() {
    checkLogin();
});
