/**
 * demo.js — Zigflow DSL Compiler Demo (new 4-section layout)
 *
 * Layout:
 *   Section 01 — Workflow Overview  (description, diagram, metrics)
 *   Section 02 — Compiler Journey   (accordion: node map, adjacency, traversal)
 *   Section 03 — Generated DSL      (summary bar + collapsible viewer)
 *   Section 04 — Validation         (badge + CLI output)
 *
 * Timeline: 4 visual stages (Workflow / Compiler / DSL / Validation)
 */

'use strict';
// ── Business-friendly level labels ──────────────────────────────────────────────

const LEVEL_LABELS = {
  1: {
    name: 'Level 1 - Linear Workflow',
    subtitle: 'START → INPUT → ACTION → OUTPUT → END. The simplest sequential workflow.'
  },

  2: {
    name: 'Level 2 - Two-Branch Workflow',
    subtitle: 'Two parallel branches execute from a shared INPUT and produce separate outputs.'
  },

  3: {
    name: 'Level 3 - Three-Branch Workflow',
    subtitle: 'Three concurrent branches execute from the same starting point.'
  },

  4: {
    name: 'Level 4 - Deep Branch Workflow',
    subtitle: 'Parallel branches containing chained ACTION nodes before producing outputs.'
  },

  5: {
    name: 'Level 5 - Mixed-Depth Workflow',
    subtitle: 'Branches with different depths and processing complexity.'
  },

  6: {
    name: 'Level 6 - WAIT Workflow',
    subtitle: 'Introduces a WAIT node that pauses execution for a configured duration.'
  },

  7: {
    name: 'Level 7 - WAIT + Parallel Workflow',
    subtitle: 'Parallel execution where one branch contains a WAIT node.'
  },

  8: {
    name: 'Level 8 - Event Workflow',
    subtitle: 'Execution pauses until an external event or signal is received.'
  },

  9: {
    name: 'Level 9 - WAIT + Event Workflow',
    subtitle: 'Combines timer-based waiting and event-driven continuation.'
  },

  10: {
    name: 'Level 10 - IF Workflow',
    subtitle: 'A single IF condition routes execution through true and false branches.'
  },

  11: {
    name: 'Level 11 - Nested IF Workflow',
    subtitle: 'Multiple IF conditions nested inside other decision branches.'
  },

  12: {
    name: 'Level 12 - PARALLEL Workflow',
    subtitle: 'Independent ACTION branches execute concurrently and merge into a shared output.'
  },

  13: {
    name: 'Level 13 - Advanced PARALLEL Workflow',
    subtitle: 'PARALLEL execution combined with IF logic and sequential processing chains.'
  },

  14: {
    name: 'Level 14 - PARALLEL Convergence Workflow',
    subtitle: 'Multiple branches converge onto the same downstream node to validate compiler behavior.'
  }
};
// ── State ────────────────────────────────────────────────────────────────────

let _lastWorkflowJson = null;
let _lastDsl = null;
let _currentMode = 'generate';

// ── DOM helpers ──────────────────────────────────────────────────────────────

const $ = (id) => document.getElementById(id);
const qsa = (sel, ctx = document) => ctx.querySelectorAll(sel);

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' });
  loadLevels();
  wireControls();
  wireAccordion();
  wireDslToggle();
  wireDiagramControls();
});

// ── Level Dropdown ───────────────────────────────────────────────────────────

async function loadLevels() {
  try {
    const res = await fetch('/api/levels');
    const levels = await res.json();
    const sel = $('level-select');
    levels.forEach(({ level }) => {
      const opt = document.createElement('option');
      opt.value = level;
      const label = LEVEL_LABELS[level];
      opt.textContent = label ? label.name : `Level ${level}`;
      sel.appendChild(opt);
    });
  } catch (e) {
    showError('Failed to load difficulty levels: ' + e.message);
  }
}

// ── Controls ─────────────────────────────────────────────────────────────────

function wireControls() {
  // Mode toggle
  qsa('.mode-btn').forEach((btn) => {
    btn.addEventListener('click', () => switchMode(btn.dataset.mode));
  });

  $('btn-run').addEventListener('click', () => runGenerate());
  $('btn-regen').addEventListener('click', () => runGenerate());
  $('btn-compile-paste').addEventListener('click', () => runPasteCompile());

  $('btn-download-dsl').addEventListener('click', () => downloadJson(_lastDsl, 'dsl.json'));
  $('btn-download-workflow').addEventListener('click', () => downloadJson(_lastWorkflowJson, 'workflow.json'));
}

function switchMode(mode) {
  _currentMode = mode;
  qsa('.mode-btn').forEach((b) => b.classList.toggle('active', b.dataset.mode === mode));
  $('ctrl-generate').classList.toggle('hidden', mode !== 'generate');
  $('ctrl-paste').classList.toggle('hidden', mode !== 'paste');
  $('paste-area').classList.toggle('hidden', mode !== 'paste');
}

// ── Accordion ─────────────────────────────────────────────────────────────────

function wireAccordion() {
  document.addEventListener('click', (e) => {
    const trigger = e.target.closest('.accordion-trigger');
    if (!trigger) return;
    const bodyId = trigger.getAttribute('aria-controls');
    const body = document.getElementById(bodyId);
    if (!body) return;
    const open = trigger.getAttribute('aria-expanded') === 'true';
    trigger.setAttribute('aria-expanded', String(!open));
    body.hidden = open;
  });
}

// ── DSL Toggle ────────────────────────────────────────────────────────────────

function wireDslToggle() {
  $('btn-toggle-dsl').addEventListener('click', () => {
    const viewer = $('dsl-viewer');
    const nowHidden = viewer.classList.toggle('hidden');
    $('btn-toggle-dsl').textContent = nowHidden ? 'View DSL ▼' : 'Hide DSL ▲';
  });
}

// ── Diagram Controls (pan / zoom) ────────────────────────────────────────────

function wireDiagramControls() {
  $('btn-zoom-in').addEventListener('click', () => {
    if (!window._panzoomInst) return;
    const rect = $('diagram-container').getBoundingClientRect();
    window._panzoomInst.smoothZoom(rect.left + rect.width / 2, rect.top + rect.height / 2, 1.4);
  });
  $('btn-zoom-out').addEventListener('click', () => {
    if (!window._panzoomInst) return;
    const rect = $('diagram-container').getBoundingClientRect();
    window._panzoomInst.smoothZoom(rect.left + rect.width / 2, rect.top + rect.height / 2, 0.72);
  });
  $('btn-zoom-reset').addEventListener('click', () => {
    if (!window._panzoomInst) return;
    const fs = window._fitState ?? { scale: 1, x: 0, y: 0 };
    window._panzoomInst.zoomAbs(0, 0, fs.scale);
    window._panzoomInst.moveTo(fs.x, fs.y);
  });
  $('btn-zoom-fullscreen').addEventListener('click', () => {
    const el = $('diagram-container');
    if (!el) return;
    if (el.requestFullscreen) el.requestFullscreen();
    else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
  });
}

// ── Generate ──────────────────────────────────────────────────────────────────

async function runGenerate() {
  const level = parseInt($('level-select').value, 10);
  if (!level) { showError('Please select a difficulty level first.'); return; }

  showLoading('Generating & Compiling…');
  resetTimeline();
  $('results-area').classList.add('hidden');

  try {
    setStage(0, 'active');
    const res = await fetch('/api/pipeline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ level }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    await renderAll(data, true);
    $('btn-regen').disabled = false;
  } catch (e) {
    showError('Pipeline error: ' + e.message);
    resetTimeline();
  } finally {
    hideLoading();
  }
}

// ── Paste Compile ─────────────────────────────────────────────────────────────

async function runPasteCompile() {
  const raw = $('paste-input').value.trim();
  if (!raw) { showError('Please paste a workflow JSON first.'); return; }
  let workflow;
  try { workflow = JSON.parse(raw); } catch (e) { showError('Invalid JSON: ' + e.message); return; }

  showLoading('Compiling custom workflow…');
  resetTimeline();
  $('results-area').classList.add('hidden');

  try {
    setStage(0, 'active');
    const res = await fetch('/api/compile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workflow }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    await renderAll(data, false);
  } catch (e) {
    showError('Compile error: ' + e.message);
    resetTimeline();
  } finally {
    hideLoading();
  }
}

// ── Render All ────────────────────────────────────────────────────────────────

async function renderAll(data, hasGenerator) {
  const { compiler, dsl, validation, metrics } = data;

  _lastDsl = dsl;

  // ── Stage 1: Workflow Overview ─────────────────────────────────────────────
  setStage(0, 'active');

  if (hasGenerator && data.generator) {
    const gen = data.generator;
    _lastWorkflowJson = gen.workflow_json;

    // Friendly name + subtitle from lookup table
    const labels = LEVEL_LABELS[gen.level];
    $('workflow-name').textContent = labels ? labels.name : (gen.description || 'Workflow');
    $('workflow-subtitle').textContent = labels ? labels.subtitle : '';

    const rawEl = $('raw-workflow-json');
    rawEl.textContent = JSON.stringify(gen.workflow_json, null, 2);
    hljs.highlightElement(rawEl);

    $('panel-description').style.display = '';
    $('panel-diagram').style.display = '';

    await renderMermaid(gen.mermaid_raw);
  } else {
    // Paste mode: hide description + diagram panels
    $('panel-description').style.display = 'none';
    $('panel-diagram').style.display = 'none';
    if (compiler.node_map) {
      _lastWorkflowJson = { nodes: Object.values(compiler.node_map), edges: [] };
    }
  }

  // Node type badges (bonus — derived from metrics)
  renderNodeBadges(metrics?.node_types ?? []);

  setStage(0, 'done');

  // ── Stage 2: DSL (hero output) ────────────────────────────────────────────
  setStage(1, 'active');
  await sleep(80);

  const dslEl = $('dsl-output');
  dslEl.textContent = JSON.stringify(dsl, null, 2);
  hljs.highlightElement(dslEl);

  // DSL summary bar
  const doList = dsl?.do ?? [];
  $('dsl-task-count').textContent = doList.length;
  $('dsl-workflow-type').textContent = dsl?.document?.workflowType ?? '—';
  $('dsl-dsl-version').textContent = dsl?.document?.dsl ?? '—';

  // DSL viewer open by default (it's the hero output)
  $('dsl-viewer').classList.remove('hidden');
  $('btn-toggle-dsl').textContent = 'Hide DSL ▲';

  setStage(1, 'done');

  // ── Stage 3: Compiler Journey ─────────────────────────────────────────────
  setStage(2, 'active');
  await sleep(80);

  renderNodeMap(compiler.node_map);
  renderAdjacency(compiler.adjacency_display);
  renderTraversal(compiler.traversal_display);

  setStage(2, 'done');

  // ── Stage 4: Validation ────────────────────────────────────────────────────
  setStage(3, 'active');
  await sleep(60);

  renderValidation(validation);

  setStage(3, 'done');

  // ── Metrics grid ───────────────────────────────────────────────────────────
  renderMetrics(metrics, validation);

  // Reveal results
  $('results-area').classList.remove('hidden');
}

// ── Mermaid + pan/zoom ───────────────────────────────────────────────────────────────

async function renderMermaid(mermaidRaw) {
  const container = $('diagram-container');
  if (!container) return;
  container.innerHTML = '';
  container.style.minHeight = '';  // clear any previous inline value
  container.style.height = '';

  // Strip unsupported Mermaid edge label syntax
  const sanitized = mermaidRaw.replace(/-- \{([^}]+)\} -->/g, '-- ($1) -->');

  try {
    const { svg } = await mermaid.render('mermaid-svg-' + Date.now(), sanitized);
    container.innerHTML = svg;

    const svgEl = container.querySelector('svg');
    if (svgEl) {
      // Remove Mermaid's max-width so panzoom can scale freely
      svgEl.style.maxWidth = 'none';
      svgEl.style.display = 'block';

      if (typeof panzoom !== 'undefined') {
        // Dispose previous instance if any
        if (window._panzoomInst) {
          try { window._panzoomInst.dispose(); } catch (_) {}
        }
        window._panzoomInst = panzoom(svgEl, {
          maxZoom: 5,
          minZoom: 0.15,
          zoomDoubleClickSpeed: 1,
        });

        // \u2500\u2500 Fit-to-container: use actual rendered SVG dimensions \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        const bbox = svgEl.getBBox();
        const svgW = bbox.width  || svgEl.scrollWidth  || 800;
        const svgH = bbox.height || svgEl.scrollHeight || 400;

        // Dynamic viewport sizing based on actual diagram size
        const targetH = Math.max(
          400,
          Math.min(svgH + 80, 1400)
        );

        container.style.height = `${targetH}px`;

        const cw = container.clientWidth;

        // Fit to BOTH dimensions but never upscale
        const fitScale = Math.min(
          cw / svgW,
          targetH / svgH,
          1
        );

        // Center horizontally
        const fitX = (cw - svgW * fitScale) / 2;

        // Top align instead of vertical centering
        const fitY = 20;

        window._fitState = { scale: fitScale, x: fitX, y: fitY };
        window._panzoomInst.zoomAbs(0, 0, fitScale);
        window._panzoomInst.moveTo(fitX, fitY);

        const ctrl = $('diagram-controls');
        if (ctrl) ctrl.classList.remove('hidden');
      }
    }
  } catch (e) {
    container.innerHTML = `<p style="color:#ef4444;font-size:13px;padding:16px;">Diagram render error: ${escapeHtml(e.message)}</p>`;
  }
}
// ── Node type badges (bonus) ──────────────────────────────────────────────────────

function renderNodeBadges(nodeTypes) {
  const container = $('node-type-badges');
  if (!container) return;
  container.innerHTML = '';
  (nodeTypes || []).forEach((type) => {
    const span = document.createElement('span');
    span.className = `badge-item badge-${type}`;
    span.textContent = type;
    container.appendChild(span);
  });
}

// ── Node Map ──────────────────────────────────────────────────────────────────

function renderNodeMap(nodeMap) {
  const tbody = $('nodemap-tbody');
  tbody.innerHTML = '';
  Object.values(nodeMap).forEach((node) => {
    const tr = document.createElement('tr');
    const dataSummary = node.data ? JSON.stringify(node.data, null, 2) : '—';
    tr.innerHTML = `
      <td><code>${escapeHtml(node.id || '?')}</code></td>
      <td><span class="node-type-badge ntype-${escapeHtml(node.type || '')}">${escapeHtml(node.type || '?')}</span></td>
      <td><pre class="node-data-summary">${escapeHtml(dataSummary)}</pre></td>
    `;
    tbody.appendChild(tr);
  });
}

// ── Adjacency List ────────────────────────────────────────────────────────────

function renderAdjacency(adjacency) {
  const container = $('adjacency-list');
  container.innerHTML = '';
  adjacency.forEach((row) => {
    const div = document.createElement('div');
    div.className = 'adjacency-row';
    const targetsHtml = row.targets
      .map((t) => {
        const ctrl = t.control ? `<span class="adj-control">${escapeHtml(JSON.stringify(t.control))}</span>` : '';
        return `<div class="adj-target"><code>${escapeHtml(t.id)}</code><span class="node-type-badge ntype-${escapeHtml(t.type)}">${escapeHtml(t.type)}</span>${ctrl}</div>`;
      })
      .join('');
    div.innerHTML = `
      <div class="adj-source">${escapeHtml(row.source)}</div>
      <div class="adj-arrow">→</div>
      <div class="adj-targets">${targetsHtml || '<span style="color:var(--text-dim)">terminal</span>'}</div>
    `;
    container.appendChild(div);
  });
}

// ── Traversal List ────────────────────────────────────────────────────────────

function renderTraversal(traversal) {
  const container = $('traversal-list');
  container.innerHTML = '';
  traversal.forEach((entry) => {
    const div = document.createElement('div');
    div.className = 'traversal-entry';

    const extras = [];
    if (entry.is_terminal) extras.push(['terminal', 'true']);
    if (entry.incoming_edge_control) extras.push(['edge_ctrl', JSON.stringify(entry.incoming_edge_control)]);
    if (entry.reads_from_context) extras.push(['reads_ctx', 'true']);
    if (entry.branch_map && Object.keys(entry.branch_map).length) {
      extras.push(['branches', Object.keys(entry.branch_map).join(', ')]);
    }
    if (entry.parallel_branches) extras.push(['parallel_branches', entry.parallel_branches.join(', ')]);
    if (entry.successors && entry.successors.length) extras.push(['successors', entry.successors.join(', ')]);

    const extrasHtml = extras
      .map(([k, v]) => `<div class="trav-detail-row"><span class="trav-detail-key">${escapeHtml(k)}:</span><span class="trav-detail-val">${escapeHtml(v)}</span></div>`)
      .join('');

    div.innerHTML = `
      <div class="trav-step">${entry.step}</div>
      <div class="trav-type"><span class="node-type-badge ntype-${escapeHtml(entry.node_type)}">${escapeHtml(entry.node_type)}</span></div>
      <div class="trav-details">
        <div class="trav-detail-row"><span class="trav-detail-key">id:</span><span class="trav-detail-val">${escapeHtml(entry.node_id)}</span></div>
        ${extrasHtml}
      </div>
    `;
    container.appendChild(div);
  });
}

// ── Validation ────────────────────────────────────────────────────────────────

function renderValidation(validation) {
  const badge = $('validation-badge');
  const icon = $('vbadge-icon');
  const text = $('vbadge-text');
  const output = $('validation-output');

  if (validation.passed) {
    badge.className = 'validation-result pass';
    icon.textContent = '✅';
    text.textContent = 'zigflow validate — PASSED';
  } else {
    badge.className = 'validation-result fail';
    icon.textContent = '❌';
    text.textContent = 'zigflow validate — FAILED';
  }
  output.textContent = validation.output || '(no output)';
}

// ── Metrics Grid ──────────────────────────────────────────────────────────────

function renderMetrics(metrics, validation) {
  $('m-nodes').textContent = metrics.node_count ?? '—';
  $('m-edges').textContent = metrics.edge_count ?? '—';
  $('m-steps').textContent = metrics.traversal_steps ?? '—';
  $('m-topology').textContent = metrics.topology_label ?? '—';

  const card = $('mc-validation');
  const label = $('m-valid-label');

  const passed = validation?.passed ?? metrics.validation_passed;
  if (passed === true) {
    label.textContent = '✅ Passed';
    card.classList.add('valid');
    card.classList.remove('invalid');
  } else if (passed === false) {
    label.textContent = '❌ Failed';
    card.classList.add('invalid');
    card.classList.remove('valid');
  } else {
    label.textContent = '—';
  }

  $('metrics-card').classList.remove('hidden');
}

// ── Timeline ──────────────────────────────────────────────────────────────────

function setStage(vstage, state) {
  const el = document.querySelector(`[data-vstage="${vstage}"]`);
  if (!el) return;
  el.classList.remove('stage-pending', 'stage-active', 'stage-done');
  el.classList.add(`stage-${state}`);
}

function resetTimeline() {
  qsa('[data-vstage]').forEach((el) => {
    el.classList.remove('stage-active', 'stage-done');
    el.classList.add('stage-pending');
  });
}

// ── Loading + Error ───────────────────────────────────────────────────────────

function showLoading(text = 'Compiling…') {
  $('loading-text').textContent = text;
  $('loading-overlay').classList.remove('hidden');
}
function hideLoading() { $('loading-overlay').classList.add('hidden'); }

function showError(msg) {
  $('error-toast-msg').textContent = msg;
  $('error-toast').classList.remove('hidden');
  setTimeout(() => $('error-toast').classList.add('hidden'), 6000);
}

// ── Download ──────────────────────────────────────────────────────────────────

function downloadJson(obj, filename) {
  if (!obj) { showError('Nothing to download yet.'); return; }
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Utils ─────────────────────────────────────────────────────────────────────

function escapeHtml(str) {
  if (typeof str !== 'string') str = String(str ?? '');
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function truncate(str, len) {
  return str && str.length > len ? str.slice(0, len) + '…' : str;
}

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }
