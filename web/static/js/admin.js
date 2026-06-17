let currentRange = '1d';
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
                setTimeout(() => {
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
            body: JSON.stringify({ url })
        });
        const data = await res.json();
        if (data.success) {
            const name = data.data?.name || url.split('/').pop();
            firstRunChannelsAdded.push({ url, name });
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
    let html = '<div style="background:#f6ffed;padding:10px;border-radius:6px;border:1px solid #b7eb8f;">';
    html += '<div style="font-size:13px;font-weight:600;margin-bottom:6px;">✅ 已添加的频道：</div>';
    firstRunChannelsAdded.forEach((c, i) => {
        html += '<div style="font-size:12px;padding:2px 0;">' + (i+1) + '. ' + c.name + '</div>';
    });
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
    loadSummaryPreview('today');
    loadChannels();
    loadOverviewChannels();
    loadScrapeInterval();
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
        let html = '<div class="table-wrap"><table><thead><tr><th>状态</th><th>频道名</th><th>URL</th></tr></thead><tbody>';
        channels.forEach(c => {
            const status = c.enabled ? '<span class="status-dot on"></span>正常' : '<span class="status-dot off"></span>已停用';
            html += '<tr><td>' + status + '</td><td><strong>' + c.name + '</strong></td><td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"><a href="' + c.url + '" target="_blank" style="color:#0f3460;font-size:12px;">' + c.url + '</a></td></tr>';
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
            container.innerHTML = '<div class="empty">暂无订阅频道，请输入上方 URL 添加</div>';
            return;
        }
        let html = '<div class="table-wrap"><table><thead><tr><th>启用</th><th>频道名</th><th>URL</th><th>历史回填条数</th><th>添加时间</th><th>操作</th></tr></thead><tbody>';
        channels.forEach(c => {
            const timeStr = c.created_at ? new Date(c.created_at).toLocaleString('zh-CN') : '-';
            html += '<tr>' +
                '<td><label class="toggle"><input type="checkbox" ' + (c.enabled ? 'checked' : '') + ' onchange="toggleChannel(\'' + c.id + '\', this.checked)"><span class="slider"></span></label></td>' +
                '<td><strong>' + c.name + '</strong></td>' +
                '<td style="max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"><a href="' + c.url + '" target="_blank" style="color:#0f3460;">' + c.url + '</a></td>' +
                '<td style="font-size:12px;color:#999;">' + (c.scrape_depth || 0) + ' 条</td>' +
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
    const depthInput = document.getElementById('channelScrapeDepth');
    const url = input.value.trim();
    const scrape_depth = parseInt(depthInput.value) || 1000;
    if (!url) { showToast('❌ 请输入频道 URL', 'error'); return; }
    if (!url.startsWith('https://t.me/s/')) { showToast('❌ URL 格式错误，应为 https://t.me/s/频道名', 'error'); return; }
    try {
        const res = await fetch('/api/admin/channels/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, scrape_depth })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ 已添加频道: ' + data.data?.name, 'success');
            input.value = '';
            loadChannels();
            loadStats();
            checkChannelWarning();
        } else {
            showToast('❌ ' + (data.message || '添加失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    }
}

async function removeChannel(id, name) {
    if (!confirm('⚠️ 确定要删除频道 "' + name + '" 吗？\n\n此操作将同时删除该频道下的所有新闻数据，不可恢复！')) return;
    try {
        const res = await fetch('/api/admin/channels/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        });
        const data = await res.json();
        if (data.success) {
            const deletedNews = data.deleted_news || 0;
            showToast('✅ 频道已删除，已清理 ' + deletedNews + ' 条关联新闻', 'success');
            loadChannels();
            loadStats();
            checkChannelWarning();
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
            body: JSON.stringify({ id, enabled })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ ' + data.message, 'success');
        } else {
            showToast('❌ ' + (data.message || '操作失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    }
}

// ======== 抓取间隔控制 ========
async function loadScrapeInterval() {
    const container = document.getElementById('scrapeSettings');
    try {
        const res = await fetch('/api/admin/settings');
        const data = await res.json();
        if (data.success) {
            const settings = data.data;
            const interval = settings.scrape_interval_minutes || '30';
            container.innerHTML = `
                <div class="config-row">
                    <span class="config-label">⏱️ 自动抓取间隔</span>
                    <span class="config-value">每 <strong>${interval}</strong> 分钟</span>
                    <button class="btn btn-outline btn-sm" onclick="openModal('intervalModal')" style="margin-left:12px;">修改</button>
                </div>
                <div class="config-row">
                    <span class="config-label">📡 定时抓取</span>
                    <span class="config-value ${settings.scheduler_running ? 'ok' : 'err'}">${settings.scheduler_running ? '✅ 运行中' : '❌ 未启动'}</span>
                </div>
            `;
        }
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 加载失败</div>';
    }
}

async function loadScrapeIntervalBar() {
    const container = document.getElementById('scrapeIntervalBar');
    try {
        const res = await fetch('/api/admin/settings');
        const data = await res.json();
        if (data.success) {
            const settings = data.data;
            const interval = settings.scrape_interval_minutes || '30';
            container.innerHTML = `
                <div class="config-row">
                    <span class="config-label">⏱️ 当前抓取间隔</span>
                    <span class="config-value">每 <strong>${interval}</strong> 分钟</span>
                    <button class="btn btn-outline btn-sm" onclick="openModal('intervalModal')" style="margin-left:12px;">修改</button>
                </div>
                <div class="config-row">
                    <span class="config-label">📡 定时任务状态</span>
                    <span class="config-value ${settings.scheduler_running ? 'ok' : 'err'}">${settings.scheduler_running ? '✅ 运行中' : '❌ 未启动'}</span>
                </div>
            `;
        }
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 加载失败</div>';
    }
}

function setIntervalPreset(minutes) {
    document.getElementById('intervalInput').value = minutes;
}

async function saveInterval() {
    const input = document.getElementById('intervalInput');
    const interval = parseInt(input.value);
    if (!interval || interval < 1) {
        showToast('❌ 请输入有效的间隔分钟数', 'error');
        return;
    }
    try {
        const res = await fetch('/api/admin/settings/interval', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ interval })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ ' + data.message, 'success');
            closeModal('intervalModal');
            loadScrapeInterval();
            loadScrapeIntervalBar();
        } else {
            showToast('❌ ' + (data.message || '保存失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    }
}

// ======== AI 设置 ========
async function loadAISettings() {
    const container = document.getElementById('aiSettings');
    container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
    try {
        const res = await fetch('/api/ai/status');
        const data = await res.json();
        if (data.success) {
            const d = data.data;
            container.innerHTML = `
                <div style="max-width:500px;">
                    <div class="form-group">
                        <label class="form-label">🤖 AI Base URL</label>
                        <input type="text" class="input-text" id="aiBaseUrl" value="${d.base_url || ''}" placeholder="https://api.openai.com/v1">
                    </div>
                    <div class="form-group" style="margin-top:10px;">
                        <label class="form-label">🔑 API Key</label>
                        <div style="display:flex;gap:8px;">
                            <input type="password" class="input-text" id="aiApiKey" value="${d.api_key || ''}" placeholder="sk-..." style="flex:1;" autocomplete="off">
                            <button class="btn btn-outline btn-sm" onclick="toggleAIApiKeyVisibility()" id="toggleApiKeyBtn">👁️</button>
                        </div>
                    </div>
                    <div class="form-group" style="margin-top:10px;">
                        <label class="form-label">📝 模型名称</label>
                        <input type="text" class="input-text" id="aiModel" value="${d.model || ''}" placeholder="gpt-4o-mini / deepseek-chat">
                    </div>
                    <div style="margin-top:12px;display:flex;gap:8px;">
                        <button class="btn btn-primary" onclick="saveAISettings()">💾 保存设置</button>
                        <button class="btn btn-success" onclick="testAIConnection()" id="testAiBtn">🔗 测试连接</button>
                    </div>
                    <div id="aiTestResult" style="margin-top:10px;font-size:13px;"></div>
                    <div style="margin-top:12px;padding:10px;background:#e6f7ff;border-radius:6px;border:1px solid #91d5ff;font-size:13px;">
                        <strong>💡 支持的 AI 服务：</strong>
                        <ul style="margin:5px 0 0 15px;padding:0;">
                            <li>OpenAI (api.openai.com) - gpt-4o-mini, gpt-4o</li>
                            <li>DeepSeek (api.deepseek.com) - deepseek-chat</li>
                            <li>通义千问 (dashscope.aliyuncs.com) - qwen-plus</li>
                            <li>任何兼容 OpenAI API 的服务</li>
                        </ul>
                    </div>
                </div>
            `;
        } else {
            container.innerHTML = '<div class="error">❌ 加载失败</div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="error">❌ 网络错误</div>';
    }
}

function toggleAIApiKeyVisibility() {
    const input = document.getElementById('aiApiKey');
    const btn = document.getElementById('toggleApiKeyBtn');
    if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = '🙈';
    } else {
        input.type = 'password';
        btn.textContent = '👁️';
    }
}

async function saveAISettings() {
    const base_url = document.getElementById('aiBaseUrl').value.trim();
    const api_key = document.getElementById('aiApiKey').value.trim();
    const model = document.getElementById('aiModel').value.trim();
    if (!base_url) { showToast('❌ 请输入 AI Base URL', 'error'); return; }
    if (!api_key) { showToast('❌ 请输入 API Key', 'error'); return; }
    try {
        const res = await fetch('/api/ai/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ base_url, api_key, model })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ AI 设置已保存', 'success');
            loadConfig();
        } else {
            showToast('❌ ' + (data.message || '保存失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    }
}

async function testAIConnection() {
    const btn = document.getElementById('testAiBtn');
    const resultDiv = document.getElementById('aiTestResult');
    btn.disabled = true;
    btn.textContent = '⏳ 测试中...';
    resultDiv.innerHTML = '';
    try {
        const res = await fetch('/api/ai/test', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            resultDiv.innerHTML = '<span style="color:#52c41a;">✅ ' + (data.message || '连接成功') + '</span>';
        } else {
            resultDiv.innerHTML = '<span style="color:#ff4d4f;">❌ ' + (data.message || '连接失败') + '</span>';
        }
    } catch (e) {
        resultDiv.innerHTML = '<span style="color:#ff4d4f;">❌ 网络错误: ' + e.message + '</span>';
    } finally {
        btn.disabled = false;
        btn.textContent = '🔗 测试连接';
    }
}

// ======== 密码修改 ========
async function changePwd() {
    const oldPwd = document.getElementById('oldPassword').value;
    const newPwd = document.getElementById('newPassword').value;
    if (!oldPwd) { showToast('❌ 请输入原密码', 'error'); return; }
    if (!newPwd || newPwd.length < 4) { showToast('❌ 新密码至少 4 位', 'error'); return; }
    try {
        const res = await fetch('/api/admin/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_password: oldPwd, new_password: newPwd })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ 密码已修改', 'success');
            document.getElementById('oldPassword').value = '';
            document.getElementById('newPassword').value = '';
        } else {
            showToast('❌ ' + (data.message || '修改失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 网络错误: ' + e.message, 'error');
    }
}

// ======== AI 总结预览（管理后台 AI 总结 Tab）=======
async function loadSummaryPreview(range) {
    const container = document.getElementById('aiSummaryPreview');
    if (!container) return;
    container.innerHTML = '<div class="loading">⏳ 加载中...</div>';
    
    const endpointMap = {
        'today': '/api/summary/today',
        'yesterday': '/api/summary/yesterday',
        '3d': '/api/summary/3d',
        '1w': '/api/summary/1w'
    };
    const url = endpointMap[range];
    if (!url) { container.innerHTML = '<div class="error">无效的时间范围</div>'; return; }
    
    try {
        const res = await fetch(url);
        const data = await res.json();
        if (data.success && data.data) {
            const summary = data.data;
            let html = summary.content
                .replace(/### /g, '<h3>').replace(/#### /g, '<h4>')
                .replace(/- /g, '<li>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>');
            html = html.replace(/<li>/g, '<ul><li>').replace(/<\/li>/g, '</li></ul>').replace(/<\/ul><ul>/g, '');
            container.innerHTML = html;
            // 显示生成时间
            const nowEl = document.createElement('div');
            nowEl.style.cssText = 'margin-top:15px;padding-top:10px;border-top:1px solid #eee;font-size:12px;color:#999;';
            nowEl.textContent = '🕐 生成于: ' + (summary.generated_at || '-') + ' | 基于 ' + (summary.news_count || 0) + ' 条新闻';
            container.appendChild(nowEl);
        } else {
            container.innerHTML = '<div class="ai-summary-empty">暂无总结，点击"刷新"按钮生成</div>';
        }
    } catch (e) {
        console.error('loadSummaryPreview:', e);
        container.innerHTML = '<div class="ai-summary-error">❌ 加载失败</div>';
    }
}

function switchRange(range, btn) {
    document.querySelectorAll('.range-tabs .range-tab').forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');
    currentRange = range;
    loadSummaryPreview(range);
}

async function manualRefresh() {
    let range = currentRange || 'today';
    const container = document.getElementById('aiSummaryPreview');
    if (container) container.innerHTML = '<div class="loading">⏳ 生成中...</div>';
    
    const endpointMap = {
        'today': '/api/summary/today',
        'yesterday': '/api/summary/yesterday',
        '3d': '/api/summary/3d',
        '1w': '/api/summary/1w'
    };
    const url = endpointMap[range];
    if (!url) return;
    
    try {
        await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ force: true })
        });
        setTimeout(() => loadSummaryPreview(range), 1000);
    } catch (e) {
        console.error(e);
        if (container) container.innerHTML = '<div class="ai-summary-error">❌ 刷新失败</div>';
    }
}

// ======== 手动操作 ========
async function manualScrape() {
    const btn = document.getElementById('scrapeBtn');
    const log = document.getElementById('operationLog');
    btn.disabled = true;
    btn.textContent = '⏳ 抓取中...';
    log.style.display = 'block';
    log.innerHTML += '<div>⏳ 开始手动抓取...</div>';
    try {
        const res = await fetch('/api/admin/scrape', { method: 'POST' });
        const data = await res.json();
        log.innerHTML += '<div>' + (data.success ? '✅' : '❌') + ' ' + (data.message || '完成') + '</div>';
        if (data.success) {
            loadStats();
            showToast('✅ 抓取完成', 'success');
        } else {
            showToast('❌ ' + (data.message || '抓取失败'), 'error');
        }
    } catch (e) {
        log.innerHTML += '<div>❌ 网络错误</div>';
        showToast('❌ 网络错误', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🔍 手动抓取 Telegram';
    }
}

async function manualCleanup() {
    if (!confirm('确定要清理旧数据吗？该操作将删除 7 天前的新闻。')) return;
    const btn = document.getElementById('cleanupBtn');
    const log = document.getElementById('operationLog');
    btn.disabled = true;
    btn.textContent = '⏳ 清理中...';
    log.style.display = 'block';
    log.innerHTML += '<div>⏳ 开始清理旧数据...</div>';
    try {
        const res = await fetch('/api/admin/cleanup', { method: 'POST' });
        const data = await res.json();
        log.innerHTML += '<div>' + (data.success ? '✅' : '❌') + ' ' + (data.message || '完成') + '</div>';
        if (data.success) {
            loadStats();
            showToast('✅ 清理完成', 'success');
        } else {
            showToast('❌ ' + (data.message || '清理失败'), 'error');
        }
    } catch (e) {
        log.innerHTML += '<div>❌ 网络错误</div>';
        showToast('❌ 网络错误', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🧹 清理旧数据';
    }
}

// ======== 模态框 ========
function openModal(id) {
    document.getElementById(id).classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

// ======== Toast 提示 ========
function showToast(message, type) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.className = 'toast ' + (type || 'info');
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => { toast.classList.add('show'); }, 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ======== 键盘事件 ========
document.addEventListener('DOMContentLoaded', function() {
    checkLogin();
});