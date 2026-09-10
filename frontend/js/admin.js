/**
 * POLAR ENERGY AI - SYSTEM ADMINISTRATION & HARDWARE CONFIG
 * Critical Thresholds, Emergency Blackout Prevention, Database Seed Reset & Audit Logs
 */

import { apiFetch, GlobalState, subscribeState, showToast } from './app.js';

export function initAdmin() {
  loadHardwareConfig();
  loadAuditLogs();
  bindConfigForm();
  bindAdminActions();
  subscribeState(() => {
    loadHardwareConfig();
  });
}

/**
 * Load hardware parameters from backend
 */
async function loadHardwareConfig() {
  try {
    const data = await apiFetch(`/api/admin/config?station_id=${GlobalState.stationId}`);
    if (data && data.station) {
      const st = data.station;
      setInput('inpBatteryCapacity', st.battery_capacity_kwh);
      setInput('inpGenRating', st.generator_rating_kw);
      setInput('inpThermalRating', st.base_thermal_rating_kw);
      setText('dispStationName', `${st.name} (${st.location})`);
      setText('dispLlmProvider', data.llm_provider || 'Deterministic Polar Engine');
    }
  } catch (err) {
    console.warn("Failed to load admin station config:", err);
  }
}

function setInput(id, val) {
  const el = document.getElementById(id);
  if (el && val !== undefined) el.value = val;
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

/**
 * Handle configuration update submission
 */
function bindConfigForm() {
  const form = document.getElementById('formHardwareConfig');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const batteryCap = parseFloat(document.getElementById('inpBatteryCapacity').value);
    const genRating = parseFloat(document.getElementById('inpGenRating').value);
    const thermalRating = parseFloat(document.getElementById('inpThermalRating').value);

    try {
      const payload = {
        station_id: GlobalState.stationId,
        battery_capacity_kwh: batteryCap,
        generator_rating_kw: genRating,
        base_thermal_rating_kw: thermalRating
      };

      const res = await apiFetch('/api/admin/config', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (res && res.ok) {
        showToast('Station hardware capacities updated successfully', 'success');
      }
    } catch (err) {
      showToast('Failed to update hardware config', 'crit');
    }
  });
}

/**
 * Bind Emergency and Reset Actions
 */
function bindAdminActions() {
  // 1. Emergency Shed
  const btnShed = document.getElementById('btnAdminShed');
  if (btnShed) {
    btnShed.addEventListener('click', async () => {
      try {
        const res = await apiFetch('/api/emergency/shed', {
          method: 'POST',
          body: JSON.stringify({ station_id: GlobalState.stationId })
        });
        if (res && res.ok) {
          showToast(`Emergency shed executed. Assets isolated: ${res.shedded_assets.join(', ') || 'None'}`, 'crit');
        }
      } catch (err) {
        showToast('Emergency shed failed', 'crit');
      }
    });
  }

  // 2. Restore all relays
  const btnRestore = document.getElementById('btnAdminRestore');
  if (btnRestore) {
    btnRestore.addEventListener('click', async () => {
      try {
        const res = await apiFetch('/api/emergency/restore', {
          method: 'POST',
          body: JSON.stringify({ station_id: GlobalState.stationId })
        });
        if (res && res.ok) {
          showToast(`All ${res.total_loads || 5} station loads restored to ONLINE`, 'success');
        }
      } catch (err) {
        showToast('Relay restore failed', 'crit');
      }
    });
  }

  // 3. Database Clean Reset
  const btnResetDb = document.getElementById('btnAdminResetDb');
  if (btnResetDb) {
    btnResetDb.addEventListener('click', async () => {
      if (!confirm('CAUTION: Restore database to pristine SIH 26061 factory seed state?')) {
        return;
      }
      try {
        const res = await apiFetch('/api/admin/reset-db', { method: 'POST' });
        if (res && res.ok) {
          showToast('Database wiped and re-seeded cleanly', 'success');
          setTimeout(() => window.location.reload(), 1000);
        }
      } catch (err) {
        showToast('Database reset failed', 'crit');
      }
    });
  }
}

/**
 * Load System Logs
 */
async function loadAuditLogs() {
  const tbody = document.getElementById('auditLogsTableBody');
  if (!tbody) return;

  try {
    const data = await apiFetch('/api/admin/logs?limit=15');
    if (!data || !data.logs) return;

    tbody.innerHTML = '';
    data.logs.forEach(log => {
      const tr = document.createElement('tr');
      const net = log.net_power_kw;
      const netClass = net >= 0 ? 'text-emerald' : 'text-crimson';

      tr.innerHTML = `
        <td style="font-family: var(--font-mono); color: var(--text-dim);">${log.timestamp || 'RECENT'}</td>
        <td>${log.station_id}</td>
        <td>${log.solar_kw.toFixed(1)} kW</td>
        <td>${log.wind_kw.toFixed(1)} kW</td>
        <td>${log.demand_kw.toFixed(1)} kW</td>
        <td>${log.battery_soc_pct.toFixed(0)}% (${log.battery_kwh.toFixed(1)} kWh)</td>
        <td class="${netClass}">${net >= 0 ? '+' : ''}${net.toFixed(1)} kW</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.warn("Failed to load audit logs:", err);
  }
}

// Auto-run on admin page
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('formHardwareConfig') || document.getElementById('btnAdminResetDb')) {
    initAdmin();
  }
});




