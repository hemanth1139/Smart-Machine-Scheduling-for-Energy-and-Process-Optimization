// Configuration
const API_BASE = 'https://smart-machine-scheduling-for-energy-and.onrender.com';

// Constants
const MODEL_ORDER = ['FCFS','EDF','Makespan_Greedy','Deterministic_Greedy','Proposed_Robust_Greedy','Hybrid_Solver'];
const SHORT_LABELS = {FCFS:'FCFS', EDF:'EDF', Makespan_Greedy:'Makespan', Deterministic_Greedy:'Det. Greedy', Proposed_Robust_Greedy:'Robust Greedy', Hybrid_Solver:'Hybrid CP-SAT'};
const FULL_LABELS = {FCFS:'FCFS (Baseline)', EDF:'Earliest Deadline First', Makespan_Greedy:'Makespan-Only Greedy', Deterministic_Greedy:'Deterministic Energy-Aware Greedy', Proposed_Robust_Greedy:'Robust Energy-Aware Greedy', Hybrid_Solver:'Hybrid CP-SAT Solver'};
const MODEL_COLORS = {FCFS:'#ef4444', EDF:'#f97316', Makespan_Greedy:'#f59e0b', Deterministic_Greedy:'#6366f1', Proposed_Robust_Greedy:'#4f46e5', Hybrid_Solver:'#1e1b4b'};
const HIGHER_BETTER = new Set(['On-Time Completion (%)','Machine Utilization (%)']);

const ALGO_INFO = [
  {key:'FCFS', tag:'Baseline', tagColor:'#fef2f2', tagText:'#b91c1c', name:'First-Come First-Served (FCFS)', desc:'Processes jobs strictly by arrival timestamp. Energy-blind and causes severe peak tariff overlaps.'},
  {key:'EDF', tag:'Classical', tagColor:'#fffbeb', tagText:'#92400e', name:'Earliest Deadline First (EDF)', desc:'Prioritises urgent job deadlines to minimize lateness, but ignores electricity tariff pricing.'},
  {key:'Makespan_Greedy', tag:'Classical', tagColor:'#fffbeb', tagText:'#92400e', name:'Makespan-Only Greedy', desc:'Focuses purely on total completion throughput. Fast execution but leads to high peak power draw.'},
  {key:'Deterministic_Greedy', tag:'Energy-Aware', tagColor:'#eff6ff', tagText:'#1d4ed8', name:'Deterministic Energy Greedy', desc:'Routes jobs to cheaper time windows based on static tariff schedules. First energy-aware heuristic.'},
  {key:'Proposed_Robust_Greedy', tag:'Energy-Aware', tagColor:'#eff6ff', tagText:'#1d4ed8', name:'Robust Energy Greedy', desc:'Enhances deterministic greedy with XGBoost forecast quantile uncertainty for resilient schedules.'},
  {key:'Hybrid_Solver', tag:'Proposed AI Model', tagColor:'#ede9fe', tagText:'#5b21b6', name:'Hybrid CP-SAT AI Solver', desc:'Google OR-Tools CP-SAT solver. Jointly optimizes energy tariff, peak load, carbon footprint, and deadlines.', ours:true},
];

// Global State
let globalKpi = null;
let globalForecast = null;

// Helpers
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

const fmt = (n, prefix='', suffix='', decimals=0) => {
  if (n === null || n === undefined || isNaN(n)) return '-';
  return `${prefix}${Number(n).toLocaleString(undefined, {minimumFractionDigits: decimals, maximumFractionDigits: decimals})}${suffix}`;
};

const computeImprovement = (kpi, metric, model) => {
  if (kpi.improvements && kpi.improvements[model] && kpi.improvements[model][metric] !== undefined) {
    return kpi.improvements[model][metric];
  }
  const modelIdx = kpi.models.indexOf(model);
  const baselineIdx = kpi.models.indexOf('FCFS');
  const metricIdx = kpi.metrics.indexOf(metric);
  if(modelIdx===-1 || baselineIdx===-1 || metricIdx===-1) return 0;
  const val = kpi.values[modelIdx][metricIdx];
  const base = kpi.values[baselineIdx][metricIdx];
  if (base === 0) return 0;
  const pct = ((val - base) / base) * 100;
  return HIGHER_BETTER.has(metric) ? pct : -pct;
};

const computeCompositeScore = (kpi, model) => {
  const modelIdx = kpi.models.indexOf(model);
  if(modelIdx===-1) return 0;
  let score = 0, count = 0;
  kpi.metrics.forEach((metric, mIdx) => {
    let min = Infinity, max = -Infinity;
    kpi.values.forEach(row => {
      const v = row[mIdx];
      if(v < min) min = v;
      if(v > max) max = v;
    });
    if(max > min) {
      const val = kpi.values[modelIdx][mIdx];
      let norm = (val - min) / (max - min);
      if(!HIGHER_BETTER.has(metric)) norm = 1 - norm;
      score += norm;
      count++;
    }
  });
  return count > 0 ? (score / count) * 100 : 0;
};

const normalizeKpi = (raw) => {
  const values = raw.models.map(model =>
    raw.metrics.map(metric => (raw.values[model] ? (raw.values[model][metric] ?? 0) : 0))
  );
  return { ...raw, values };
};

// Main Initialization
async function init() {
  showLoading();
  try {
    const [kpiResp, scheduleResp, forecastResp] = await Promise.all([
      fetch(`${API_BASE}/api/kpi`),
      fetch(`${API_BASE}/api/schedule/Hybrid_Solver`),
      fetch(`${API_BASE}/api/forecast`),
    ]);

    if (!kpiResp.ok) throw new Error(`API error ${kpiResp.status}`);

    const rawKpi = await kpiResp.json();
    globalKpi = normalizeKpi(rawKpi);
    const schedule = await scheduleResp.json();
    globalForecast = await forecastResp.json();

    document.getElementById('api-status-text').innerText = 'Backend API Online';

    renderHero(globalKpi);
    renderAlgoCards();
    renderLeaderboard(globalKpi);
    renderImprovementHeatmap(globalKpi);
    renderCompositeBar(globalKpi);
    renderBubbleChart(globalKpi);
    renderWinBoxes(globalKpi);
    renderKPICards(globalKpi);
    renderScheduleStats(schedule);
    renderGantt(schedule, globalForecast);
    renderScheduleTable(schedule);

    // Setup Model Selector Event Listener
    const selector = document.getElementById('model-selector');
    if (selector) {
      selector.addEventListener('change', async (e) => {
        const selectedModel = e.target.value;
        try {
          showLoading();
          const resp = await fetch(`${API_BASE}/api/schedule/${selectedModel}`);
          const newSchedule = await resp.json();
          renderScheduleStats(newSchedule);
          renderGantt(newSchedule, globalForecast);
          renderScheduleTable(newSchedule);
        } catch (err) {
          console.error('Error fetching schedule model:', err);
        } finally {
          hideLoading();
        }
      });
    }

  } catch(e) {
    console.warn('API error, falling back to client-side demonstration data:', e);
    document.getElementById('api-status-text').innerText = 'Using Offline Demo Mode';
    renderMockAll();
  } finally {
    hideLoading();
  }
}

// Render Functions
const renderHero = (kpi) => {
  const hybridIdx = kpi.models.indexOf('Hybrid_Solver');
  const fcfsIdx = kpi.models.indexOf('FCFS');
  if(hybridIdx===-1 || fcfsIdx===-1) return;

  const getMetricVal = (mName) => {
    const mIdx = kpi.metrics.findIndex(m => m.toLowerCase().includes(mName.toLowerCase()));
    return mIdx !== -1 ? kpi.values[hybridIdx][mIdx] : 0;
  };
  const getFcfsVal = (mName) => {
    const mIdx = kpi.metrics.findIndex(m => m.toLowerCase().includes(mName.toLowerCase()));
    return mIdx !== -1 ? kpi.values[fcfsIdx][mIdx] : 0;
  };

  const hybridCost = getMetricVal('cost');
  const fcfsCost = getFcfsVal('cost');
  const savings = fcfsCost - hybridCost;
  const savingsPct = fcfsCost > 0 ? (savings / fcfsCost) * 100 : 0;

  const peakCut = computeImprovement(kpi, kpi.metrics.find(m => m.includes('Peak')) || 'Peak Grid Load (kW)', 'Hybrid_Solver');
  const co2Cut = computeImprovement(kpi, kpi.metrics.find(m => m.includes('Carbon')) || 'Carbon Emissions (tCO2)', 'Hybrid_Solver');
  const onTime = getMetricVal('on-time');

  document.getElementById('stat-savings').innerText = fmt(savings, '₹', '', 0);
  document.getElementById('stat-savings-pct').innerText = fmt(savingsPct, '', '%', 1);
  document.getElementById('stat-peak-cut').innerText = fmt(peakCut, '', '%', 1);
  document.getElementById('stat-co2-cut').innerText = fmt(co2Cut, '', '%', 1);
  document.getElementById('stat-late-jobs').innerText = fmt(onTime, '', '%', 0);
};

const renderAlgoCards = () => {
  const container = document.getElementById('algo-cards');
  if (!container) return;

  container.innerHTML = ALGO_INFO.map(algo => `
    <div class="algo-card ${algo.ours ? 'our-model' : ''}">
      <div>
        <span class="tag-pill" style="background-color: ${algo.tagColor}; color: ${algo.tagText};">
          ${algo.tag}
        </span>
        <h4>${algo.name}</h4>
        <p>${algo.desc}</p>
      </div>
    </div>
  `).join('');
};

const renderLeaderboard = (kpi) => {
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
      isOurs: model === 'Hybrid_Solver',
    };
  });

  // Sort by energy cost ascending
  rows.sort((a, b) => a.cost - b.cost);

  let html = `
    <thead>
      <tr>
        <th>Rank</th>
        <th>Algorithm / Model</th>
        <th>Energy Cost (₹)</th>
        <th>Peak Load (kW)</th>
        <th>Carbon Footprint</th>
        <th>On-Time Rate</th>
        <th>Makespan (hrs)</th>
      </tr>
    </thead>
    <tbody>
  `;

  rows.forEach((r, rank) => {
    html += `
      <tr class="${r.isOurs ? 'highlight-row' : ''}">
        <td><strong>#${rank + 1}</strong></td>
        <td><strong>${r.label}</strong> ${r.isOurs ? '✨ (Proposed)' : ''}</td>
        <td>${fmt(r.cost, '₹', '', 0)}</td>
        <td>${fmt(r.peak, '', ' kW', 1)}</td>
        <td>${fmt(r.co2, '', ' tCO₂', 1)}</td>
        <td>${fmt(r.onTime, '', '%', 0)}</td>
        <td>${fmt(r.makespan, '', ' hrs', 1)}</td>
      </tr>
    `;
  });

  html += '</tbody>';
  table.innerHTML = html;
};

const renderImprovementHeatmap = (kpi) => {
  const el = document.getElementById('improvement-heatmap');
  if (!el || typeof Plotly === 'undefined') return;

  const models = kpi.models.filter(m => m !== 'FCFS');
  const metrics = kpi.metrics;

  const zData = metrics.map(metric => {
    return models.map(model => computeImprovement(kpi, metric, model));
  });

  const textData = zData.map(row => row.map(v => `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`));

  const data = [{
    z: zData,
    x: models.map(m => SHORT_LABELS[m] || m),
    y: metrics,
    text: textData,
    texttemplate: "%{text}",
    type: 'heatmap',
    colorscale: [
      [0, '#ef4444'],
      [0.5, '#f8fafc'],
      [1.0, '#10b981']
    ],
    showscale: true,
  }];

  const layout = {
    title: { text: '% Metric Improvement Relative to FCFS Baseline (Green = Better)', font: { size: 14, weight: 700 } },
    font: { family: 'Inter, sans-serif', size: 11, color: '#334155' },
    margin: { l: 180, r: 40, t: 50, b: 60 },
    paper_bgcolor: '#ffffff',
    plot_bgcolor: '#ffffff',
  };

  Plotly.newPlot('improvement-heatmap', data, layout, { responsive: true, displayModeBar: false });
};

const renderCompositeBar = (kpi) => {
  const el = document.getElementById('composite-bar');
  if (!el || typeof Plotly === 'undefined') return;

  const scores = kpi.models.map(m => ({
    model: m,
    label: SHORT_LABELS[m] || m,
    score: computeCompositeScore(kpi, m),
    color: MODEL_COLORS[m] || '#6366f1'
  }));

  scores.sort((a, b) => a.score - b.score);

  const data = [{
    type: 'bar',
    x: scores.map(s => s.score),
    y: scores.map(s => s.label),
    orientation: 'h',
    marker: { color: scores.map(s => s.color) }
  }];

  const layout = {
    title: { text: 'Overall Composite Efficiency Index (0-100)', font: { size: 14, weight: 700 } },
    xaxis: { title: 'Composite Score', range: [0, 100] },
    font: { family: 'Inter, sans-serif', size: 11, color: '#334155' },
    margin: { l: 100, r: 30, t: 50, b: 40 },
    paper_bgcolor: '#ffffff',
    plot_bgcolor: '#ffffff',
  };

  Plotly.newPlot('composite-bar', data, layout, { responsive: true, displayModeBar: false });
};

const renderBubbleChart = (kpi) => {
  const el = document.getElementById('bubble-chart');
  if (!el || typeof Plotly === 'undefined') return;

  const getMetricVal = (mIdx, mName) => {
    const idx = kpi.metrics.findIndex(m => m.toLowerCase().includes(mName.toLowerCase()));
    return idx !== -1 ? kpi.values[mIdx][idx] : 0;
  };

  const data = kpi.models.map((m, idx) => {
    const cost = getMetricVal(idx, 'cost');
    const onTime = getMetricVal(idx, 'on-time');
    const co2 = getMetricVal(idx, 'carbon');

    return {
      x: [cost],
      y: [onTime],
      text: [SHORT_LABELS[m] || m],
      mode: 'markers+text',
      textposition: 'top center',
      name: SHORT_LABELS[m] || m,
      marker: {
        size: [Math.max(15, co2 / 100)],
        color: MODEL_COLORS[m] || '#6366f1',
        opacity: 0.85
      }
    };
  });

  const layout = {
    title: { text: 'Trade-off: Energy Cost vs On-Time Completion (Bubble = Carbon)', font: { size: 14, weight: 700 } },
    xaxis: { title: 'Total Energy Cost (₹)' },
    yaxis: { title: 'On-Time Completion (%)', range: [50, 105] },
    font: { family: 'Inter, sans-serif', size: 11, color: '#334155' },
    margin: { l: 60, r: 40, t: 50, b: 50 },
    paper_bgcolor: '#ffffff',
    plot_bgcolor: '#ffffff',
    showlegend: false,
  };

  Plotly.newPlot('bubble-chart', data, layout, { responsive: true, displayModeBar: false });
};

const renderWinBoxes = (kpi) => {
  const el = document.getElementById('win-boxes');
  if (!el) return;

  const hybridIdx = kpi.models.indexOf('Hybrid_Solver');
  const fcfsIdx = kpi.models.indexOf('FCFS');
  if(hybridIdx===-1 || fcfsIdx===-1) return;

  const getVal = (mIdx, mName) => {
    const idx = kpi.metrics.findIndex(m => m.toLowerCase().includes(mName.toLowerCase()));
    return idx !== -1 ? kpi.values[mIdx][idx] : 0;
  };

  const hybridCost = getVal(hybridIdx, 'cost');
  const fcfsCost = getVal(fcfsIdx, 'cost');
  const savings = fcfsCost - hybridCost;

  const peakCut = computeImprovement(kpi, kpi.metrics.find(m => m.includes('Peak')) || 'Peak Grid Load (kW)', 'Hybrid_Solver');
  const co2Cut = computeImprovement(kpi, kpi.metrics.find(m => m.includes('Carbon')) || 'Carbon Emissions (tCO2)', 'Hybrid_Solver');

  el.innerHTML = `
    <div class="win-box">
      <div class="win-value">${fmt(savings, '₹', '', 0)}</div>
      <div class="win-label">Total Cost Savings</div>
      <p class="win-desc">Direct electricity bill reduction per benchmark cycle</p>
    </div>
    <div class="win-box">
      <div class="win-value">${fmt(peakCut, '', '%', 1)}</div>
      <div class="win-label">Peak Demand Shaving</div>
      <p class="win-desc">Prevents peak utility surge charges and grid penalties</p>
    </div>
    <div class="win-box">
      <div class="win-value">${fmt(co2Cut, '', '%', 1)}</div>
      <div class="win-label">Carbon Abatement</div>
      <p class="win-desc">Significant greenhouse gas emission reductions</p>
    </div>
  `;
};

const renderKPICards = (kpi) => {
  const el = document.getElementById('kpi-cards');
  if (!el) return;

  const hybridIdx = kpi.models.indexOf('Hybrid_Solver');
  if(hybridIdx === -1) return;

  const displayMetrics = kpi.metrics.slice(0, 6);

  el.innerHTML = displayMetrics.map((metric, mIdx) => {
    const val = kpi.values[hybridIdx][mIdx];
    const imp = computeImprovement(kpi, metric, 'Hybrid_Solver');

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
};

const renderScheduleStats = (schedule) => {
  const el = document.getElementById('schedule-stats');
  if (!el || !Array.isArray(schedule)) return;

  const totalJobs = schedule.length;
  const machines = new Set(schedule.map(j => j.Assigned_Machine || j.Machine)).size;
  const totalCost = schedule.reduce((sum, j) => sum + (Number(j.Energy_Cost) || 0), 0);

  el.innerHTML = `
    <div class="kpi-card">
      <div class="kpi-title">Total Scheduled Jobs</div>
      <div class="kpi-value">${totalJobs}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Active Fleet Machines</div>
      <div class="kpi-value">${machines}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Scheduled Energy Cost</div>
      <div class="kpi-value">${fmt(totalCost, '₹', '', 0)}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">On-Time Execution</div>
      <div class="kpi-value">100%</div>
    </div>
  `;
};

const renderGantt = (schedule, forecast) => {
  const el = document.getElementById('gantt-chart');
  if (!el || typeof Plotly === 'undefined' || !Array.isArray(schedule)) return;

  const baseTime = new Date('2024-01-01T00:00:00Z').getTime();

  const data = schedule.map(job => {
    const startMs = baseTime + (Number(job.Start_Slot) || 0) * 15 * 60 * 1000;
    const durMs = Math.max(1, (Number(job.End_Slot || job.Start_Slot + 1) - Number(job.Start_Slot)) * 15 * 60 * 1000);
    const priority = job.Priority || 'Medium';

    return {
      x: [durMs],
      y: [job.Assigned_Machine || job.Machine || 'M1'],
      base: [startMs],
      type: 'bar',
      orientation: 'h',
      name: `Job ${job.Job_ID}`,
      text: `${job.Job_ID} (${priority})`,
      textposition: 'inside',
      marker: {
        color: priority === 'High' ? '#ef4444' : (priority === 'Medium' ? '#f59e0b' : '#10b981'),
        opacity: 0.85
      },
      hoverinfo: 'text',
      hovertext: `<b>${job.Job_ID}</b><br>Machine: ${job.Assigned_Machine}<br>Priority: ${priority}<br>Slots: ${job.Start_Slot} → ${job.End_Slot}<br>Energy Cost: ₹${Number(job.Energy_Cost || 0).toFixed(1)}`
    };
  });

  const shapes = [];
  if (Array.isArray(forecast)) {
    forecast.forEach(slot => {
      if (slot.Load_Type === 'Maximum_Load') {
        const start = baseTime + (slot.Slot) * 15 * 60 * 1000;
        const end = baseTime + (slot.Slot + 1) * 15 * 60 * 1000;
        shapes.push({
          type: 'rect',
          xref: 'x',
          yref: 'paper',
          x0: start,
          x1: end,
          y0: 0,
          y1: 1,
          fillcolor: 'rgba(239, 68, 68, 0.12)',
          line: { width: 0 }
        });
      }
    });
  }

  const layout = {
    title: { text: 'Machine Job Allocation Timeline (Red Shading = Peak TOU Electricity Tariff)', font: { size: 14, weight: 700 } },
    xaxis: { type: 'date', title: 'Operational Timeline' },
    yaxis: { title: 'Assigned Machine Fleet', categoryorder: 'category ascending' },
    shapes,
    showlegend: false,
    paper_bgcolor: '#ffffff',
    plot_bgcolor: '#ffffff',
    font: { family: 'Inter, sans-serif', size: 11, color: '#334155' },
    margin: { l: 80, r: 30, t: 50, b: 50 },
    barmode: 'stack'
  };

  Plotly.newPlot('gantt-chart', data, layout, { responsive: true, displayModeBar: false });
};

const renderScheduleTable = (schedule) => {
  const table = document.getElementById('schedule-table');
  if (!table || !Array.isArray(schedule)) return;

  let html = `
    <thead>
      <tr>
        <th>Job ID</th>
        <th>Assigned Machine</th>
        <th>Priority</th>
        <th>Start Slot</th>
        <th>End Slot</th>
        <th>Duration (Slots)</th>
        <th>Delay</th>
        <th>Energy Cost (₹)</th>
      </tr>
    </thead>
    <tbody>
  `;

  schedule.slice(0, 50).forEach(j => {
    const priority = j.Priority || 'Medium';
    const dur = (Number(j.End_Slot) || 0) - (Number(j.Start_Slot) || 0);
    html += `
      <tr>
        <td><strong>${j.Job_ID}</strong></td>
        <td>${j.Assigned_Machine || j.Machine}</td>
        <td><span class="badge-priority ${priority}">${priority}</span></td>
        <td>${j.Start_Slot}</td>
        <td>${j.End_Slot}</td>
        <td>${dur} slots (${dur * 15}m)</td>
        <td>${j.Delay_Slots || 0}</td>
        <td>${fmt(j.Energy_Cost, '₹', '', 1)}</td>
      </tr>
    `;
  });

  html += '</tbody>';
  table.innerHTML = html;
};

// Fallback Mock Demo
const renderMockAll = () => {
  const mockKpi = {
    models: MODEL_ORDER,
    metrics: ['Total Energy Cost (INR)', 'Peak Grid Load (kW)', 'Carbon Emissions (tCO2)', 'On-Time Completion (%)', 'Average Waiting Time (min)', 'Makespan (hours)'],
    values: [
      [186096, 778.9, 2950, 100, 0, 49.2],
      [185686, 778.9, 3031, 100, 0, 49.0],
      [186096, 778.9, 2950, 100, 0, 49.2],
      [167723, 778.9, 2757, 100, 0, 49.2],
      [167723, 778.9, 2757, 100, 0, 49.2],
      [125350, 448.9, 2191, 100, 0, 50.0]
    ]
  };

  const mockForecast = Array.from({length: 96}, (_, i) => ({
    Slot: i,
    Load_Type: (i >= 20 && i <= 36) ? 'Maximum_Load' : 'Medium_Load'
  }));

  const mockSchedule = Array.from({length: 30}, (_, i) => ({
    Job_ID: `J${100 + i}`,
    Assigned_Machine: `Machine_${(i % 5) + 1}`,
    Priority: ['High', 'Medium', 'Low'][i % 3],
    Start_Slot: (i * 3) % 80,
    End_Slot: ((i * 3) % 80) + 4,
    Delay_Slots: 0,
    Energy_Cost: 450 + (i * 15)
  }));

  renderHero(mockKpi);
  renderAlgoCards();
  renderLeaderboard(mockKpi);
  renderImprovementHeatmap(mockKpi);
  renderCompositeBar(mockKpi);
  renderBubbleChart(mockKpi);
  renderWinBoxes(mockKpi);
  renderKPICards(mockKpi);
  renderScheduleStats(mockSchedule);
  renderGantt(mockSchedule, mockForecast);
  renderScheduleTable(mockSchedule);
};

document.addEventListener('DOMContentLoaded', init);
