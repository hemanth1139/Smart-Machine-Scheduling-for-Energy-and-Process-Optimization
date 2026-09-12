// ============================================================================
// Smart Schedule — Multi-Page SPA Dashboard (app.js)
// ============================================================================

// Configuration
const API_BASE = 'https://smart-machine-scheduling-for-energy-and.onrender.com';

// ── 10 Algorithm Constants ──────────────────────────────────────────────────
const MODEL_ORDER = [
  'FCFS','EDD','SPT','LPT',
  'Energy_Unaware','Makespan_Greedy',
  'FD_PDTS_Det','FD_PDTS_Robust',
  'CP_SAT_Warm','CP_SAT_Cold'
];

const SHORT_LABELS = {
  FCFS:'FCFS', EDD:'EDD', SPT:'SPT', LPT:'LPT',
  Energy_Unaware:'Energy Unaware', Makespan_Greedy:'Makespan Greedy',
  FD_PDTS_Det:'FD-PDTS Det.', FD_PDTS_Robust:'FD-PDTS Robust',
  CP_SAT_Warm:'Hybrid CP-SAT', CP_SAT_Cold:'CP-SAT Cold'
};

const FULL_LABELS = {
  FCFS:'First-Come First-Served (FCFS)',
  EDD:'Earliest Due Date (EDD)',
  SPT:'Shortest Processing Time (SPT)',
  LPT:'Longest Processing Time (LPT)',
  Energy_Unaware:'Energy-Unaware Greedy',
  Makespan_Greedy:'Makespan Load-Balancing Greedy',
  FD_PDTS_Det:'FD-PDTS Deterministic (p50)',
  FD_PDTS_Robust:'FD-PDTS Robust (p90 × 1.25)',
  CP_SAT_Warm:'Hybrid CP-SAT Warm-Start ✨',
  CP_SAT_Cold:'CP-SAT Cold-Start (Ablation)'
};

const MODEL_COLORS = {
  FCFS:'#ef4444', EDD:'#f97316', SPT:'#fb923c', LPT:'#fbbf24',
  Energy_Unaware:'#a3a3a3', Makespan_Greedy:'#facc15',
  FD_PDTS_Det:'#818cf8', FD_PDTS_Robust:'#6366f1',
  CP_SAT_Warm:'#a78bfa', CP_SAT_Cold:'#64748b'
};

const HIGHER_BETTER = new Set(['On-Time Completion (%)','Machine Utilization (%)']);

const ALGO_INFO = [
  {key:'FCFS', tag:'Baseline', tagColor:'rgba(239,68,68,0.15)', tagText:'#f87171', name:'First-Come First-Served (FCFS)', desc:'Processes jobs strictly by arrival timestamp. Energy-blind — serves as the primary comparison baseline.'},
  {key:'EDD', tag:'Baseline', tagColor:'rgba(249,115,22,0.15)', tagText:'#fb923c', name:'Earliest Due Date (EDD)', desc:'Prioritises urgent job deadlines to minimize lateness, but ignores electricity tariff pricing.'},
  {key:'SPT', tag:'Baseline', tagColor:'rgba(251,191,36,0.15)', tagText:'#fbbf24', name:'Shortest Processing Time (SPT)', desc:'Dispatches shortest jobs first to reduce average flow time. May cause deadline misses for longer jobs.'},
  {key:'LPT', tag:'Baseline', tagColor:'rgba(251,191,36,0.15)', tagText:'#fbbf24', name:'Longest Processing Time (LPT)', desc:'Schedules longest jobs first for better load balancing across machines.'},
  {key:'Energy_Unaware', tag:'Baseline', tagColor:'rgba(163,163,163,0.15)', tagText:'#a3a3a3', name:'Energy-Unaware Greedy', desc:'Arrival-order placement always picking the highest-power compatible machine — worst-case energy baseline.'},
  {key:'Makespan_Greedy', tag:'Classical', tagColor:'rgba(250,204,21,0.15)', tagText:'#facc15', name:'Makespan Greedy', desc:'Load-balancing greedy that assigns each job to the machine with earliest completion time.'},
  {key:'FD_PDTS_Det', tag:'Proposed', tagColor:'rgba(99,102,241,0.15)', tagText:'#818cf8', name:'FD-PDTS Deterministic', desc:'Forecast-Driven Priority Dispatching with Tariff Shifting using p50 energy forecasts and soft peak guards.'},
  {key:'FD_PDTS_Robust', tag:'Proposed', tagColor:'rgba(99,102,241,0.15)', tagText:'#818cf8', name:'FD-PDTS Robust', desc:'Robust variant applying 1.25× tariff multiplier on p90 forecasts with overload penalty scaling.'},
  {key:'CP_SAT_Warm', tag:'Proposed ⭐', tagColor:'rgba(167,139,250,0.2)', tagText:'#a78bfa', name:'Hybrid CP-SAT Warm-Start', desc:'OR-Tools CP-SAT solver initialized with FD-PDTS warm-start solution. Jointly optimizes energy, peak, carbon, and deadlines.', ours:true},
  {key:'CP_SAT_Cold', tag:'Ablation', tagColor:'rgba(100,116,139,0.15)', tagText:'#94a3b8', name:'CP-SAT Cold-Start', desc:'CP-SAT without warm-start hints — proves the necessity of FD-PDTS initialization for feasible solutions.'},
];

// ── Plotly Dark Theme ───────────────────────────────────────────────────────
const PLOTLY_DARK = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { family: 'Inter, sans-serif', size: 11, color: '#94a3b8' },
  xaxis: { gridcolor: 'rgba(148,163,184,0.1)', zerolinecolor: 'rgba(148,163,184,0.15)' },
  yaxis: { gridcolor: 'rgba(148,163,184,0.1)', zerolinecolor: 'rgba(148,163,184,0.15)' },
};

// ── Global State ────────────────────────────────────────────────────────────
let globalKpi = null;
let globalForecast = null;
let globalJobs = null;
let globalMachines = null;
let pagesLoaded = { dashboard: false, datasets: false, algorithms: false, gantt: false, results: false };

// ── Helpers ─────────────────────────────────────────────────────────────────
const showLoading = () => {
  const el = document.getElementById('loading-overlay');
  if (el) { el.style.display = 'flex'; el.style.opacity = '1'; }
};

const hideLoading = () => {
  const el = document.getElementById('loading-overlay');
  if (el) {
    el.style.opacity = '0';
    setTimeout(() => { el.style.display = 'none'; }, 300);
  }
};

const fmt = (n, prefix = '', suffix = '', decimals = 0) => {
  if (n === null || n === undefined || isNaN(n)) return '—';
  return `${prefix}${Number(n).toLocaleString('en-IN', {minimumFractionDigits: decimals, maximumFractionDigits: decimals})}${suffix}`;
};

const normalizeKpi = (raw) => {
  const models = raw.models || MODEL_ORDER;
  const values = models.map(model =>
    raw.metrics.map(metric => (raw.values[model] ? (raw.values[model][metric] ?? 0) : 0))
  );
  return { ...raw, models, values };
};

const computeImprovement = (kpi, metric, model) => {
  if (kpi.improvements && kpi.improvements[model] && kpi.improvements[model][metric] !== undefined) {
    return kpi.improvements[model][metric];
  }
  const modelIdx = kpi.models.indexOf(model);
  const baselineIdx = kpi.models.indexOf('FCFS');
  const metricIdx = kpi.metrics.indexOf(metric);
  if (modelIdx === -1 || baselineIdx === -1 || metricIdx === -1) return 0;
  const val = kpi.values[modelIdx][metricIdx];
  const base = kpi.values[baselineIdx][metricIdx];
  if (base === 0) return 0;
  const pct = ((val - base) / base) * 100;
  return HIGHER_BETTER.has(metric) ? pct : -pct;
};

const computeCompositeScore = (kpi, model) => {
  const modelIdx = kpi.models.indexOf(model);
  if (modelIdx === -1) return 0;
  let score = 0, count = 0;
  kpi.metrics.forEach((metric, mIdx) => {
    let min = Infinity, max = -Infinity;
    kpi.values.forEach(row => {
      const v = row[mIdx]; if (v < min) min = v; if (v > max) max = v;
    });
    if (max > min) {
      const val = kpi.values[modelIdx][mIdx];
      let norm = (val - min) / (max - min);
      if (!HIGHER_BETTER.has(metric)) norm = 1 - norm;
      score += norm; count++;
    }
  });
  return count > 0 ? (score / count) * 100 : 0;
};

// ── Hash Router ─────────────────────────────────────────────────────────────
function navigateTo(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const pageEl = document.getElementById(`page-${page}`);
  const navEl = document.querySelector(`.nav-item[data-page="${page}"]`);

  if (pageEl) pageEl.classList.add('active');
  if (navEl) navEl.classList.add('active');

  // Lazy-load page content
  loadPage(page);

  // Close mobile sidebar
  document.getElementById('sidebar')?.classList.remove('open');

  // Scroll to top
  document.getElementById('main-content')?.scrollTo(0, 0);
}

function handleHashChange() {
  const hash = window.location.hash.replace('#', '') || 'dashboard';
  navigateTo(hash);
}

// ── Page Loaders ────────────────────────────────────────────────────────────
async function loadPage(page) {
  if (page === 'dashboard' && !pagesLoaded.dashboard) {
    await loadDashboard();
  } else if (page === 'datasets' && !pagesLoaded.datasets) {
    await loadDatasets();
  } else if (page === 'algorithms' && !pagesLoaded.algorithms) {
    await loadAlgorithms();
  } else if (page === 'gantt' && !pagesLoaded.gantt) {
    await loadGantt();
  } else if (page === 'results' && !pagesLoaded.results) {
    await loadResults();
  }
}

// ── Data Fetching ───────────────────────────────────────────────────────────
async function fetchJSON(endpoint) {
  try {
    const resp = await fetch(`${API_BASE}${endpoint}`);
    if (!resp.ok) throw new Error(`API ${resp.status}`);
    return await resp.json();
  } catch (e) {
    console.warn(`Fetch failed for ${endpoint}:`, e);
    return null;
  }
}

async function ensureKpi() {
  if (!globalKpi) {
    const raw = await fetchJSON('/api/kpi');
    if (raw) globalKpi = normalizeKpi(raw);
    else globalKpi = getMockKpi();
  }
  return globalKpi;
}

async function ensureForecast() {
  if (!globalForecast) {
    globalForecast = await fetchJSON('/api/forecast');
    if (!globalForecast) globalForecast = getMockForecast();
  }
  return globalForecast;
}

// ── PAGE 1: DASHBOARD ───────────────────────────────────────────────────────
async function loadDashboard() {
  showLoading();
  try {
    const kpi = await ensureKpi();
    renderHeroStats(kpi);
    renderDashboardKPIs(kpi);
    pagesLoaded.dashboard = true;
  } catch (e) {
    console.error('Dashboard error:', e);
  } finally {
    hideLoading();
  }
}

function renderHeroStats(kpi) {
  const hybridIdx = kpi.models.indexOf('CP_SAT_Warm');
  const fcfsIdx = kpi.models.indexOf('FCFS');
  if (hybridIdx === -1 || fcfsIdx === -1) return;

  const getVal = (idx, mName) => {
    const mIdx = kpi.metrics.findIndex(m => m.toLowerCase().includes(mName.toLowerCase()));
    return mIdx !== -1 ? kpi.values[idx][mIdx] : 0;
  };

  const hybridCost = getVal(hybridIdx, 'cost');
  const fcfsCost = getVal(fcfsIdx, 'cost');
  const savings = fcfsCost - hybridCost;
  const savingsPct = fcfsCost > 0 ? (savings / fcfsCost) * 100 : 0;
  const peakMetric = kpi.metrics.find(m => m.includes('Peak')) || '';
  const co2Metric = kpi.metrics.find(m => m.includes('Carbon')) || '';
  const peakCut = computeImprovement(kpi, peakMetric, 'CP_SAT_Warm');
  const co2Cut = computeImprovement(kpi, co2Metric, 'CP_SAT_Warm');
  const onTime = getVal(hybridIdx, 'on-time');

  document.getElementById('stat-savings').innerText = fmt(savings, '₹', '', 0);
  document.getElementById('stat-savings-pct').innerText = fmt(savingsPct, '', '%', 1);
  document.getElementById('stat-peak-cut').innerText = fmt(peakCut, '', '%', 1);
  document.getElementById('stat-co2-cut').innerText = fmt(co2Cut, '', '%', 1);
  document.getElementById('stat-ontime').innerText = fmt(onTime, '', '%', 0);
}

function renderDashboardKPIs(kpi) {
  const el = document.getElementById('dashboard-kpi-cards');
  if (!el) return;

  const hybridIdx = kpi.models.indexOf('CP_SAT_Warm');
  const fcfsIdx = kpi.models.indexOf('FCFS');
  if (hybridIdx === -1 || fcfsIdx === -1) return;

  const icons = ['💰', '⚡', '🏭', '⏱️', '🕐', '✅', '⏳', '🌱', '📊', '🔌'];

  el.innerHTML = kpi.metrics.map((metric, mIdx) => {
    const hybridVal = kpi.values[hybridIdx][mIdx];
    const fcfsVal = kpi.values[fcfsIdx][mIdx];
    const imp = computeImprovement(kpi, metric, 'CP_SAT_Warm');
    const isGood = imp >= 0;
    const icon = icons[mIdx % icons.length];

    return `
      <div class="kpi-card">
        <div class="kpi-icon">${icon}</div>
        <div class="kpi-title">${metric}</div>
        <div class="kpi-row">
          <div>
            <div class="kpi-label">Hybrid CP-SAT</div>
            <div class="kpi-value">${fmt(hybridVal, '', '', 1)}</div>
          </div>
          <div>
            <div class="kpi-label">FCFS Baseline</div>
            <div class="kpi-value kpi-value-muted">${fmt(fcfsVal, '', '', 1)}</div>
          </div>
        </div>
        <div class="kpi-delta ${isGood ? 'positive' : 'negative'}">
          ${isGood ? '▲' : '▼'} ${Math.abs(imp).toFixed(1)}% vs FCFS
        </div>
      </div>
    `;
  }).join('');
}

// ── PAGE 2: DATASETS ────────────────────────────────────────────────────────
async function loadDatasets() {
  showLoading();
  try {
    const [machinesResp, jobsResp] = await Promise.all([
      fetchJSON('/api/datasets/machines'),
      fetchJSON('/api/datasets/jobs'),
    ]);

    const machines = machinesResp || getMockMachines();
    const jobs = jobsResp || getMockJobs();
    globalMachines = machines;
    globalJobs = jobs;

    renderDatasetStats(machines, jobs);
    renderMachineTable(machines);
    renderJobTable(jobs);
    setupJobFilters(jobs);

    pagesLoaded.datasets = true;
  } catch (e) {
    console.error('Datasets error:', e);
  } finally {
    hideLoading();
  }
}

function renderDatasetStats(machines, jobs) {
  const el = document.getElementById('dataset-stats');
  if (!el) return;

  const stats = jobs.stats || {};
  el.innerHTML = `
    <div class="stat-card-sm">
      <div class="stat-sm-value">${machines.count || 8}</div>
      <div class="stat-sm-label">Machines in Fleet</div>
    </div>
    <div class="stat-card-sm">
      <div class="stat-sm-value">${jobs.count || 160}</div>
      <div class="stat-sm-label">Total Jobs</div>
    </div>
    <div class="stat-card-sm">
      <div class="stat-sm-value">${stats.avg_duration_min || 63} min</div>
      <div class="stat-sm-label">Avg Job Duration</div>
    </div>
    <div class="stat-card-sm">
      <div class="stat-sm-value">${stats.min_duration_min || 15}–${stats.max_duration_min || 150} min</div>
      <div class="stat-sm-label">Duration Range</div>
    </div>
    <div class="stat-card-sm">
      <div class="stat-sm-value">3</div>
      <div class="stat-sm-label">Setup Types</div>
    </div>
    <div class="stat-card-sm">
      <div class="stat-sm-value">15 min</div>
      <div class="stat-sm-label">Slot Duration</div>
    </div>
  `;
}

function renderMachineTable(machines) {
  const table = document.getElementById('machine-table');
  if (!table) return;

  const data = machines.data || [];
  let html = `
    <thead>
      <tr>
        <th>Machine ID</th><th>Machine Type</th><th>Active Power (kW)</th>
        <th>Idle Power (kW)</th><th>Setup Energy (kW)</th><th>Changeover (min)</th>
      </tr>
    </thead><tbody>
  `;

  data.forEach(m => {
    html += `
      <tr>
        <td><strong>${m.Machine_ID}</strong></td>
        <td>${(m.Machine_Type || '').replace(/_/g, ' ')}</td>
        <td><span class="value-highlight">${m.Active_Power_kW} kW</span></td>
        <td>${m.Idle_Power_kW} kW</td>
        <td>${m.Setup_Energy_kW} kW</td>
        <td>${m.Changeover_Time_min} min</td>
      </tr>
    `;
  });

  html += '</tbody>';
  table.innerHTML = html;
}

function renderJobTable(jobs, filterPriority = 'all', searchId = '') {
  const table = document.getElementById('job-table');
  if (!table) return;

  let data = jobs.data || [];

  if (filterPriority !== 'all') {
    data = data.filter(j => String(j.Priority) === filterPriority);
  }
  if (searchId.trim()) {
    const q = searchId.trim().toUpperCase();
    data = data.filter(j => (j.Job_ID || '').toUpperCase().includes(q));
  }

  const badge = document.getElementById('job-count-badge');
  if (badge) badge.textContent = `${data.length} Jobs Shown`;

  let html = `
    <thead>
      <tr>
        <th>Job ID</th><th>Duration (min)</th><th>Deadline (slot)</th>
        <th>Priority</th><th>Arrival (slot)</th><th>Setup Type</th><th>Compatible Machines</th>
      </tr>
    </thead><tbody>
  `;

  data.forEach(j => {
    const priLabel = j.Priority == 1 ? 'High' : j.Priority == 2 ? 'Medium' : 'Low';
    const priClass = j.Priority == 1 ? 'High' : j.Priority == 2 ? 'Medium' : 'Low';
    html += `
      <tr>
        <td><strong>${j.Job_ID}</strong></td>
        <td>${j.Duration_min} min</td>
        <td>${j.Deadline}</td>
        <td><span class="badge-priority ${priClass}">${priLabel}</span></td>
        <td>${j.Arrival_Time}</td>
        <td>${j.Setup_Type}</td>
        <td class="compat-cell">${j.Compatible_Machines}</td>
      </tr>
    `;
  });

  html += '</tbody>';
  table.innerHTML = html;
}

function setupJobFilters(jobs) {
  const priorityFilter = document.getElementById('job-priority-filter');
  const searchInput = document.getElementById('job-search');

  const applyFilters = () => {
    renderJobTable(jobs, priorityFilter?.value || 'all', searchInput?.value || '');
  };

  if (priorityFilter) priorityFilter.addEventListener('change', applyFilters);
  if (searchInput) searchInput.addEventListener('input', applyFilters);
}

// ── PAGE 3: ALGORITHMS ──────────────────────────────────────────────────────
async function loadAlgorithms() {
  showLoading();
  try {
    const kpi = await ensureKpi();
    renderAlgoCards();
    renderLeaderboard(kpi);
    pagesLoaded.algorithms = true;
  } catch (e) {
    console.error('Algorithms error:', e);
  } finally {
    hideLoading();
  }
}

function renderAlgoCards() {
  const container = document.getElementById('algo-cards');
  if (!container) return;

  container.innerHTML = ALGO_INFO.map(algo => `
    <div class="algo-card ${algo.ours ? 'our-model' : ''}">
      <div>
        <span class="tag-pill" style="background:${algo.tagColor}; color:${algo.tagText};">
          ${algo.tag}
        </span>
        <h4>${algo.name}</h4>
        <p>${algo.desc}</p>
      </div>
    </div>
  `).join('');
}

function renderLeaderboard(kpi) {
  const table = document.getElementById('leaderboard-table');
  if (!table) return;

  const rows = kpi.models.map((model, idx) => {
    const getVal = (mName) => {
      const mIdx = kpi.metrics.findIndex(m => m.toLowerCase().includes(mName.toLowerCase()));
      return mIdx !== -1 ? kpi.values[idx][mIdx] : 0;
    };
    return {
      model,
      label: FULL_LABELS[model] || model,
      cost: getVal('cost'),
      peak: getVal('peak'),
      co2: getVal('carbon'),
      onTime: getVal('on-time'),
      makespan: getVal('makespan'),
      util: getVal('utilization'),
      waiting: getVal('waiting'),
      isOurs: model === 'CP_SAT_Warm',
    };
  });

  rows.sort((a, b) => a.cost - b.cost);

  let html = `
    <thead>
      <tr>
        <th>Rank</th><th>Algorithm</th><th>Energy Cost (₹)</th>
        <th>Peak Load (kW)</th><th>CO₂ (tCO₂)</th><th>On-Time</th>
        <th>Makespan (hrs)</th><th>Utilization</th><th>Avg Wait (min)</th>
      </tr>
    </thead><tbody>
  `;

  rows.forEach((r, rank) => {
    html += `
      <tr class="${r.isOurs ? 'highlight-row' : ''}">
        <td><strong>#${rank + 1}</strong></td>
        <td><strong>${r.label}</strong></td>
        <td>${fmt(r.cost, '₹', '', 0)}</td>
        <td>${fmt(r.peak, '', ' kW', 1)}</td>
        <td>${fmt(r.co2, '', ' tCO₂', 1)}</td>
        <td>${fmt(r.onTime, '', '%', 0)}</td>
        <td>${fmt(r.makespan, '', ' hrs', 1)}</td>
        <td>${fmt(r.util, '', '%', 1)}</td>
        <td>${fmt(r.waiting, '', ' min', 0)}</td>
      </tr>
    `;
  });

  html += '</tbody>';
  table.innerHTML = html;
}

// ── PAGE 4: GANTT CHARTS ────────────────────────────────────────────────────
async function loadGantt() {
  showLoading();
  try {
    const [schedule, forecast] = await Promise.all([
      fetchJSON('/api/schedule/CP_SAT_Warm'),
      ensureForecast(),
    ]);

    const sched = schedule || getMockSchedule();
    renderScheduleStats(sched);
    renderGantt(sched, forecast);
    renderScheduleTable(sched);

    // Model selector event
    const selector = document.getElementById('model-selector');
    if (selector) {
      selector.addEventListener('change', async (e) => {
        showLoading();
        try {
          const resp = await fetchJSON(`/api/schedule/${e.target.value}`);
          const s = resp || getMockSchedule();
          renderScheduleStats(s);
          renderGantt(s, globalForecast);
          renderScheduleTable(s);
        } finally {
          hideLoading();
        }
      });
    }

    pagesLoaded.gantt = true;
  } catch (e) {
    console.error('Gantt error:', e);
  } finally {
    hideLoading();
  }
}

function renderScheduleStats(schedule) {
  const el = document.getElementById('schedule-stats');
  if (!el || !Array.isArray(schedule)) return;

  const totalJobs = schedule.length;
  const machines = new Set(schedule.map(j => j.Assigned_Machine || j.Machine_ID || j.Machine)).size;
  const totalCost = schedule.reduce((sum, j) => {
    const cost = Number(j['Energy_Cost_$'] ?? j.Energy_Cost ?? j.Energy_Cost_INR ?? 0);
    return sum + (isNaN(cost) ? 0 : cost);
  }, 0);
  const lateJobs = schedule.filter(j => Number(j.Is_Late || 0) > 0).length;

  el.innerHTML = `
    <div class="stat-card-sm">
      <div class="stat-sm-value">${totalJobs}</div>
      <div class="stat-sm-label">Scheduled Jobs</div>
    </div>
    <div class="stat-card-sm">
      <div class="stat-sm-value">${machines}</div>
      <div class="stat-sm-label">Active Machines</div>
    </div>
    <div class="stat-card-sm">
      <div class="stat-sm-value">${fmt(totalCost, '₹', '', 0)}</div>
      <div class="stat-sm-label">Total Energy Cost</div>
    </div>
    <div class="stat-card-sm">
      <div class="stat-sm-value">${lateJobs === 0 ? '100%' : `${((1 - lateJobs / totalJobs) * 100).toFixed(0)}%`}</div>
      <div class="stat-sm-label">On-Time Rate</div>
    </div>
  `;
}

function renderGantt(schedule, forecast) {
  const el = document.getElementById('gantt-chart');
  if (!el || typeof Plotly === 'undefined' || !Array.isArray(schedule)) return;

  const baseTime = new Date('2024-01-01T00:00:00Z').getTime();

  const data = schedule.map(job => {
    const startMs = baseTime + (Number(job.Start_Slot) || 0) * 15 * 60 * 1000;
    const durMs = Math.max(1, (Number(job.End_Slot || job.Start_Slot + 1) - Number(job.Start_Slot)) * 15 * 60 * 1000);
    const priority = job.Priority || 'Medium';
    const priLabel = priority == 1 ? 'High' : priority == 2 ? 'Medium' : priority === 'High' ? 'High' : priority === 'Low' ? 'Low' : 'Medium';
    const energyCost = Number(job['Energy_Cost_$'] ?? job.Energy_Cost ?? job.Energy_Cost_INR ?? 0);

    return {
      x: [durMs], y: [job.Assigned_Machine || job.Machine_ID || 'M01'],
      base: [startMs], type: 'bar', orientation: 'h',
      name: `Job ${job.Job_ID}`, text: `${job.Job_ID}`, textposition: 'inside',
      textfont: { size: 9, color: '#fff' },
      marker: {
        color: priLabel === 'High' ? '#ef4444' : (priLabel === 'Medium' ? '#f59e0b' : '#10b981'),
        opacity: 0.85, line: { width: 0.5, color: 'rgba(0,0,0,0.3)' }
      },
      hoverinfo: 'text',
      hovertext: `<b>${job.Job_ID}</b><br>Machine: ${job.Assigned_Machine || job.Machine_ID}<br>Priority: ${priLabel}<br>Start: ${job.Start_Time || job.Start_Slot}<br>End: ${job.End_Time || job.End_Slot}<br>Energy: ₹${energyCost.toFixed(1)}`
    };
  });

  const shapes = [];
  if (Array.isArray(forecast)) {
    forecast.forEach(slot => {
      if (slot.Load_Type === 'Maximum_Load') {
        const start = baseTime + (slot.Slot) * 15 * 60 * 1000;
        const end = baseTime + (slot.Slot + 1) * 15 * 60 * 1000;
        shapes.push({ type: 'rect', xref: 'x', yref: 'paper', x0: start, x1: end, y0: 0, y1: 1,
          fillcolor: 'rgba(239, 68, 68, 0.12)', line: { width: 0 } });
      }
    });
  }

  const layout = {
    ...PLOTLY_DARK,
    title: { text: 'Machine Job Allocation Timeline (Red Zones = Peak TOU Tariff)', font: { size: 13, color: '#e2e8f0' } },
    xaxis: { ...PLOTLY_DARK.xaxis, type: 'date', title: { text: 'Timeline', font: { color: '#94a3b8' } } },
    yaxis: { ...PLOTLY_DARK.yaxis, title: { text: 'Machine', font: { color: '#94a3b8' } }, categoryorder: 'category ascending' },
    shapes, showlegend: false,
    margin: { l: 80, r: 30, t: 50, b: 50 },
    barmode: 'stack'
  };

  Plotly.newPlot('gantt-chart', data, layout, { responsive: true, displayModeBar: false });
}

function renderScheduleTable(schedule) {
  const table = document.getElementById('schedule-table');
  if (!table || !Array.isArray(schedule)) return;

  let html = `
    <thead>
      <tr>
        <th>Job ID</th><th>Machine</th><th>Type</th><th>Priority</th>
        <th>Start</th><th>End</th><th>Duration</th><th>Delay</th><th>Energy Cost</th>
      </tr>
    </thead><tbody>
  `;

  schedule.forEach(j => {
    const pri = j.Priority == 1 ? 'High' : j.Priority == 2 ? 'Medium' : j.Priority === 'High' ? 'High' : j.Priority === 'Low' ? 'Low' : 'Medium';
    const durMin = j.Duration_min ?? ((Number(j.End_Slot || 0) - Number(j.Start_Slot || 0)) * 15);
    const cost = Number(j['Energy_Cost_$'] ?? j.Energy_Cost ?? j.Energy_Cost_INR ?? 0);

    html += `
      <tr>
        <td><strong>${j.Job_ID}</strong></td>
        <td>${j.Assigned_Machine || j.Machine_ID || j.Machine}</td>
        <td>${(j.Machine_Type || '').replace(/_/g, ' ')}</td>
        <td><span class="badge-priority ${pri}">${pri}</span></td>
        <td>${j.Start_Time || j.Start_Slot}</td>
        <td>${j.End_Time || j.End_Slot}</td>
        <td>${durMin} min</td>
        <td>${j.Delay_min ?? 0} min</td>
        <td>${fmt(cost, '₹', '', 1)}</td>
      </tr>
    `;
  });

  html += '</tbody>';
  table.innerHTML = html;
}

// ── PAGE 5: RESULTS ─────────────────────────────────────────────────────────
async function loadResults() {
  showLoading();
  try {
    const kpi = await ensureKpi();
    const aggData = await fetchJSON('/api/aggregate-stats');

    renderWinBoxes(kpi);
    renderImprovementHeatmap(kpi);
    renderCompositeBar(kpi);
    renderPeakBar(kpi);
    renderResultsKPIs(kpi);
    if (aggData) renderAggregateTable(aggData);

    pagesLoaded.results = true;
  } catch (e) {
    console.error('Results error:', e);
  } finally {
    hideLoading();
  }
}

function renderWinBoxes(kpi) {
  const el = document.getElementById('win-boxes');
  if (!el) return;

  const hybridIdx = kpi.models.indexOf('CP_SAT_Warm');
  const fcfsIdx = kpi.models.indexOf('FCFS');
  if (hybridIdx === -1 || fcfsIdx === -1) return;

  const getVal = (idx, mName) => {
    const mIdx = kpi.metrics.findIndex(m => m.toLowerCase().includes(mName.toLowerCase()));
    return mIdx !== -1 ? kpi.values[idx][mIdx] : 0;
  };

  const savings = getVal(fcfsIdx, 'cost') - getVal(hybridIdx, 'cost');
  const peakMetric = kpi.metrics.find(m => m.includes('Peak')) || '';
  const co2Metric = kpi.metrics.find(m => m.includes('Carbon')) || '';
  const peakCut = computeImprovement(kpi, peakMetric, 'CP_SAT_Warm');
  const co2Cut = computeImprovement(kpi, co2Metric, 'CP_SAT_Warm');

  el.innerHTML = `
    <div class="win-box">
      <div class="win-icon">💰</div>
      <div class="win-value">${fmt(savings, '₹', '', 0)}</div>
      <div class="win-label">Total Cost Savings</div>
      <p class="win-desc">Direct electricity bill reduction per scheduling cycle</p>
    </div>
    <div class="win-box">
      <div class="win-icon">⚡</div>
      <div class="win-value">${fmt(peakCut, '', '%', 1)}</div>
      <div class="win-label">Peak Demand Shaving</div>
      <p class="win-desc">Prevents peak utility surge charges and grid penalties</p>
    </div>
    <div class="win-box">
      <div class="win-icon">🌱</div>
      <div class="win-value">${fmt(co2Cut, '', '%', 1)}</div>
      <div class="win-label">Carbon Abatement</div>
      <p class="win-desc">Greenhouse gas emission reduction per cycle</p>
    </div>
  `;
}

function renderImprovementHeatmap(kpi) {
  const el = document.getElementById('improvement-heatmap');
  if (!el || typeof Plotly === 'undefined') return;

  const models = kpi.models.filter(m => m !== 'FCFS');
  const metrics = kpi.metrics;

  const zData = metrics.map(metric => models.map(model => computeImprovement(kpi, metric, model)));
  const textData = zData.map(row => row.map(v => Math.abs(v) < 0.01 ? "0.0%" : `${v > 0 ? '+' : ''}${v.toFixed(1)}%`));

  let flat = zData.flat();
  let minZ = Math.min(...flat, -5);
  let maxZ = Math.max(...flat, 45);
  let zeroFrac = Math.max(0.01, Math.min(0.99, (0 - minZ) / (maxZ - minZ)));

  const data = [{
    z: zData, x: models.map(m => SHORT_LABELS[m] || m), y: metrics,
    text: textData, texttemplate: "%{text}", type: 'heatmap',
    zmin: minZ, zmax: maxZ,
    colorscale: [[0.0, '#ef4444'], [zeroFrac, '#1e293b'], [1.0, '#10b981']],
    showscale: true, colorbar: { tickfont: { color: '#94a3b8' } }
  }];

  const layout = {
    ...PLOTLY_DARK,
    title: { text: '% Improvement vs FCFS (Green = Better, Red = Worse)', font: { size: 13, color: '#e2e8f0' } },
    margin: { l: 200, r: 40, t: 50, b: 80 },
  };

  Plotly.newPlot('improvement-heatmap', data, layout, { responsive: true, displayModeBar: false });
}

function renderCompositeBar(kpi) {
  const el = document.getElementById('composite-bar');
  if (!el || typeof Plotly === 'undefined') return;

  const scores = kpi.models.map(m => ({
    model: m, label: SHORT_LABELS[m] || m,
    score: computeCompositeScore(kpi, m),
    color: MODEL_COLORS[m] || '#6366f1'
  }));
  scores.sort((a, b) => a.score - b.score);

  const data = [{
    type: 'bar', x: scores.map(s => s.score), y: scores.map(s => s.label),
    orientation: 'h', marker: { color: scores.map(s => s.color) },
    text: scores.map(s => s.score.toFixed(1)), textposition: 'inside',
    textfont: { color: '#fff', size: 11 }
  }];

  const layout = {
    ...PLOTLY_DARK,
    title: { text: 'Overall Composite Efficiency Index (0–100)', font: { size: 13, color: '#e2e8f0' } },
    xaxis: { ...PLOTLY_DARK.xaxis, title: { text: 'Composite Score', font: { color: '#94a3b8' } }, range: [0, 100] },
    margin: { l: 120, r: 30, t: 50, b: 40 },
  };

  Plotly.newPlot('composite-bar', data, layout, { responsive: true, displayModeBar: false });
}

function renderPeakBar(kpi) {
  const el = document.getElementById('peak-bar');
  if (!el || typeof Plotly === 'undefined') return;

  const peaks = kpi.models.map((m, idx) => {
    const peakIdx = kpi.metrics.findIndex(metric => metric.toLowerCase().includes('peak'));
    const val = peakIdx !== -1 ? kpi.values[idx][peakIdx] : 0;
    return { model: m, label: SHORT_LABELS[m] || m, val, color: MODEL_COLORS[m] || '#6366f1' };
  });
  peaks.sort((a, b) => b.val - a.val);

  const data = [{
    type: 'bar', x: peaks.map(p => p.val), y: peaks.map(p => p.label),
    orientation: 'h', marker: { color: peaks.map(p => p.color) },
    text: peaks.map(p => `${p.val.toFixed(1)} kW`), textposition: 'inside',
    textfont: { color: '#fff', size: 11 }
  }];

  const layout = {
    ...PLOTLY_DARK,
    title: { text: 'Peak Grid Power Demand (kW) — Lower is Better', font: { size: 13, color: '#e2e8f0' } },
    xaxis: { ...PLOTLY_DARK.xaxis, title: { text: 'Peak Demand (kW)', font: { color: '#94a3b8' } } },
    margin: { l: 120, r: 30, t: 50, b: 40 },
  };

  Plotly.newPlot('peak-bar', data, layout, { responsive: true, displayModeBar: false });
}

function renderResultsKPIs(kpi) {
  const el = document.getElementById('results-kpi-cards');
  if (!el) return;

  const hybridIdx = kpi.models.indexOf('CP_SAT_Warm');
  if (hybridIdx === -1) return;

  el.innerHTML = kpi.metrics.map((metric, mIdx) => {
    const val = kpi.values[hybridIdx][mIdx];
    const imp = computeImprovement(kpi, metric, 'CP_SAT_Warm');
    const isGood = imp >= 0;
    return `
      <div class="kpi-card">
        <div class="kpi-title">${metric}</div>
        <div class="kpi-value">${fmt(val, '', '', 1)}</div>
        <div class="kpi-delta ${isGood ? 'positive' : 'negative'}">
          ${isGood ? '▲' : '▼'} ${Math.abs(imp).toFixed(1)}% vs FCFS
        </div>
      </div>
    `;
  }).join('');
}

function renderAggregateTable(data) {
  const table = document.getElementById('aggregate-stats-table');
  if (!table || !Array.isArray(data)) return;

  // Group by Algorithm
  const grouped = {};
  data.forEach(row => {
    const algo = row.Algorithm;
    if (!grouped[algo]) grouped[algo] = [];
    grouped[algo].push(row);
  });

  let html = `
    <thead>
      <tr>
        <th>Algorithm</th><th>Metric</th><th>N</th>
        <th>Mean</th><th>SD</th><th>Median</th>
        <th>95% CI</th>
      </tr>
    </thead><tbody>
  `;

  const algoOrder = ['FCFS','SPT','LPT','EDD','Energy_Unaware_Greedy','Makespan_Greedy','FD_PDTS_Deterministic','FD_PDTS_Robust','CP_SAT_Warm','CP_SAT_Cold'];

  algoOrder.forEach(algo => {
    const rows = grouped[algo] || [];
    const isOurs = algo === 'CP_SAT_Warm';

    rows.forEach((r, i) => {
      const displayAlgo = i === 0 ? (SHORT_LABELS[algo] || FULL_LABELS[algo] || algo.replace(/_/g, ' ')) : '';
      html += `
        <tr class="${isOurs ? 'highlight-row' : ''}">
          <td>${displayAlgo ? `<strong>${displayAlgo}</strong>` : ''}</td>
          <td>${r.Metric?.replace(/_/g, ' ') || ''}</td>
          <td>${r.N || 20}</td>
          <td>${Number(r.Mean || 0).toFixed(2)}</td>
          <td>${Number(r.SD || 0).toFixed(2)}</td>
          <td>${Number(r.Median || 0).toFixed(2)}</td>
          <td>[${Number(r.CI_95_Lower || 0).toFixed(2)}, ${Number(r.CI_95_Upper || 0).toFixed(2)}]</td>
        </tr>
      `;
    });
  });

  html += '</tbody>';
  table.innerHTML = html;
}

// ── Mock Data Fallbacks ─────────────────────────────────────────────────────
function getMockKpi() {
  return {
    models: MODEL_ORDER,
    metrics: [
      'Total Energy Cost (INR)', 'Peak Grid Load (kW)', 'Makespan (hours)',
      'Machine Utilization (%)', 'Average Waiting Time (min)', 'On-Time Completion (%)',
      'Carbon Emissions (tCO2)', 'Power Factor Penalty (INR)'
    ],
    values: MODEL_ORDER.map(() => [
      [181528, 784.5, 47.25, 45.77, 45, 100, 671.9, 30660],
      [174318, 784.5, 47.25, 45.77, 65, 100, 705.2, 29452],
      [164128, 784.5, 48.0, 45.05, 79, 97.5, 723.1, 27935],
      [179592, 784.5, 47.25, 45.77, 58, 100, 666.6, 30458],
      [181284, 784.5, 47.25, 45.77, 47, 100, 668.6, 30724],
      [177671, 784.5, 47.25, 45.77, 54, 100, 659.7, 30031],
      [162875, 784.5, 47.5, 45.53, 89, 100, 624.8, 27658],
      [160398, 784.5, 50.5, 42.82, 100, 100, 619.5, 27324],
      [120183, 454.5, 51.5, 41.99, 112, 100, 483.9, 20431],
      [78302, 161.5, 55.5, 38.96, 420, 94.4, 573.3, 13528],
    ]),
    improvements: {}
  };
}

function getMockForecast() {
  return Array.from({length: 192}, (_, i) => ({
    Slot: i,
    Load_Type: (i >= 32 && i < 72) || (i >= 128 && i < 168) ? 'Maximum_Load' : 'Medium_Load'
  }));
}

function getMockSchedule() {
  return Array.from({length: 40}, (_, i) => ({
    Job_ID: `J${String(i + 1).padStart(3, '0')}`, Machine_ID: `M0${(i % 8) + 1}`,
    Assigned_Machine: `M0${(i % 8) + 1}`, Machine_Type: 'CNC_Machining',
    Priority: (i % 3) + 1, Start_Slot: (i * 4) % 160, End_Slot: ((i * 4) % 160) + 4,
    Start_Time: '08:00', End_Time: '09:00', Duration_min: 60, Delay_min: 0,
    'Energy_Cost_$': 400 + i * 20, Is_Late: 0
  }));
}

function getMockMachines() {
  return { count: 8, columns: ['Machine_ID','Machine_Type','Idle_Power_kW','Active_Power_kW','Setup_Energy_kW','Changeover_Time_min'],
    data: [
      {Machine_ID:'M01',Machine_Type:'CNC_Machining',Idle_Power_kW:3.85,Active_Power_kW:88.0,Setup_Energy_kW:15.63,Changeover_Time_min:15},
      {Machine_ID:'M02',Machine_Type:'Laser_Cutting',Idle_Power_kW:9.85,Active_Power_kW:35.0,Setup_Energy_kW:5.55,Changeover_Time_min:15},
      {Machine_ID:'M03',Machine_Type:'Welding_Robot',Idle_Power_kW:4.15,Active_Power_kW:175.0,Setup_Energy_kW:21.88,Changeover_Time_min:15},
      {Machine_ID:'M04',Machine_Type:'Heat_Treatment',Idle_Power_kW:6.34,Active_Power_kW:75.0,Setup_Energy_kW:12.95,Changeover_Time_min:15},
      {Machine_ID:'M05',Machine_Type:'Stamping_Press',Idle_Power_kW:8.79,Active_Power_kW:95.0,Setup_Energy_kW:15.42,Changeover_Time_min:15},
      {Machine_ID:'M06',Machine_Type:'Assembly_Line',Idle_Power_kW:6.99,Active_Power_kW:155.0,Setup_Energy_kW:15.92,Changeover_Time_min:15},
      {Machine_ID:'M07',Machine_Type:'Injection_Moulding',Idle_Power_kW:7.99,Active_Power_kW:42.0,Setup_Energy_kW:3.63,Changeover_Time_min:15},
      {Machine_ID:'M08',Machine_Type:'Surface_Grinding',Idle_Power_kW:10.45,Active_Power_kW:110.0,Setup_Energy_kW:15.75,Changeover_Time_min:15},
    ]};
}

function getMockJobs() {
  return { count: 20, columns: ['Job_ID','Duration_min','Deadline','Priority','Compatible_Machines','Arrival_Time','Setup_Type'],
    stats: { total_jobs: 20, avg_duration_min: 62.75, min_duration_min: 15, max_duration_min: 150, priority_distribution: {1:4,2:11,3:5}, setup_type_distribution: {} },
    data: Array.from({length: 20}, (_, i) => ({
      Job_ID: `J${String(i+1).padStart(3,'0')}`, Duration_min: [15,30,45,60,75,90][i%6],
      Deadline: 100 + i*5, Priority: (i%3)+1, Compatible_Machines: 'M01,M02,M03',
      Arrival_Time: i*8, Setup_Type: ['Type_A','Type_B','Type_C'][i%3]
    }))};
}

// ── Initialization ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Sidebar nav click handlers
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const page = item.dataset.page;
      window.location.hash = page;
    });
  });

  // Mobile hamburger
  const hamburger = document.getElementById('hamburger-btn');
  const sidebar = document.getElementById('sidebar');
  if (hamburger && sidebar) {
    hamburger.addEventListener('click', () => sidebar.classList.toggle('open'));
  }

  // Listen for hash changes
  window.addEventListener('hashchange', handleHashChange);

  // Initial route
  handleHashChange();
});
