/**
 * POLAR ENERGY AI - RESEARCHER & SCIENTIFIC ACTIVITY SCHEDULER
 * Green Energy Surplus Windows, Experiment Queue, and AI Allocation Advisor
 */

import { apiFetch, GlobalState, subscribeState, showToast } from './app.js';

export function initResearcher() {
  loadGreenWindows();
  loadActivities();
  bindForm();
  subscribeState(() => {
    loadActivities();
  });
}

/**
 * Load and render Green Energy Surplus Windows
 */
async function loadGreenWindows() {
  const container = document.getElementById('greenWindowsTimeline');
  if (!container) return;

  try {
    const data = await apiFetch('/api/optimization/green-windows?required_kwh=25.0&duration_hrs=3.5');
    if (!data || !data.windows) return;

    let html = '';
    data.windows.forEach(w => {
      const isGreen = w.is_green;
      const cardClass = isGreen ? 'green-slot-active' : 'green-slot-deficit';
      const badge = isGreen
        ? '<span class="badge badge-normal">SURPLUS WINDOW</span>'
        : '<span class="badge badge-warning">DEFICIT / CONSERVE</span>';

      html += `
        <div class="card ${cardClass}" style="border-left: 4px solid ${isGreen ? 'var(--emerald)' : 'var(--border-subtle)'};">
          <div class="card-header">
            <span class="card-title">${w.time_label}</span>
            ${badge}
          </div>
          <div style="font-family: var(--font-mono); font-size: 1.1rem; font-weight: 700; color: ${isGreen ? 'var(--emerald)' : 'var(--text-dim)'};">
            ${w.surplus_kw > 0 ? '+' : ''}${w.surplus_kw.toFixed(1)} kW Renewable Margin
          </div>
          <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 6px;">
            ${w.recommendation}
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  } catch (err) {
    console.warn("Error fetching green windows:", err);
  }
}

/**
 * Load and render the science activities table
 */
async function loadActivities() {
  const tbody = document.getElementById('activityTableBody');
  if (!tbody) return;

  try {
    const data = await apiFetch(`/api/activities?station_id=${GlobalState.stationId}&surplus_kw=8.5`);
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
          <strong>${act.name}</strong>
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

