/* ============================================================
   AI Hackathon 智能评审系统 - 前端逻辑
   ============================================================ */

const API_BASE = '/api/v1';
let currentPage = 'dashboard';
let cachedData = {};

/* -------------------- 初始化 -------------------- */
document.addEventListener('DOMContentLoaded', () => {
    initRouter();
    checkHealth();
    setInterval(checkHealth, 30000);
});

/* -------------------- 路由 -------------------- */
function initRouter() {
    const links = document.querySelectorAll('.nav-link');
    links.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = link.dataset.page;
            navigateTo(page);
        });
    });

    // 默认页面
    navigateTo('dashboard');
}

function navigateTo(page) {
    currentPage = page;

    // 更新导航高亮
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    document.querySelector(`.nav-link[data-page="${page}"]`)?.classList.add('active');

    // 更新标题
    const titles = {
        dashboard: 'Dashboard',
        teams: '队伍管理',
        submit: '提交作品',
        leaderboard: '排行榜',
        submissions: '作品列表',
    };
    document.getElementById('page-title').textContent = titles[page] || page;

    // 渲染页面
    const content = document.getElementById('content');
    content.innerHTML = '<div class="loading"><div class="spinner"></div>加载中...</div>';

    switch (page) {
        case 'dashboard': renderDashboard(); break;
        case 'teams': renderTeams(); break;
        case 'submit': renderSubmit(); break;
        case 'leaderboard': renderLeaderboard(); break;
        case 'submissions': renderSubmissions(); break;
        default: renderDashboard();
    }
}

/* -------------------- Dashboard -------------------- */
async function renderDashboard() {
    try {
        const [teamsRes, subsRes, healthRes] = await Promise.all([
            fetch(`${API_BASE}/teams?page_size=1`),
            fetch(`${API_BASE}/submissions?page_size=1`),
            fetch(`${API_BASE}/health`),
        ]);

        const teams = await teamsRes.json();
        const subs = await subsRes.json();
        const health = await healthRes.json();

        const completed = subs.items?.filter(s => s.status === 'completed').length || 0;
        const pending = subs.items?.filter(s => s.status === 'pending').length || 0;

        document.getElementById('content').innerHTML = `
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-label">参赛队伍</div>
                    <div class="stat-value">${teams.total || 0}</div>
                    <div class="stat-sub">已注册队伍总数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">作品提交</div>
                    <div class="stat-value">${subs.total || 0}</div>
                    <div class="stat-sub">已完成 ${completed} / 待评审 ${pending}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">赛题数量</div>
                    <div class="stat-value">7</div>
                    <div class="stat-sub">覆盖 functional / agent / system</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">系统状态</div>
                    <div class="stat-value" style="font-size:18px;color:${health.status === 'ok' ? 'var(--color-success)' : 'var(--color-danger)'};padding-top:4px;">
                        ${health.status === 'ok' ? '运行正常' : '异常'}
                    </div>
                    <div class="stat-sub">${health.components?.database || '?'} · ${health.components?.redis || '?'}</div>
                </div>
            </div>

            <div class="dashboard-grid">
                <div class="card">
                    <div class="card-header"><h2>最近提交</h2></div>
                    <div class="card-body" id="recent-submissions">
                        ${renderRecentSubmissions(subs.items || [])}
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>赛题分布</h2></div>
                    <div class="card-body">
                        <div style="display:flex;flex-direction:column;gap:12px;">
                            ${[1,2,3,4,5,6,7].map(q => `
                                <div style="display:flex;align-items:center;justify-content:space-between;">
                                    <span style="font-size:13px;">Q${q}</span>
                                    <span class="tag tag-muted">${getQuestionTitle(q)}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;
    } catch (e) {
        showError('加载 Dashboard 失败: ' + e.message);
    }
}

function renderRecentSubmissions(items) {
    if (!items.length) {
        return '<div class="empty-state"><div class="empty-icon">📭</div><h3>暂无提交</h3><p>作品提交后将在此显示</p></div>';
    }
    return items.slice(0, 5).map(s => `
        <div class="recent-item" onclick="showSubmissionDetail('${s.id}')">
            <div class="recent-item-info">
                <div class="recent-item-title">作品 #${s.submission_version} - Q${s.question_id}</div>
                <div class="recent-item-meta">${formatTime(s.submitted_at)} · ${formatStatus(s.status)}</div>
            </div>
            ${s.status === 'completed'
                ? `<span class="score-badge score-mid">${Math.round(s.final_score?.total_score || 0)}</span>`
                : `<span class="tag tag-muted">评审中</span>`}
        </div>
    `).join('');
}

function getQuestionTitle(id) {
    const titles = {
        1: '招投标聚合', 2: '文件整理', 3: '嵌入式AI', 4: 'Agent记忆',
        5: 'PPT检索', 6: '示意图生成', 7: 'Rust重构',
    };
    return titles[id] || `Q${id}`;
}

/* -------------------- Teams -------------------- */
async function renderTeams() {
    document.getElementById('content').innerHTML = `
        <div class="card">
            <div class="card-header">
                <h2>注册新队伍</h2>
            </div>
            <div class="card-body">
                <div id="team-alert" class="alert"></div>
                <form id="team-form" onsubmit="handleCreateTeam(event)">
                    <div class="form-group">
                        <label>队伍编号 <span class="required">*</span></label>
                        <input type="text" name="team_code" placeholder="如 T001" required>
                    </div>
                    <div class="form-group">
                        <label>队伍名称 <span class="required">*</span></label>
                        <input type="text" name="team_name" placeholder="队伍名称" required>
                    </div>
                    <div class="form-group">
                        <label>联系邮箱</label>
                        <input type="email" name="contact_email" placeholder="team@example.com">
                    </div>
                    <button type="submit" class="btn btn-primary">注册队伍</button>
                </form>
            </div>
        </div>

        <div class="card">
            <div class="card-header"><h2>队伍列表</h2></div>
            <div class="card-body" id="teams-list">
                <div class="loading"><div class="spinner"></div>加载中...</div>
            </div>
        </div>
    `;

    try {
        const res = await fetch(`${API_BASE}/teams`);
        const data = await res.json();
        document.getElementById('teams-list').innerHTML = renderTeamsTable(data.items || []);
    } catch (e) {
        document.getElementById('teams-list').innerHTML = `<div class="alert alert-error show">加载失败: ${e.message}</div>`;
    }
}

function renderTeamsTable(teams) {
    if (!teams.length) return '<div class="empty-state"><div class="empty-icon">👥</div><h3>暂无队伍</h3></div>';

    return `
        <div class="table-container">
            <table>
                <thead><tr><th>编号</th><th>名称</th><th>联系邮箱</th><th>注册时间</th></tr></thead>
                <tbody>
                    ${teams.map(t => `
                        <tr>
                            <td><code>${t.team_code}</code></td>
                            <td><strong>${t.team_name}</strong></td>
                            <td>${t.contact_email || '-'}</td>
                            <td style="color:var(--color-text-muted)">${formatTime(t.created_at)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

async function handleCreateTeam(e) {
    e.preventDefault();
    const form = e.target;
    const data = {
        team_code: form.team_code.value,
        team_name: form.team_name.value,
        contact_email: form.contact_email.value,
    };

    try {
        const res = await fetch(`${API_BASE}/teams`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (res.ok) {
            showAlert('team-alert', '队伍注册成功！', 'success');
            form.reset();
            setTimeout(() => renderTeams(), 500);
        } else {
            const err = await res.json();
            showAlert('team-alert', err.detail || '注册失败', 'error');
        }
    } catch (e) {
        showAlert('team-alert', '网络错误: ' + e.message, 'error');
    }
}

/* -------------------- Submit -------------------- */
async function renderSubmit() {
    try {
        const [teamsRes, questionsRes] = await Promise.all([
            fetch(`${API_BASE}/teams?page_size=100`),
            fetch(`${API_BASE}/questions`),
        ]);
        const teams = await teamsRes.json();
        const questions = await questionsRes.json();

        cachedData.teams = teams.items || [];
        cachedData.questions = questions || [];

        document.getElementById('content').innerHTML = `
            <div class="card" style="max-width:600px;">
                <div class="card-header"><h2>提交参赛作品</h2></div>
                <div class="card-body">
                    <div id="submit-alert" class="alert"></div>
                    <form id="submit-form" onsubmit="handleSubmitWork(event)">
                        <div class="form-group">
                            <label>选择队伍 <span class="required">*</span></label>
                            <select name="team_id" required>
                                <option value="">请选择队伍</option>
                                ${cachedData.teams.map(t => `<option value="${t.id}">${t.team_code} - ${t.team_name}</option>`).join('')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>选择赛题 <span class="required">*</span></label>
                            <select name="question_id" required>
                                <option value="">请选择赛题</option>
                                ${cachedData.questions.map(q => `<option value="${q.id}">Q${q.id} - ${q.title}</option>`).join('')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>作品文件 <span class="required">*</span></label>
                            <input type="file" name="file" accept=".zip,.tar.gz,.tgz" required>
                            <p style="font-size:12px;color:var(--color-text-muted);margin-top:4px;">支持 ZIP 或 TAR.GZ 格式，最大 500MB</p>
                        </div>
                        <div class="form-group">
                            <label>作品说明</label>
                            <textarea name="description" rows="3" placeholder="简要描述作品功能和亮点"></textarea>
                        </div>
                        <button type="submit" class="btn btn-primary">提交作品</button>
                    </form>
                </div>
            </div>
        `;
    } catch (e) {
        showError('加载失败: ' + e.message);
    }
}

async function handleSubmitWork(e) {
    e.preventDefault();
    const form = e.target;
    const file = form.file.files[0];
    if (!file) { showAlert('submit-alert', '请选择文件', 'error'); return; }

    const formData = new FormData();
    formData.append('team_id', form.team_id.value);
    formData.append('question_id', form.question_id.value);
    formData.append('file', file);
    if (form.description.value) formData.append('description', form.description.value);

    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width:14px;height:14px;border-width:2px;display:inline-block;vertical-align:middle;margin-right:6px;"></div>上传中...';

    try {
        const res = await fetch(`${API_BASE}/submissions`, { method: 'POST', body: formData });
        if (res.ok) {
            const data = await res.json();
            showAlert('submit-alert', `提交成功！作品ID: ${data.id}，评审任务已创建`, 'success');
            form.reset();
        } else {
            const err = await res.json();
            showAlert('submit-alert', err.detail || '提交失败', 'error');
        }
    } catch (e) {
        showAlert('submit-alert', '网络错误: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '提交作品';
    }
}

/* -------------------- Leaderboard -------------------- */
async function renderLeaderboard() {
    document.getElementById('content').innerHTML = `
        <div class="card">
            <div class="card-header">
                <h2>排行榜</h2>
                <select id="leaderboard-filter" onchange="loadLeaderboard()" style="width:auto;min-width:140px;">
                    <option value="">总分榜</option>
                    ${[1,2,3,4,5,6,7].map(q => `<option value="${q}">Q${q} - ${getQuestionTitle(q)}</option>`).join('')}
                </select>
            </div>
            <div class="card-body" id="leaderboard-content">
                <div class="loading"><div class="spinner"></div>加载中...</div>
            </div>
        </div>
    `;
    await loadLeaderboard();
}

async function loadLeaderboard() {
    const qid = document.getElementById('leaderboard-filter')?.value || '';
    const url = qid ? `${API_BASE}/leaderboard?question_id=${qid}` : `${API_BASE}/leaderboard`;

    try {
        const res = await fetch(url);
        const data = await res.json();
        document.getElementById('leaderboard-content').innerHTML = renderLeaderboardTable(data);
    } catch (e) {
        document.getElementById('leaderboard-content').innerHTML = `<div class="alert alert-error show">加载失败: ${e.message}</div>`;
    }
}

function renderLeaderboardTable(data) {
    const items = data.items || [];
    if (!items.length) return '<div class="empty-state"><div class="empty-icon">🏆</div><h3>暂无数据</h3></div>';

    return `
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th style="width:50px;">排名</th>
                        <th>队伍</th>
                        <th style="width:100px;">总分</th>
                        <th style="width:100px;">置信度</th>
                        <th style="width:80px;">状态</th>
                    </tr>
                </thead>
                <tbody>
                    ${items.map((item, idx) => `
                        <tr>
                            <td><strong style="font-size:16px;color:${idx < 3 ? 'var(--color-accent)' : 'var(--color-text-muted)'};">${item.rank}</strong></td>
                            <td>
                                <div style="font-weight:500;">${item.team_name}</div>
                                <div style="font-size:12px;color:var(--color-text-muted);">${item.team_code}</div>
                            </td>
                            <td><strong>${item.total_score?.toFixed ? item.total_score.toFixed(2) : item.total_score}</strong></td>
                            <td style="color:var(--color-text-muted)">${item.confidence ? (item.confidence * 100).toFixed(0) + '%' : '-'}</td>
                            <td>${item.human_reviewed ? '<span class="tag tag-muted">已复核</span>' : '<span class="tag tag-info">AI评审</span>'}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

/* -------------------- Submissions -------------------- */
async function renderSubmissions() {
    document.getElementById('content').innerHTML = `
        <div class="card">
            <div class="card-header">
                <h2>作品列表</h2>
                <select id="sub-status-filter" onchange="loadSubmissions()" style="width:auto;">
                    <option value="">全部状态</option>
                    <option value="pending">待评审</option>
                    <option value="running">评审中</option>
                    <option value="completed">已完成</option>
                    <option value="failed">失败</option>
                </select>
            </div>
            <div class="card-body" id="submissions-content">
                <div class="loading"><div class="spinner"></div>加载中...</div>
            </div>
        </div>
    `;
    await loadSubmissions();
}

async function loadSubmissions() {
    const status = document.getElementById('sub-status-filter')?.value || '';
    let url = `${API_BASE}/submissions?page_size=50`;
    if (status) url += `&status=${status}`;

    try {
        const res = await fetch(url);
        const data = await res.json();
        document.getElementById('submissions-content').innerHTML = renderSubmissionsTable(data.items || []);
    } catch (e) {
        document.getElementById('submissions-content').innerHTML = `<div class="alert alert-error show">加载失败: ${e.message}</div>`;
    }
}

function renderSubmissionsTable(items) {
    if (!items.length) return '<div class="empty-state"><div class="empty-icon">📋</div><h3>暂无作品</h3></div>';

    return `
        <div class="table-container">
            <table>
                <thead>
                    <tr><th>作品</th><th>赛题</th><th>状态</th><th>提交时间</th><th>操作</th></tr>
                </thead>
                <tbody>
                    ${items.map(s => `
                        <tr class="submission-row" onclick="showSubmissionDetail('${s.id}')">
                            <td>
                                <div style="font-weight:500;">v${s.submission_version}</div>
                                <div style="font-size:12px;color:var(--color-text-muted);">${(s.file_size / 1024).toFixed(1)} KB</div>
                            </td>
                            <td>Q${s.question_id}</td>
                            <td>${formatStatus(s.status)}</td>
                            <td style="color:var(--color-text-muted)">${formatTime(s.submitted_at)}</td>
                            <td><button class="btn btn-sm" onclick="event.stopPropagation();showSubmissionDetail('${s.id}')">查看</button></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

/* -------------------- Submission Detail Modal -------------------- */
async function showSubmissionDetail(id) {
    document.getElementById('modal-overlay').classList.add('active');
    document.getElementById('modal-title').textContent = '作品详情';
    document.getElementById('modal-body').innerHTML = '<div class="loading"><div class="spinner"></div>加载中...</div>';

    try {
        const [subRes, scoresRes, reportRes] = await Promise.all([
            fetch(`${API_BASE}/submissions/${id}`),
            fetch(`${API_BASE}/submissions/${id}/scores`),
            fetch(`${API_BASE}/submissions/${id}/report`),
        ]);

        const sub = await subRes.json();
        const scores = await scoresRes.json();
        const report = await reportRes.json();

        document.getElementById('modal-title').textContent = `作品详情 - Q${sub.question_id} v${sub.submission_version}`;
        document.getElementById('modal-body').innerHTML = `
            <div style="margin-bottom:16px;">
                <span class="tag ${sub.status === 'completed' ? 'tag-success' : sub.status === 'failed' ? 'tag-danger' : 'tag-warning'}">
                    ${formatStatusText(sub.status)}
                </span>
                <span style="color:var(--color-text-muted);margin-left:8px;font-size:13px;">
                    ${formatTime(sub.submitted_at)}
                </span>
            </div>

            ${scores.scores?.length ? `
                <h4 style="margin:16px 0 8px;font-size:14px;font-weight:500;">评分详情</h4>
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-bottom:16px;">
                    ${scores.scores.map(s => `
                        <div style="background:var(--color-bg-secondary);padding:10px 12px;border-radius:var(--radius);text-align:center;">
                            <div style="font-size:11px;color:var(--color-text-muted);margin-bottom:2px;">${s.dimension}</div>
                            <div style="font-size:18px;font-weight:600;">${s.score}</div>
                        </div>
                    `).join('')}
                </div>
                <div style="background:var(--color-bg-secondary);padding:10px 12px;border-radius:var(--radius);margin-bottom:16px;">
                    <strong>加权总分: ${scores.total_score?.toFixed ? scores.total_score.toFixed(2) : scores.total_score}</strong>
                    <span style="color:var(--color-text-muted);margin-left:8px;">置信度: ${scores.overall_confidence ? (scores.overall_confidence * 100).toFixed(0) + '%' : '-'}</span>
                </div>
            ` : '<p style="color:var(--color-text-muted)">暂无评分</p>'}

            ${report.content ? `
                <h4 style="margin:16px 0 8px;font-size:14px;font-weight:500;">评审报告</h4>
                <div class="report-content" style="background:var(--color-bg-secondary);padding:16px;border-radius:var(--radius);max-height:400px;overflow-y:auto;">
                    ${markdownToHtml(report.content)}
                </div>
            ` : ''}
        `;
    } catch (e) {
        document.getElementById('modal-body').innerHTML = `<div class="alert alert-error show">加载失败: ${e.message}</div>`;
    }
}

function closeModal() {
    document.getElementById('modal-overlay').classList.remove('active');
}

/* -------------------- Health Check -------------------- */
async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();
        const statusEl = document.getElementById('system-status');
        const dot = document.querySelector('.status-dot');
        if (data.status === 'ok') {
            statusEl.textContent = '系统正常';
            dot.className = 'status-dot';
        } else {
            statusEl.textContent = '系统异常';
            dot.className = 'status-dot error';
        }
    } catch {
        document.getElementById('system-status').textContent = '连接断开';
        document.querySelector('.status-dot').className = 'status-dot error';
    }
}

/* -------------------- Utilities -------------------- */
function formatTime(iso) {
    if (!iso) return '-';
    const d = new Date(iso);
    return d.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function formatStatus(status) {
    const map = {
        pending: '<span class="tag tag-warning">待评审</span>',
        running: '<span class="tag tag-info">评审中</span>',
        completed: '<span class="tag tag-success">已完成</span>',
        failed: '<span class="tag tag-danger">失败</span>',
    };
    return map[status] || `<span class="tag tag-muted">${status}</span>`;
}

function formatStatusText(status) {
    const map = { pending: '待评审', running: '评审中', completed: '已完成', failed: '失败' };
    return map[status] || status;
}

function showAlert(id, msg, type) {
    const el = document.getElementById(id);
    if (!el) return;
    el.className = `alert alert-${type} show`;
    el.textContent = msg;
    setTimeout(() => { el.classList.remove('show'); }, 5000);
}

function showError(msg) {
    document.getElementById('content').innerHTML = `<div class="alert alert-error show" style="display:block;">${msg}</div>`;
}

function markdownToHtml(md) {
    return md
        .replace(/# (.*)/g, '<h1>$1</h1>')
        .replace(/## (.*)/g, '<h2>$1</h2>')
        .replace(/### (.*)/g, '<h3>$1</h3>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/- (.*)/g, '<li>$1</li>')
        .replace(/\n/g, '<br>');
}
