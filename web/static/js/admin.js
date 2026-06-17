let currentRange = '1d';
let isLoggedIn = false;

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

// ======== Tab 切换 ========
function switchTab(tab, btn) {
    document.querySelectorAll('.tabs .tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + tab).classList.add('active');
    if (tab === 'channels') {
        loadChannels();
        loadScrapeIntervalBar();
    }
    if (tab === 'settings') {
        loadScrapeInterval();
        loadAISettings();
    }
}

// ======== 初始化管理后台 ========
async function initAdmin() {
    loadStats();
    loadConfig();
    loadTags();
    loadSummaryPreview('1d');
    loadChannels();
    loadOverviewChannels();
    loadScrapeInterval();
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
            container.innerHTML = '<div class="empty">暂无订阅频道</div>';
            return;
        }
        let html = '<div class="table-wrap"><table><thead><tr><th>状态</th><th>频道名</th><th>URL</th></tr></thead><tbody>';
        channels.forEach(c => {
            const status = c.enabled ? '<span class="status-dot on"></span>正常' : '<span class="status-dot off"></span>已停用';
            html += `<tr>
                <td>${status}</td>
                <td><strong>${c.name}</strong></td>
                <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"><a href="${c.url}" target="_blank" style="color:#0f3460;font-size:12px;">${c.url}</a></td>
            </tr>`;
        });
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
            const d = data.data;
            let html = '';
            html += `<div class="config-row"><span class="config-label">📡 Web 服务</span><span class="config-value ok">🟢 运行中</span></div>`;
            html += `<div class="config-row"><span class="config-label">🔑 AI API Key</span><span class="config-value ${d.configured ? 'ok' : 'err'}">${d.configured ? '✅ 已配置' : '❌ 未配置'}</span></div>`;
            html += `<div class="config-row"><span class="config-label">🔗 AI Base URL</span><span class="config-value">${d.base_url || '-'}</span></div>`;
            html += `<div class="config-row"><span class="config-label">🤖 AI 模型</span><span class="config-value">${d.model || '-'}</span></div>`;
            html += `<div class="config-row"><span class="config-label">🌐 API 连接</span><span class="config-value ${d.connected ? 'ok' : 'err'}">${d.connected ? '✅ 正常' : '❌ 失败'}</span></div>`;
            html += `<div class="config-row"><span class="config-label">💾 总结缓存</span><span class="config-value ${d.summary_cached ? 'ok' : ''}">${d.summary_cached ? '✅ 已缓存' : '⏳ 未生成'}</span></div>`;
            if (d.summaries) {
                html += `<div style="margin-top:8px;font-size:12px;color:#999;">缓存详情：</div>`;
                for (const [k, v] of Object.entries(d.summaries)) {
                    const label = { '1d': '今日', '3d': '近3天', '1w': '近1周' }[k] || k;
                    html += `<div class="config-row" style="padding-left:20px;font-size:13px;">
                        <span class="config-label">${label}</span>
                        <span class="config-value">${v.cached ? '✅ ' + v.news_count + '条' : '⏳ 未生成'} ${v.generated_at ? '| '+new Date(v.generated_at).toLocaleString('zh-CN') : ''}</span>
                    </div>`;
                }
            }
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
            let html = '<div class="tag-list">';
            tags.forEach(tag => {
                const name = tag.name || tag;
                const count = tag.count ? ' <span class="count">(' + tag.count + ')</span>' : '';
                html += '<span class="tag-item">' + name + count + '</span>';
            });
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
async function loadChannels() {
    const container = document.getElementById('channelList');
    container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
    try {
        const res = await fetch('/api/admin/channels');
        const data = await res.json();
        if (!data.success) {
            if (data.need_login) { checkLogin(); return; }
            container.innerHTML = '<div class="error">❌ ' + (data.message || '加载失败') + '</div>';
            return;
        }
        const channels = data.data || [];
        if (channels.length === 0) {
            container.innerHTML = '<div class="empty">暂无订阅频道，请在上方添加</div>';
            return;
        }
        let html = '<div class="table-wrap"><table><thead><tr><th>启用</th><th>频道名</th><th>URL</th><th>添加时间</th><th>操作</th></tr></thead><tbody>';
        channels.forEach(c => {
            const timeStr = c.created_at ? new Date(c.created_at).toLocaleString('zh-CN') : '-';
            html += '<tr>' +
                '<td><label class="toggle"><input type="checkbox" ' + (c.enabled ? 'checked' : '') + ' onchange="toggleChannel(\'' + c.id + '\', this.checked)"><span class="slider"></span></label></td>' +
                '<td><strong>' + c.name + '</strong></td>' +
                '<td style="max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"><a href="' + c.url + '" target="_blank" style="color:#0f3460;">' + c.url + '</a></td>' +
                '<td style="font-size:12px;color:#999;">' + timeStr + '</td>' +
                '<td><button class="btn btn-danger btn-xs" onclick="removeChannel(\'' + c.id + '\',\'' + c.name + '\')">删除</button></td>' +
                '</tr>';
        });
        html += '</tbody></table></div>';
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 网络错误</div>';
    }
}

async function addChannel() {
    const input = document.getElementById('channelUrl');
    const url = input.value.trim();
    if (!url) { showToast('❌ 请输入频道 URL', 'error'); return; }
    if (!url.startsWith('https://t.me/s/')) { showToast('❌ URL 格式错误，应为 https://t.me/s/频道名', 'error'); return; }
    try {
        const res = await fetch('/api/admin/channels/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ 已添加频道: ' + data.data?.name, 'success');
            input.value = '';
            loadChannels();
            loadStats();
        } else {
            showToast('❌ ' + (data.message || '添加失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    }
}

async function removeChannel(id, name) {
    if (!confirm('确定要删除频道 "' + name + '" 吗？')) return;
    try {
        const res = await fetch('/api/admin/channels/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ ' + data.message, 'success');
            loadChannels();
            loadStats();
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
        if (!data.success) {
            showToast('❌ ' + (data.message || '操作失败'), 'error');
            loadChannels();
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
        loadChannels();
    }
}

// ======== AI 总结 ========
async function loadSummaryPreview(range) {
    const container = document.getElementById('aiSummaryPreview');
    container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
    try {
        const res = await fetch('/api/ai/summary?range=' + range);
        const data = await res.json();
        if (data.success && data.data && data.data.content) {
            const html = data.data.content;
            const labels = { '1d': '今日', '3d': '近3天', '1w': '近1周' };
            const info = '📊 ' + (labels[range] || range) + '总结 | ' + data.data.news_count + ' 条新闻 | ' + (data.data.generated_at ? new Date(data.data.generated_at).toLocaleString('zh-CN') : '-');
            container.innerHTML = '<div style="font-size:12px;color:#999;margin-bottom:8px;">' + info + '</div><div class="summary-content">' + html + '</div>';
        } else {
            container.innerHTML = '<div class="empty">⏳ 该时间范围尚未生成总结，点击"刷新"按钮生成</div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 加载失败</div>';
    }
}

function switchRange(range, btn) {
    currentRange = range;
    document.querySelectorAll('.range-tab').forEach(function(t) { t.classList.remove('active'); });
    btn.classList.add('active');
    loadSummaryPreview(range);
}

async function manualRefresh() {
    var btns = [document.getElementById('refreshSumBtn')];
    btns.forEach(function(b) { if(b) { b.disabled = true; b.textContent = '⏳ 生成中...'; } });
    var rangeLabel = ({'1d':'今日','3d':'近3天','1w':'近1周'})[currentRange] || currentRange;
    showLog('🤖 开始生成 ' + rangeLabel + ' AI 总结...');
    try {
        var res = await fetch('/api/ai/summary/refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ range: currentRange })
        });
        var data = await res.json();
        if (data.success) {
            appendLog('✅ ' + rangeLabel + ' 总结生成成功！共 ' + (data.data?.news_count || 0) + ' 条新闻');
            loadSummaryPreview(currentRange);
            loadConfig();
        } else {
            appendLog('❌ 生成失败: ' + (data.message || '未知错误'));
        }
    } catch (e) {
        appendLog('❌ 网络错误: ' + e.message);
    } finally {
        btns.forEach(function(b) { if(b) { b.disabled = false; b.textContent = ' 刷新'; } });
    }
}

// ======== 手动操作 ========
async function manualScrape() {
    var btn = document.getElementById('scrapeBtn');
    btn.disabled = true;
    btn.textContent = '⏳ 抓取中...';
    showLog('🔍 开始手动抓取 Telegram 频道...');
    try {
        var res = await fetch('/api/admin/scrape/trigger', { method: 'POST' });
        var data = await res.json();
        if (data.success) {
            appendLog('✅ ' + data.message);
            loadStats();
        } else if (data.need_channel) {
            appendLog('⚠️ ' + data.message);
            showToast(data.message, 'warning');
            // 切换到频道管理 Tab 方便用户添加
            var channelTab = document.querySelector('.tabs .tab:nth-child(2)');
            if (channelTab) channelTab.click();
        } else {
            appendLog('❌ ' + (data.message || '抓取失败'));
        }
    } catch (e) {
        appendLog('❌ 网络错误: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '🔍 手动抓取 Telegram';
    }
}

async function manualCleanup() {
    var btn = document.getElementById('cleanupBtn');
    if (!confirm('确定要清理重复新闻吗？')) return;
    btn.disabled = true;
    btn.textContent = '⏳ 清理中...';
    showLog('🧹 开始清理重复新闻...');
    try {
        var res = await fetch('/api/admin/cleanup', { method: 'POST' });
        var data = await res.json();
        if (data.success) {
            appendLog('✅ 清理完成！移除了 ' + (data.count || data.data?.removed || 0) + ' 条重复新闻');
            loadStats();
        } else {
            appendLog('❌ 清理失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        appendLog('❌ 网络错误: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '🧹 清理重复新闻';
    }
}

// ======== 频道 Tab 抓取频率 ========
async function loadScrapeIntervalBar() {
    var container = document.getElementById('scrapeIntervalBar');
    if (!container) return;
    container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
    try {
        var res = await fetch('/api/admin/settings');
        var data = await res.json();
        if (data.success) {
            var settings = data.data || {};
            var interval = settings.scrape_interval_minutes || '30';
            var html = '<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">' +
                '<span style="font-size:15px;">⏱ 当前抓取间隔：<strong>' + interval + '</strong> 分钟</span>' +
                '<button class="btn btn-warning btn-sm" onclick="showUpdateIntervalModal()">⚙️ 修改</button>' +
                '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="error">❌ 加载失败</div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 网络错误</div>';
    }
}

// ======== 设置 ========
async function loadScrapeInterval() {
    var container = document.getElementById('scrapeSettings');
    if (!container) return;
    container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
    try {
        var res = await fetch('/api/admin/settings');
        var data = await res.json();
        if (data.success) {
            var settings = data.data || {};
            var interval = settings.scrape_interval_minutes || '30';
            var html = '<div class="config-row"><span class="config-label">⏱ 抓取间隔（分钟）</span><span class="config-value">' + interval + ' 分钟</span></div>';
            if (settings.tg_bot_token) {
                html += '<div class="config-row"><span class="config-label">🤖 Telegram Bot Token</span><span class="config-value">' + settings.tg_bot_token.substring(0, 8) + '...' + settings.tg_bot_token.substring(settings.tg_bot_token.length - 4) + '</span></div>';
            }
            html += '<div class="config-row"><span class="config-label">🔑 Admin 密码</span><span class="config-value">' + (settings.admin_password ? '✅ 已设置' : '❌ 未设置') + '</span></div>';
            html += '<div class="action-row"><button class="btn btn-warning btn-sm" onclick="showUpdateIntervalModal()">⚙️ 修改间隔</button></div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="error">❌ 加载设置失败</div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 网络错误</div>';
    }
}

function showUpdateIntervalModal() {
    document.getElementById('intervalModal').classList.add('active');
    document.getElementById('intervalInput').value = '';
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

async function saveInterval() {
    var input = document.getElementById('intervalInput');
    var val = parseInt(input.value);
    if (!val || val < 1) { showToast('❌ 请输入有效的分钟数（≥1）', 'error'); return; }
    try {
        var res = await fetch('/api/admin/settings/interval', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ interval: val })
        });
        var data = await res.json();
        if (data.success) {
            showToast('✅ 抓取间隔已更新为 ' + val + ' 分钟', 'success');
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

// ======== AI API 设置 ========
async function loadAISettings() {
    var container = document.getElementById('aiSettings');
    if (!container) return;
    container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
    try {
        var res = await fetch('/api/ai/status');
        var data = await res.json();
        if (data.success) {
            var d = data.data;
            var html = '<div style="max-width:500px;">';
            html += '<div class="form-group"><label>API Key</label>' +
                '<input type="password" class="input-text" id="aiApiKey" placeholder="输入 API Key" value="' + (d.api_key || '') + '">' +
                '<div style="font-size:11px;color:#999;margin-top:4px;">' + (d.configured ? '当前: ' + d.api_key : '未配置') + '</div></div>';
            html += '<div class="form-group" style="margin-top:10px;"><label>Base URL</label>' +
                '<input type="text" class="input-text" id="aiBaseUrl" placeholder="https://api.example.com/v1" value="' + (d.base_url || '') + '"></div>';
            html += '<div class="form-group" style="margin-top:10px;"><label>模型名称</label>' +
                '<input type="text" class="input-text" id="aiModel" placeholder="模型名称" value="' + (d.model || '') + '"></div>';
            html += '<div style="margin-top:4px;font-size:11px;color:#999;">连接状态: ' + (d.connected ? '✅ 正常' : '❌ 失败') + '</div>';
            html += '<button class="btn btn-primary" onclick="saveAISettings()" style="margin-top:12px;" id="saveAiBtn">💾 保存 AI 设置</button>';
            html += '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="error">❌ 加载 AI 设置失败</div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 网络错误</div>';
    }
}

async function saveAISettings() {
    var btn = document.getElementById('saveAiBtn');
    btn.disabled = true;
    btn.textContent = '⏳ 保存中...';
    var apiKey = document.getElementById('aiApiKey').value.trim();
    var baseUrl = document.getElementById('aiBaseUrl').value.trim();
    var model = document.getElementById('aiModel').value.trim();
    if (!baseUrl) { showToast('❌ 请输入 Base URL', 'error'); btn.disabled = false; btn.textContent = '💾 保存 AI 设置'; return; }
    if (!model) { showToast('❌ 请输入模型名称', 'error'); btn.disabled = false; btn.textContent = '💾 保存 AI 设置'; return; }
    try {
        var res = await fetch('/api/admin/ai/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey, base_url: baseUrl, model: model })
        });
        var data = await res.json();
        if (data.success) {
            showToast('✅ AI 设置已更新', 'success');
            loadAISettings();
            loadConfig();
        } else {
            showToast('❌ ' + (data.message || '保存失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '💾 保存 AI 设置';
    }
}

// ======== 日志增强 ========
function showLog(msg) {
    var el = document.getElementById('logBox');
    if (!el) return;
    var card = document.getElementById('logCard');
    if (card) card.style.display = 'block';
    el.innerHTML += '<div class="log-info">' + msg + '</div>';
    el.scrollTop = el.scrollHeight;
}

function appendLog(msg) {
    showLog(msg);
}

// ======== Toast ========
function showToast(msg, type) {
    var existing = document.querySelector('.toast');
    if (existing) existing.remove();
    var toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 3000);
}

// ======== 初始化 ========
document.addEventListener('DOMContentLoaded', checkLogin);
