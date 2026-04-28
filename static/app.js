/* app.js - Frontend Logic for Shadow Applicant */

// ── State ──
let appState = {
    datasetLoaded: false,
    auditRun: false,
    cfRun: false,
    approvalChart: null,
    gaugeChart: null
};

// ── Initialization ──
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initTabs();
    initUploadPage();
    initFormOptions();
    initAuditPage();
    checkSystemStatus();
    initCharts();
});

// ── Navigation ──
function initNavigation() {
    const navBtns = document.querySelectorAll('.nav-btn');
    const pages = document.querySelectorAll('.page');

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            navBtns.forEach(b => b.classList.remove('active'));
            pages.forEach(p => p.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(btn.dataset.target).classList.add('active');
            
            if(btn.dataset.target === 'page-dashboard') checkSystemStatus();
        });
    });
}

function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const parent = btn.closest('.tabs');
            const targetId = btn.dataset.tab || btn.dataset.target;
            if(!targetId) return;

            // Handle chart tabs separately
            if(targetId.startsWith('chart-')) {
                parent.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                updateApprovalChart(targetId.replace('chart-', ''));
                return;
            }

            // Normal tabs
            parent.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            const container = parent.nextElementSibling;
            if(container && container.classList.contains('tab-content')) {
                // simple layout assumption for Run Audit page
                document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
                document.getElementById(targetId).classList.add('active');
            }
            btn.classList.add('active');
        });
    });
}

// ── Toasts ──
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i class="ph ph-${type === 'success' ? 'check-circle' : 'warning-circle'}"></i> ${message}`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ── System Status ──
async function checkSystemStatus() {
    try {
        const res = await fetch('/api/status');
        const status = await res.json();
        
        appState.datasetLoaded = status.dataset_loaded;
        appState.auditRun = status.audit_run;
        
        updateStatusDot('status-dataset', status.dataset_loaded);
        updateStatusDot('status-batch', status.audit_run);
        updateStatusDot('status-cf', status.cf_run);

        const btnRunBatch = document.getElementById('btn-run-batch');
        if(btnRunBatch) {
            btnRunBatch.disabled = !status.dataset_loaded;
            document.getElementById('batch-status-text').textContent = status.dataset_loaded ? 
                `Dataset Ready: ${status.dataset_size} records` : 'No dataset loaded';
        }
        
        if(status.dataset_loaded && document.getElementById('preview-table').querySelector('tbody').children.length === 0) {
            loadDatasetPreview();
        }

    } catch (e) {
        console.error("Status check failed", e);
    }
}

function updateStatusDot(id, active) {
    const el = document.getElementById(id);
    if(el) {
        const dot = el.querySelector('.dot');
        dot.className = `dot ${active ? 'green' : 'red'}`;
    }
}

// ── Upload Page ──
function initUploadPage() {
    const slider = document.getElementById('sample-count');
    const valSpan = document.getElementById('sample-count-val');
    if(slider) {
        slider.addEventListener('input', e => valSpan.textContent = e.target.value);
    }

    const btnSample = document.getElementById('btn-generate-sample');
    if(btnSample) {
        btnSample.addEventListener('click', async () => {
            const n = slider.value;
            const originalText = btnSample.innerHTML;
            btnSample.innerHTML = '<div class="spinner" style="width:20px;height:20px;border-width:2px;display:inline-block;vertical-align:middle;"></div> Generating...';
            btnSample.disabled = true;
            
            try {
                const res = await fetch('/api/sample-dataset', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({n})
                });
                const data = await res.json();
                if(data.error) throw new Error(data.error);
                
                showToast(`Loaded ${data.rows} sample records!`);
                renderPreviewTable(data.preview);
                document.getElementById('dataset-preview').style.display = 'block';
                checkSystemStatus();
            } catch (e) {
                showToast(e.message, 'error');
            } finally {
                btnSample.innerHTML = originalText;
                btnSample.disabled = false;
            }
        });
    }

    const fileInput = document.getElementById('csv-file');
    if(fileInput) {
        fileInput.addEventListener('change', async (e) => {
            if(!e.target.files.length) return;
            const file = e.target.files[0];
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const res = await fetch('/api/upload', { method: 'POST', body: formData });
                const data = await res.json();
                if(data.error) throw new Error(data.error);
                showToast(`Uploaded ${data.rows} records!`);
                loadDatasetPreview();
                checkSystemStatus();
            } catch(e) {
                showToast(e.message, 'error');
            }
        });
    }
}

async function loadDatasetPreview() {
    try {
        const res = await fetch('/api/dataset/preview');
        const data = await res.json();
        if(!data.error) {
            renderPreviewTable(data.preview);
            document.getElementById('dataset-preview').style.display = 'block';
            document.getElementById('dataset-meta').textContent = `${data.rows} rows`;
        }
    } catch(e) {}
}

function renderPreviewTable(rows) {
    if(!rows || !rows.length) return;
    const thead = document.querySelector('#preview-table <thead> tr');
    const tbody = document.querySelector('#preview-table <tbody>');
    thead.innerHTML = ''; tbody.innerHTML = '';
    
    const cols = Object.keys(rows[0]);
    cols.forEach(c => {
        const th = document.createElement('th');
        th.textContent = c;
        thead.appendChild(th);
    });

    rows.forEach(r => {
        const tr = document.createElement('tr');
        cols.forEach(c => {
            const td = document.createElement('td');
            td.textContent = r[c];
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
}

// ── Forms ──
async function initFormOptions() {
    try {
        const res = await fetch('/api/options');
        const opts = await res.json();
        
        const populate = (id, arr) => {
            const sel = document.getElementById(id);
            if(!sel) return;
            arr.forEach(opt => {
                const o = document.createElement('option');
                o.value = opt; o.textContent = opt;
                sel.appendChild(o);
            });
        };

        populate('sel-gender', opts.gender);
        populate('sel-race', opts.race);
        populate('sel-marital', opts.marital_status);
        populate('sel-disability', opts.disability_status);
        populate('sel-emp', opts.employment_type);
        populate('sel-purpose', opts.loan_purpose);
        populate('sel-collat', opts.collateral);
    } catch(e) {}
}

// ── Run Audit Page ──
function initAuditPage() {
    const btnSingle = document.getElementById('btn-run-single');
    if(btnSingle) {
        btnSingle.addEventListener('click', async () => {
            btnSingle.disabled = true;
            btnSingle.innerHTML = '<i class="ph ph-spinner ph-spin"></i> Running...';
            
            const form = document.getElementById('single-audit-form');
            const fd = new FormData(form);
            const profile = Object.fromEntries(fd.entries());
            const cf_attrs = Array.from(form.querySelectorAll('input[name="cf_attrs"]:checked')).map(cb => cb.value);
            
            try {
                const res = await fetch('/api/audit/single', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ profile, cf_attributes: cf_attrs, noise: 0.05 })
                });
                const data = await res.json();
                if(data.error) throw new Error(data.error);
                
                renderSingleResults(data);
                showToast("Counterfactual audit complete!");
                checkSystemStatus();
            } catch(e) {
                showToast(e.message, 'error');
            } finally {
                btnSingle.disabled = false;
                btnSingle.innerHTML = '<i class="ph ph-rocket"></i> Run Counterfactual Audit';
            }
        });
    }

    const btnBatch = document.getElementById('btn-run-batch');
    if(btnBatch) {
        btnBatch.addEventListener('click', async () => {
            document.getElementById('batch-loader').style.display = 'block';
            btnBatch.style.display = 'none';
            
            setAgentStatus('agent-3', 'running');
            setTimeout(() => setAgentStatus('agent-4', 'running'), 1000);

            try {
                const res = await fetch('/api/audit/batch', { method: 'POST' });
                const data = await res.json();
                if(data.error) throw new Error(data.error);
                
                showToast("Batch audit complete!");
                setAgentStatus('agent-3', 'done');
                setAgentStatus('agent-4', 'done');
                
                populateDashboard(data);
                populateAnalytics(data);
                populateReports(data);
                checkSystemStatus();
                
                // Switch to analytics tab
                document.querySelector('[data-target="page-analytics"]').click();
                
            } catch(e) {
                showToast(e.message, 'error');
                setAgentStatus('agent-3', 'idle');
                setAgentStatus('agent-4', 'idle');
            } finally {
                document.getElementById('batch-loader').style.display = 'none';
                btnBatch.style.display = 'inline-flex';
            }
        });
    }
}

function setAgentStatus(id, status) {
    const el = document.getElementById(id);
    if(!el) return;
    const badge = el.querySelector('.agent-badge');
    if(status === 'running') {
        badge.className = 'agent-badge active'; badge.textContent = 'Running';
        el.style.borderLeft = '3px solid var(--primary)';
    } else if(status === 'done') {
        badge.className = 'agent-badge active'; badge.textContent = 'Done';
        el.style.borderLeft = '3px solid var(--success)';
    } else {
        badge.className = 'agent-badge idle'; badge.textContent = 'Idle';
        el.style.borderLeft = '1px solid var(--border)';
    }
}

function renderSingleResults(data) {
    document.getElementById('single-results').style.display = 'block';
    
    // KPIs
    const orig = data.original;
    document.getElementById('sr-decision').textContent = orig.approved ? 'APPROVED' : 'DENIED';
    document.getElementById('sr-decision').style.color = orig.approved ? 'var(--success)' : 'var(--danger)';
    
    document.getElementById('sr-score').textContent = orig.score.toFixed(3);
    document.getElementById('sr-risk').textContent = orig.risk_tier;
    
    const rev = data.summary.any_reversal;
    document.getElementById('sr-reversal').textContent = rev ? 'YES' : 'NO';
    document.getElementById('sr-reversal').style.color = rev ? 'var(--danger)' : 'var(--success)';

    // Table
    const tbody = document.querySelector('#variants-table tbody');
    tbody.innerHTML = '';
    
    data.variants.forEach((v, i) => {
        const tr = document.createElement('tr');
        const scoreDiff = i === 0 ? '—' : (v.score - data.variants[0].score).toFixed(4);
        const decText = v.approved ? '✅ Approved' : '❌ Denied';
        
        tr.innerHTML = `
            <td><strong>${v.profile_id}</strong></td>
            <td>${v.score.toFixed(4)}</td>
            <td style="color: ${v.approved ? 'var(--success)' : 'var(--danger)'}">${decText}</td>
            <td style="color: ${i===0?'inherit': (scoreDiff < 0 ? 'var(--danger)' : 'var(--success)')}">${scoreDiff > 0 ? '+'+scoreDiff : scoreDiff}</td>
        `;
        tbody.appendChild(tr);
    });
}

// ── Populate UI from Batch Audit ──
let batchDataCache = null;

function populateDashboard(data) {
    document.getElementById('kpi-total-profiles').textContent = data.total_profiles;
    document.getElementById('kpi-approval-rate').textContent = (data.overall_approval * 100).toFixed(1) + '%';
    document.getElementById('kpi-findings').textContent = data.critical_findings.length;
    document.getElementById('kpi-score').textContent = data.audit_score.toFixed(0);
    
    document.getElementById('kpi-score').style.color = data.audit_score >= 80 ? 'var(--success)' : 'var(--danger)';

    updateGauge(data.audit_score);

    const flist = document.getElementById('findings-list');
    flist.innerHTML = '';
    data.critical_findings.forEach(f => {
        const div = document.createElement('div');
        div.className = 'finding-item';
        div.textContent = f;
        flist.appendChild(div);
    });
    document.getElementById('dashboard-findings').style.display = 'block';
}

function populateAnalytics(data) {
    batchDataCache = data;
    document.getElementById('analytics-empty').style.display = 'none';
    document.getElementById('analytics-content').style.display = 'block';

    // Metrics table
    const tbody = document.querySelector('#metrics-table tbody');
    tbody.innerHTML = '';
    data.metrics.forEach(m => {
        const tr = document.createElement('tr');
        const color = m['Bias Severity'].includes('Critical') ? 'var(--danger)' : (m['Bias Severity'].includes('Moderate') ? 'var(--warning)' : 'var(--success)');
        tr.innerHTML = `
            <td>${m['Attribute']}: ${m['Comparison Group']}</td>
            <td>${m['DIR'].toFixed(3)}</td>
            <td style="color:${color};font-weight:600">${m['Bias Severity']}</td>
        `;
        tbody.appendChild(tr);
    });

    updateApprovalChart('race');
}

function populateReports(data) {
    document.getElementById('reports-empty').style.display = 'none';
    document.getElementById('reports-content').style.display = 'block';
    
    const preview = document.getElementById('report-preview-text');
    preview.innerHTML = `
        <pre style="background:var(--bg-main);padding:16px;border-radius:8px;border:1px solid var(--border);color:var(--text-secondary);font-size:12px;overflow-x:auto;">
========================================================================
   THE SHADOW APPLICANT
   Enterprise AI Fairness Auditor
   Compliance & Bias Audit Report
========================================================================

Overall Fairness Score : ${data.audit_score.toFixed(1)} / 100
Total Profiles Audited : ${data.total_profiles}
Overall Approval Rate  : ${(data.overall_approval * 100).toFixed(1)}%

Critical Findings:
${data.critical_findings.map(f => `  - ${f}`).join('\n')}

Click download for the full comprehensive report.
        </pre>
    `;

    document.getElementById('btn-download-report').onclick = () => {
        window.location.href = '/api/report/download';
    };
}

// ── Charts (Chart.js) ──
function initCharts() {
    Chart.defaults.color = '#8B949E';
    Chart.defaults.font.family = "'Inter', sans-serif";
}

function updateGauge(score) {
    const ctx = document.getElementById('gaugeChart');
    if(!ctx) return;
    
    document.getElementById('gauge-text').textContent = score.toFixed(0);
    document.getElementById('gauge-text').style.color = score >= 80 ? '#00D4A1' : '#FF4B6E';

    if(appState.gaugeChart) appState.gaugeChart.destroy();
    
    appState.gaugeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [score, 100 - score],
                backgroundColor: [score >= 80 ? '#00D4A1' : (score >= 60 ? '#FFB347' : '#FF4B6E'), '#1E2430'],
                borderWidth: 0,
                circumference: 180,
                rotation: 270
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '80%',
            plugins: { tooltip: { enabled: false }, legend: { display: false } }
        }
    });
}

function updateApprovalChart(attribute) {
    if(!batchDataCache || !batchDataCache.approval_charts[attribute]) return;
    const chartData = batchDataCache.approval_charts[attribute];
    
    const labels = chartData.map(d => d[attribute]);
    const rates = chartData.map(d => d.rate * 100);
    const colors = rates.map(r => r >= 50 ? '#00D4A1' : '#FF4B6E');

    const ctx = document.getElementById('approvalChart');
    if(appState.approvalChart) appState.approvalChart.destroy();

    appState.approvalChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Approval Rate (%)',
                data: rates,
                backgroundColor: colors,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, max: 100, grid: { color: '#30363D' } },
                x: { grid: { display: false } }
            },
            plugins: { legend: { display: false } }
        }
    });
}
