/**
 * BOREAS AI Microgrid - Research Experiment Optimizer
 */

const API_BASE = (window.location.port === '3000') ? 'http://127.0.0.1:8000' : window.location.origin;

const container = document.getElementById('experimentsContainer');

export function initScheduler() {
  fetchAndRenderExperiments();

  // Listen for telemetry updates to re-evaluate experiment safety in real-time
  window.addEventListener('polar:telemetryUpdated', (e) => {
    const data = e.detail;
    if (data && data.power) {
      const surplus = data.power.surplus_kw || 0.0;
      const batteryPct = data.environment.soc_pct || 50.0;
      const isCritical = data.is_critical || false;
      fetchAndRenderExperiments(surplus, batteryPct, isCritical);
    }
  });
}

export async function fetchAndRenderExperiments(surplus_kw = 0.0, battery_pct = 50.0, is_critical = false) {
  if (!container) return;

  try {
    const query = new URLSearchParams({
      surplus_kw: surplus_kw.toString(),
      battery_pct: battery_pct.toString(),
      is_critical: is_critical.toString()
    });

    const res = await fetch(`${API_BASE}/api/experiments?${query.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderExperiments(data.experiments || []);
  } catch (err) {
    console.error('Failed to load experiments:', err);
  }
}

function renderExperiments(experiments) {
  if (!container) return;
  container.innerHTML = '';

  if (experiments.length === 0) {
    container.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem;">No scientific experiments queued.</div>';
    return;
  }

  experiments.forEach(exp => {
    const card = document.createElement('div');
    card.className = 'exp-card';

    // Badge styling
    let badgeClass = 'delay';
    if (exp.can_run) {
      badgeClass = 'safe';
    } else if (String(exp.badge).includes('SURVIVAL')) {
      badgeClass = 'critical';
    }

    const isRunning = exp.status === 'RUNNING';

    card.innerHTML = `
      <div class="exp-header">
        <div>
          <div class="exp-title">${exp.name}</div>
          <span style="font-family:var(--font-mono); font-size:0.68rem; color:var(--text-muted); text-transform:uppercase;">ID: ${exp.id} | Status: ${exp.status}</span>
        </div>
        <span class="exp-badge ${badgeClass}">${exp.badge}</span>
      </div>

      <div class="exp-metrics">
        <span>⚡ Budget: ${exp.required_kwh.toFixed(1)} kWh</span>
        <span>⏱ Duration: ${exp.duration_hrs.toFixed(1)} hrs</span>
        <span>🔌 Avg: ~${exp.avg_power_kw.toFixed(1)} kW</span>
      </div>

      <div class="exp-rec">
        💡 <strong>AI Guidance:</strong> ${exp.recommendation}
      </div>

      <div class="exp-actions">
        ${isRunning
          ? `<button class="btn-polar btn-shed" data-id="${exp.id}" data-act="defer">Pause / Defer</button>`
          : `<button class="btn-polar ${exp.can_run ? 'btn-restore' : ''}" data-id="${exp.id}" data-act="run">Start Task</button>`
        }
      </div>
    `;

    const btn = card.querySelector('button');
    if (btn) {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        const act = btn.getAttribute('data-act');
        await scheduleExperiment(id, act);
      });
    }

    container.appendChild(card);
  });
}

async function scheduleExperiment(id, action) {
  try {
    const res = await fetch(`${API_BASE}/api/experiments/schedule`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, action })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    fetchAndRenderExperiments();
  } catch (err) {
    console.error('Failed to schedule experiment:', err);
  }
}




