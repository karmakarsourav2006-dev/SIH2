/**
 * POLAR ENERGY AI - RESEARCHER & SCIENTIFIC ACTIVITY SCHEDULER
 * Green Energy Surplus Windows, Experiment Queue, and AI Allocation Advisor
 */

import { apiFetch, GlobalState, subscribeState, showToast, escapeHtml, simulationInputs } from './app.js';

let windowRequest = 0;
let activityRequest = 0;

export function initResearcher() {
  loadGreenWindows();
  loadActivities();
  bindForm();
  document.getElementById('btnFindWindow')?.addEventListener('click', () => loadGreenWindows());
  subscribeState(() => {
    loadActivities();
  });
  window.addEventListener('polar:activitiesUpdated', () => {
    loadActivities();
  });
}

/**
 * Load and render Green Energy Surplus Windows
 */
async function loadGreenWindows(activity = null) {
  const container = document.getElementById('greenWindowsTimeline');
  if (!container) return;
  const request = ++windowRequest;
  const required = Number(activity?.required_kwh ?? document.getElementById('inpActKwh').value);
  const duration = Number(activity?.duration_hrs ?? document.getElementById('inpActDuration').value);
  if (!(required > 0 && duration > 0)) { showToast('Enter positive energy and duration values', 'warning'); return; }
  container.textContent = 'ANALYZING RENEWABLE WINDOW...';

  try {
    const data = await apiFetch(`/api/optimization/green-windows?required_kwh=${required}&duration_hrs=${duration}`);
    if (request !== windowRequest) return;
    if (!data || !data.windows) return;

    let html = `<p class="text-muted">${escapeHtml(activity?.name || 'Proposed experiment')} · ${required} kWh / ${duration} hrs. Backend simulated forecast; slots do not reserve a schedule.</p>`;
    if (!data.windows.length) html += '<p class="text-amber">DELAY — No supported surplus window for this energy requirement.</p>';
    data.windows.forEach(w => {
      const isGreen = true; // This endpoint returns only qualifying windows.
      const cardClass = isGreen ? 'green-slot-active' : 'green-slot-deficit';
      const badge = isGreen
        ? '<span class="badge badge-normal">SURPLUS WINDOW</span>'
        : '<span class="badge badge-warning">DEFICIT / CONSERVE</span>';

      html += `
        <div class="card ${cardClass}" style="border-left: 4px solid ${isGreen ? 'var(--emerald)' : 'var(--border-subtle)'};">
          <div class="card-header">
            <span class="card-title">${escapeHtml(w.slot)}</span>
            ${badge}
          </div>
          <div style="font-family: var(--font-mono); font-size: 1.1rem; font-weight: 700; color: ${isGreen ? 'var(--emerald)' : 'var(--text-dim)'};">
            ${w.surplus_kw > 0 ? '+' : ''}${w.surplus_kw.toFixed(1)} kW Renewable Margin
          </div>
          <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 6px;">
            SAFE TO RUN · Confidence: ${escapeHtml(w.confidence)}<br>
            Expected carbon saving: ${w.carbon_saving_kg} kg · Required power: ${data.avg_kw_needed} kW
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  } catch (err) {
    console.warn("Error fetching green windows:", err);
    if (request === windowRequest) container.textContent = 'FORECAST UNAVAILABLE — Try finding a window again.';
  }
}

/**
 * Load and render the science activities table
 */
async function loadActivities() {
  const tbody = document.getElementById('activityTableBody');
  if (!tbody) return;
  const request = ++activityRequest;
  const stationId = GlobalState.stationId;

  try {
    const telemetry = await apiFetch('/api/telemetry', {method: 'POST', body: JSON.stringify({station_id: stationId, ...simulationInputs()})});
    const state = telemetry.state;
    const surplus = state.is_critical ? 0 : Math.max(0, state.total_renewables_kw - state.active_demand_kw);
    const data = await apiFetch(`/api/activities?station_id=${encodeURIComponent(stationId)}&surplus_kw=${surplus}`);
    if (request !== activityRequest || stationId !== GlobalState.stationId) return;
    if (!data || !data.activities) return;

    tbody.innerHTML = '';
    data.activities.forEach(act => {
      const tr = document.createElement('tr');
      const isRunning = act.execution_status === 'RUNNING';
      const isCompleted = act.execution_status === 'COMPLETED';

      const statusBadge = isRunning
        ? '<span class="badge badge-normal">RUNNING</span>'
        : isCompleted
        ? '<span class="badge" style="background: rgba(148,163,184,0.2); color:#94a3b8;">COMPLETED</span>'
        : act.execution_status === 'DEFERRED'
        ? '<span class="badge badge-warning">DEFERRED</span>'
        : '<span class="badge badge-info">QUEUED</span>';

      const recBadge = act.safe_to_run
        ? `<span class="badge badge-normal" style="font-size:0.65rem;">✓ SAFE ON SURPLUS</span>`
        : `<span class="badge badge-warning" style="font-size:0.65rem;">⚠️ PEAK DRAIN</span>`;

      tr.innerHTML = `
        <td>
          <strong>${escapeHtml(act.name)}</strong>
          <div class="text-muted">Priority: P${act.priority}</div>
          <div style="font-size:0.68rem; color:var(--text-dim);">ID: ${act.id} // Window: ${act.recommended_slot || 'Dynamic'}</div>
        </td>
        <td>
          <span style="font-family: var(--font-mono);">${act.required_kwh.toFixed(1)} kWh</span>
          <div style="font-size:0.68rem; color:var(--text-dim);">~${act.avg_power_kw || (act.required_kwh/act.duration_hrs).toFixed(1)} kW avg</div>
        </td>
        <td>${act.duration_hrs.toFixed(1)} hrs</td>
        <td>${statusBadge}</td>
        <td>
          <div style="font-size:0.72rem; color:var(--text-muted);">${act.ai_recommendation || 'Evaluated'}</div>
          ${recBadge}
        </td>
        <td style="text-align: right;">
          <div style="display:flex; gap:6px; justify-content:flex-end;">
            <button class="btn" data-action="window">FIND OPTIMAL WINDOW</button>
            ${!isRunning && !isCompleted ? `
              <button class="btn btn-success" data-action="run" data-id="${act.id}" style="padding:4px 8px; font-size:0.7rem;">▶ Run</button>
            ` : ''}
            ${isRunning ? `
              <button class="btn btn-danger" data-action="defer" data-id="${act.id}" style="padding:4px 8px; font-size:0.7rem;">⏸ Pause</button>
            ` : ''}
            <button class="btn btn-danger" data-action="delete" data-id="${act.id}" style="padding:4px 8px; font-size:0.7rem;">✕</button>
          </div>
        </td>
      `;

      // Event handlers for actions
      tr.querySelector('[data-action="window"]').addEventListener('click', () => {
        loadGreenWindows(act);
        document.getElementById('greenWindowsTimeline').scrollIntoView({behavior: 'smooth', block: 'center'});
      });
      const btnRun = tr.querySelector('[data-action="run"]');
      if (btnRun) {
        btnRun.addEventListener('click', () => updateSchedule(act.id, 'run'));
      }
      const btnDefer = tr.querySelector('[data-action="defer"]');
      if (btnDefer) {
        btnDefer.addEventListener('click', () => updateSchedule(act.id, 'defer'));
      }
      const btnDel = tr.querySelector('[data-action="delete"]');
      if (btnDel) {
        btnDel.addEventListener('click', () => deleteActivity(act.id));
      }

      tbody.appendChild(tr);
    });
  } catch (err) {
    console.warn("Error fetching activities:", err);
    if (request === activityRequest) tbody.innerHTML = '<tr><td colspan="6">LOAD PRIORITY EVALUATION UNAVAILABLE — refresh to retry.</td></tr>';
  }
}

/**
 * Change status of activity
 */
async function updateSchedule(id, action) {
  try {
    const res = await apiFetch(`/api/activities/${id}/schedule?action=${action}`, { method: 'POST' });
    if (res && res.ok) {
      showToast(`Experiment ${id} set to ${res.activity.execution_status}`, 'success');
      loadActivities();
    }
  } catch (e) {
    showToast(`Failed to update schedule for ${id}`, 'crit');
  }
}

/**
 * Delete activity
 */
async function deleteActivity(id) {
  try {
    const res = await apiFetch(`/api/activities/${id}`, { method: 'DELETE' });
    if (res && res.ok) {
      showToast(`Activity ${id} removed`, 'info');
      loadActivities();
    }
  } catch (e) {
    showToast(`Failed to delete activity ${id}`, 'crit');
  }
}

/**
 * Handle new experiment submission
 */
function bindForm() {
  const form = document.getElementById('formNewActivity');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = document.getElementById('inpActName').value.trim();
    const kwh = parseFloat(document.getElementById('inpActKwh').value);
    const duration = parseFloat(document.getElementById('inpActDuration').value);
    const deadline = parseFloat(document.getElementById('inpActDeadline').value) || 24.0;
    const priority = parseInt(document.getElementById('inpActPriority').value);

    if (!name || isNaN(kwh) || isNaN(duration)) {
      showToast('Please fill out all required experiment fields', 'warning');
      return;
    }

    try {
      const payload = {
        station_id: GlobalState.stationId,
        name: name,
        required_kwh: kwh,
        duration_hrs: duration,
        deadline_hrs: deadline,
        priority: priority
      };

      const res = await apiFetch('/api/activities', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (res && res.ok) {
        showToast(`Experiment "${name}" registered in energy queue`, 'success');
        form.reset();
        loadActivities();
      }
    } catch (err) {
      showToast('Failed to queue experiment', 'crit');
    }
  });
}

// Auto-run if on researcher page
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('activityTableBody') || document.getElementById('greenWindowsTimeline')) {
    initResearcher();
  }
});




