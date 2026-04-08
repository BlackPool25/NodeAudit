const resultsEl = document.getElementById('results');
const statusEl = document.getElementById('status');
const graphFrame = document.getElementById('graphFrame');
const viewerTitle = document.getElementById('viewerTitle');
const reportJsonLink = document.getElementById('reportJsonLink');
const diagEl = document.getElementById('diag');
const schemaRows = document.getElementById('schemaRows');
const nodesEl = document.getElementById('nodes');
const moduleSearchEl = document.getElementById('moduleSearch');
const moduleDetailEl = document.getElementById('moduleDetail');
const rawCodeEl = document.getElementById('rawCode');
const rawJsonBtn = document.getElementById('rawJsonBtn');
const moduleRawJsonEl = document.getElementById('moduleRawJson');
const runAnalysisBtn = document.getElementById('runAnalysisBtn');
const analysisTimeoutEl = document.getElementById('analysisTimeout');
const analysisOutputEl = document.getElementById('analysisOutput');
const bootstrapTrainingBtn = document.getElementById('bootstrapTrainingBtn');
const runTrainingBtn = document.getElementById('runTrainingBtn');
const refreshTrainingRunsBtn = document.getElementById('refreshTrainingRunsBtn');
const trainingRunsEl = document.getElementById('trainingRuns');
const trainingOutputEl = document.getElementById('trainingOutput');
const analysisRunIdEl = document.getElementById('analysisRunId');
const fetchRunAnalysisBtn = document.getElementById('fetchRunAnalysisBtn');
const runAnalysisOutputEl = document.getElementById('runAnalysisOutput');

let currentNodes = [];
let selectedModuleId = '';

function findNodeByModuleId(moduleId) {
  const target = String(moduleId || '').trim();
  if (!target) {
    return null;
  }

  const exact = currentNodes.find((node) => String(node.module_id) === target);
  if (exact) {
    return exact;
  }

  const lowered = target.toLowerCase();
  const ci = currentNodes.find((node) => String(node.module_id).toLowerCase() === lowered);
  if (ci) {
    return ci;
  }

  return currentNodes.find((node) => String(node.module_id).endsWith(`.${target}`)) || null;
}

function selectModuleFromGraph(moduleId) {
  const node = findNodeByModuleId(moduleId);
  if (!node) {
    return;
  }
  showModule(node);
}

function bindGraphNodeClick(frameWin) {
  if (!frameWin || !frameWin.network || frameWin.__graphReviewNodeClickBound) {
    return;
  }
  frameWin.__graphReviewNodeClickBound = true;
  frameWin.network.on('click', (params) => {
    if (!params?.nodes?.length) {
      return;
    }
    const moduleId = params.nodes[0];
    selectModuleFromGraph(moduleId);
  });
}

window.addEventListener('message', (event) => {
  const payload = event.data;
  if (!payload || payload.type !== 'graphreview-node-select') {
    return;
  }
  selectModuleFromGraph(payload.moduleId);
});

function normalizeTooltipText(raw) {
  const text = String(raw || '');
  return text
    .replace(/<br\s*\/?\s*>/gi, '\n')
    .replace(/<\/?b>/gi, '')
    .replace(/<[^>]+>/g, '')
    .replace(/[ \t]+\n/g, '\n')
    .trim();
}

function normalizeGraphTooltips(frameDoc) {
  const tooltips = frameDoc.querySelectorAll('.vis-tooltip, .vis-network-tooltip');
  tooltips.forEach((tooltip) => {
    const normalized = normalizeTooltipText(tooltip.textContent);
    if (normalized && normalized !== tooltip.textContent) {
      tooltip.textContent = normalized;
    }
  });
}

function applyGraphTooltipStyles() {
  const frameDoc = graphFrame?.contentDocument;
  const frameWin = graphFrame?.contentWindow;
  if (!frameDoc) {
    return;
  }

  if (frameDoc.getElementById('graphreview-tooltip-style')) {
    return;
  }

  const style = frameDoc.createElement('style');
  style.id = 'graphreview-tooltip-style';
  style.textContent = `
    .vis-tooltip,
    .vis-network-tooltip {
      max-width: 420px !important;
      white-space: pre-wrap !important;
      overflow-wrap: anywhere !important;
      word-break: break-word !important;
      line-height: 1.35 !important;
      text-align: left !important;
    }
  `;

  frameDoc.head?.appendChild(style);

  const observer = new MutationObserver(() => normalizeGraphTooltips(frameDoc));
  observer.observe(frameDoc.body, { subtree: true, childList: true, characterData: true });
  normalizeGraphTooltips(frameDoc);

  if (frameWin) {
    bindGraphNodeClick(frameWin);
    let retries = 0;
    const interval = setInterval(() => {
      retries += 1;
      bindGraphNodeClick(frameWin);
      if (frameWin.__graphReviewNodeClickBound || retries > 20) {
        clearInterval(interval);
      }
    }, 250);
  }
}

graphFrame?.addEventListener('load', applyGraphTooltipStyles);

function fmtPct(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function fmtDate(seconds) {
  return new Date(seconds * 1000).toLocaleString();
}

function setActiveTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  document.querySelectorAll('.tab-panel').forEach((panel) => {
    panel.classList.toggle('active', panel.id === tabId);
  });
}

function renderResultList(results) {
  resultsEl.innerHTML = '';
  if (!results.length) {
    resultsEl.innerHTML = '<div class="muted">No reports found in outputs. Generate one first via CLI or /reports/generate.</div>';
    return;
  }

  results.forEach((result, idx) => {
    const item = document.createElement('button');
    item.className = 'result-item';
    item.type = 'button';
    item.innerHTML = `
      <div><strong>${result.report_title}</strong></div>
      <div class="muted" style="font-size:0.78rem;">${result.report_path}</div>
      <div class="meta-row">
        <span class="chip">nodes ${result.node_count ?? '-'}</span>
        <span class="chip">edges ${result.edge_count ?? '-'}</span>
        <span class="chip">confidence ${result.confidence_score == null ? '-' : Number(result.confidence_score).toFixed(3)}</span>
      </div>
      <div class="muted" style="font-size:0.75rem; margin-top:6px;">${fmtDate(result.generated_at)}</div>
    `;
    item.addEventListener('click', () => selectResult(result, item));
    resultsEl.appendChild(item);

    if (idx === 0) {
      item.click();
    }
  });
}

function renderSchema(columns) {
  schemaRows.innerHTML = '';
  Object.entries(columns || {}).forEach(([tableName, cols]) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${tableName}</td><td>${(cols || []).join(', ')}</td>`;
    schemaRows.appendChild(tr);
  });
}

function renderDiagnostics(connectivity, metrics, report) {
  const reportNodeCount = Array.isArray(report?.nodes) ? report.nodes.length : 0;
  const reportEdgeCount = Array.isArray(report?.edges) ? report.edges.length : 0;

  const nodeCount = Number(connectivity?.node_count || 0) || reportNodeCount;
  const edgeCount = Number(connectivity?.edge_count || 0) || reportEdgeCount;
  const connectedComponents = Number(connectivity?.connected_components || 0);
  const largestComponentSize = Number(connectivity?.largest_component_size || 0);
  const isolatedNodes = Number(connectivity?.isolated_nodes || 0);
  const isolationRatio = Number(connectivity?.isolation_ratio || 0);

  const isolationClass = isolationRatio > 0.35 ? 'danger' : '';
  diagEl.innerHTML = `
    <div class="kv"><span>Nodes</span><strong>${nodeCount}</strong></div>
    <div class="kv"><span>Edges</span><strong>${edgeCount}</strong></div>
    <div class="kv"><span>Connected Components</span><strong>${connectedComponents}</strong></div>
    <div class="kv"><span>Largest Component</span><strong>${largestComponentSize}</strong></div>
    <div class="kv"><span>Isolated Nodes</span><strong class="${isolationClass}">${isolatedNodes} (${fmtPct(isolationRatio)})</strong></div>
    <div class="kv"><span>Precision / Recall / F1</span><strong>${Number(metrics.precision || 0).toFixed(3)} / ${Number(metrics.recall || 0).toFixed(3)} / ${Number(metrics.f1 || 0).toFixed(3)}</strong></div>
    <div class="kv"><span>Security Coverage</span><strong>${Number(metrics.security_coverage || 0).toFixed(3)}</strong></div>
    <div class="kv"><span>Stage Coverage</span><strong>${Number(metrics.stage_coverage || 0).toFixed(3)}</strong></div>
  `;
}

function formatModuleDetail(node) {
  const findings = node.linter_findings || [];
  const reviews = node.reviews || [];
  const security = node.security_findings || [];
  const lastReview = reviews.length ? reviews[reviews.length - 1] : null;

  const findingList = findings.slice(0, 8).map((f) => (
    `<li>[${String(f.severity || '').toUpperCase()}] ${f.code} at line ${f.line}: ${f.message}</li>`
  )).join('');
  const reviewList = reviews.slice(-6).reverse().map((r) => (
    `<li>step ${r.step_number} | ${r.action_type} | reward ${Number(r.reward_given || 0).toFixed(2)}</li>`
  )).join('');

  return `
    <div class="module-card">
      <h4>${node.module_id}</h4>
      <div class="kv"><span>Status</span><strong>${node.status}</strong></div>
      <div class="kv"><span>Summary</span><strong>${node.summary || '-'}</strong></div>
      <div class="kv"><span>Findings</span><strong>${findings.length}</strong></div>
      <div class="kv"><span>Security Findings</span><strong>${security.length}</strong></div>
      <div class="kv"><span>Reviews</span><strong>${reviews.length}</strong></div>
      <div class="kv"><span>Latest Review</span><strong>${lastReview ? `${lastReview.action_type} (step ${lastReview.step_number})` : '-'}</strong></div>
    </div>
    <div class="module-card">
      <h4>Top Findings</h4>
      <ul>${findingList || '<li>None</li>'}</ul>
    </div>
    <div class="module-card">
      <h4>Recent Reviews</h4>
      <ul>${reviewList || '<li>None</li>'}</ul>
    </div>
  `;
}

function showModule(node) {
  if (!node) {
    return;
  }
  selectedModuleId = node.module_id;
  moduleDetailEl.classList.remove('muted');
  moduleDetailEl.innerHTML = formatModuleDetail(node);
  rawCodeEl.textContent = node.raw_code || '# No raw code available';
  if (window.hljs) {
    window.hljs.highlightElement(rawCodeEl);
  }
  rawJsonBtn.style.display = 'inline-block';
  moduleRawJsonEl.style.display = 'none';
  moduleRawJsonEl.textContent = JSON.stringify(node, null, 2);
  document.querySelectorAll('.node-row').forEach((el) => {
    el.classList.toggle('active', el.dataset.moduleId === selectedModuleId);
  });
}

function renderNodes(report) {
  currentNodes = report.nodes || [];
  nodesEl.innerHTML = '';
  const query = (moduleSearchEl.value || '').trim().toLowerCase();
  const filtered = currentNodes.filter((node) => !query || node.module_id.toLowerCase().includes(query));
  filtered.forEach((node) => {
    const row = document.createElement('div');
    row.className = 'node-row';
    row.dataset.moduleId = node.module_id;
    const findings = (node.linter_findings || []).length;
    const reviews = (node.reviews || []).length;
    row.innerHTML = `
      <div class="node-title">${node.module_id}</div>
      <div class="node-meta">
        <span>status:${node.status}</span>
        <span>findings:${findings}</span>
        <span>reviews:${reviews}</span>
      </div>
    `;
    row.addEventListener('click', () => {
      showModule(node);
    });
    nodesEl.appendChild(row);
  });

  if (!filtered.length) {
    nodesEl.innerHTML = '<div class="muted">No modules match search.</div>';
  }
}

async function selectResult(result, itemEl) {
  document.querySelectorAll('.result-item').forEach((el) => el.classList.remove('active'));
  itemEl.classList.add('active');

  statusEl.textContent = `Loading ${result.report_path}...`;
  viewerTitle.textContent = result.report_title;
  graphFrame.src = result.graph_html_url || '';
  reportJsonLink.href = result.report_json_url;

  const res = await fetch(`/ui/result?report_path=${encodeURIComponent(result.report_path)}`);
  if (!res.ok) {
    statusEl.textContent = `Failed to load report detail: ${res.status}`;
    return;
  }

  const detail = await res.json();
  renderDiagnostics(detail.connectivity, detail.report.metrics || {}, detail.report || {});
  renderSchema(detail.db_columns || {});
  renderNodes(detail.report || {});
  moduleDetailEl.classList.add('muted');
  moduleDetailEl.textContent = 'Select a module to inspect report fields, findings, and reviews.';
  rawCodeEl.textContent = 'Select a module to view raw code.';
  rawJsonBtn.style.display = 'none';
  moduleRawJsonEl.style.display = 'none';
  moduleRawJsonEl.textContent = '';
  selectedModuleId = '';
  statusEl.textContent = `Loaded ${result.report_path}`;
}

async function runAnalysis() {
  const timeout = Number(analysisTimeoutEl.value || 45);
  analysisOutputEl.textContent = 'Running analyzers...';
  const res = await fetch('/analysis/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ timeout_seconds: timeout }),
  });
  const payload = await res.json();
  analysisOutputEl.textContent = JSON.stringify(payload, null, 2);
}

async function bootstrapTraining() {
  trainingOutputEl.textContent = 'Running training bootstrap...';
  const res = await fetch('/training/bootstrap', { method: 'POST' });
  const payload = await res.json();
  trainingOutputEl.textContent = JSON.stringify(payload, null, 2);
}

function renderTrainingRuns(rows) {
  if (!rows || !rows.length) {
    trainingRunsEl.classList.add('muted');
    trainingRunsEl.innerHTML = 'No runs yet.';
    return;
  }
  trainingRunsEl.classList.remove('muted');
  trainingRunsEl.innerHTML = rows.map((row) => `
    <div class="run-row">
      <div><strong>${row.run_id}</strong></div>
      <div class="muted">${row.model_name}</div>
      <div class="run-metrics">
        <span>precision ${Number(row.precision || 0).toFixed(3)}</span>
        <span>recall ${Number(row.recall || 0).toFixed(3)}</span>
        <span>tp ${row.true_positives}</span>
        <span>fp ${row.false_positives}</span>
        <span>fn ${row.false_negatives}</span>
      </div>
      <div class="muted">${new Date(row.created_at).toLocaleString()}</div>
      <button type="button" class="small-btn run-analysis-btn" data-run-id="${row.run_id}">Analyze Run</button>
    </div>
  `).join('');

  trainingRunsEl.querySelectorAll('.run-analysis-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const runId = btn.dataset.runId || '';
      if (analysisRunIdEl) {
        analysisRunIdEl.value = runId;
      }
      fetchRunAnalysis().catch((error) => {
        if (runAnalysisOutputEl) {
          runAnalysisOutputEl.textContent = `Error: ${String(error)}`;
        }
      });
    });
  });
}

async function refreshTrainingRuns() {
  const res = await fetch('/training/runs?limit=25');
  if (!res.ok) {
    trainingRunsEl.classList.add('muted');
    trainingRunsEl.textContent = `Failed to load runs: ${res.status}`;
    return;
  }
  const payload = await res.json();
  renderTrainingRuns(payload);
}

async function runTrainingEpisode() {
  trainingOutputEl.textContent = 'Running training episode...';
  const res = await fetch('/training/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force_seed: false, regression_tolerance: 0.01 }),
  });
  const payload = await res.json();
  trainingOutputEl.textContent = JSON.stringify(payload, null, 2);
  await refreshTrainingRuns();
}

async function fetchRunAnalysis() {
  const runId = (analysisRunIdEl?.value || '').trim();
  if (!runId) {
    runAnalysisOutputEl.textContent = 'Please select or enter a training run id first.';
    return;
  }

  runAnalysisOutputEl.textContent = `Generating critical analysis for ${runId}...`;
  const res = await fetch(`/training/runs/${encodeURIComponent(runId)}/analysis`);
  const payload = await res.json();
  if (!res.ok) {
    runAnalysisOutputEl.textContent = JSON.stringify(payload, null, 2);
    return;
  }
  runAnalysisOutputEl.textContent = payload.analysis || 'No analysis returned.';
}

rawJsonBtn?.addEventListener('click', () => {
  const isHidden = moduleRawJsonEl.style.display === 'none';
  moduleRawJsonEl.style.display = isHidden ? 'block' : 'none';
  rawJsonBtn.textContent = isHidden ? 'Hide Raw Module Report JSON' : 'View Raw Module Report JSON';
});

moduleSearchEl?.addEventListener('input', () => {
  renderNodes({ nodes: currentNodes });
});

runAnalysisBtn?.addEventListener('click', () => {
  runAnalysis().catch((error) => {
    analysisOutputEl.textContent = `Error: ${String(error)}`;
  });
});

bootstrapTrainingBtn?.addEventListener('click', () => {
  bootstrapTraining().catch((error) => {
    trainingOutputEl.textContent = `Error: ${String(error)}`;
  });
});

runTrainingBtn?.addEventListener('click', () => {
  runTrainingEpisode().catch((error) => {
    trainingOutputEl.textContent = `Error: ${String(error)}`;
  });
});

refreshTrainingRunsBtn?.addEventListener('click', () => {
  refreshTrainingRuns().catch((error) => {
    trainingRunsEl.classList.add('muted');
    trainingRunsEl.textContent = `Error: ${String(error)}`;
  });
});

fetchRunAnalysisBtn?.addEventListener('click', () => {
  fetchRunAnalysis().catch((error) => {
    if (runAnalysisOutputEl) {
      runAnalysisOutputEl.textContent = `Error: ${String(error)}`;
    }
  });
});

document.querySelectorAll('.tab-btn').forEach((btn) => {
  btn.addEventListener('click', () => setActiveTab(btn.dataset.tab));
});

async function init() {
  try {
    const res = await fetch('/ui/results');
    if (!res.ok) {
      statusEl.textContent = `Failed to load results: ${res.status}`;
      return;
    }
    const results = await res.json();
    renderResultList(results);
    await refreshTrainingRuns();
    statusEl.textContent = `Found ${results.length} report set(s)`;
  } catch (err) {
    statusEl.textContent = `Failed to load UI: ${String(err)}`;
  }
}

init();
