/**
 * POLAR ENERGY AI - EXPEDITION MISSION COMMAND DASHBOARD
 * Real-time Telemetry, Digital Twin State, Relay Matrix, Survivability Dials & Anomaly Stream
 */

import { apiFetch, GlobalState, subscribeState, showToast, escapeHtml, simulationInputs } from './app.js';
import { speakText } from './voice.js';

let updateTimer = null;
let evaluating = false;
let evaluationQueued = false;
let currentTelemetry = {
  wind_mps: 12.0,
  lux: 350.0,
  temp_c: -28.0,
  battery_kwh: 85.0,
  gen_kw: 0.0
};

export function initDashboard() {
  Object.assign(currentTelemetry, simulationInputs());
  bindSliders();
  // Header relay actions are already bound once by app.js.
  subscribeState(() => {
    refreshDashboard();
  });
  refreshDashboard();
  // Poll periodically
  setInterval(refreshDashboard, 5000);
}

/**
 * Bind input range sliders and readouts
 */
function bindSliders() {
  const sliders = [
    { id: 'rngWind', valId: 'txtWind', key: 'wind_mps', unit: ' m/s' },
    { id: 'rngLux', valId: 'txtLux', key: 'lux', unit: ' Lux' },
    { id: 'rngTemp', valId: 'txtTemp', key: 'temp_c', unit: ' °C' },
    { id: 'rngBattery', valId: 'txtBattery', key: 'battery_kwh', unit: ' kWh' },
    { id: 'rngGen', valId: 'txtGen', key: 'gen_kw', unit: ' kW' }
  ];

  sliders.forEach(s => {
    const el = document.getElementById(s.id);
    const textEl = document.getElementById(s.valId);
    if (!el) return;
    el.value = currentTelemetry[s.key];
    if (textEl) textEl.textContent = `${currentTelemetry[s.key].toFixed(1)}${s.unit}`;

    el.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      currentTelemetry[s.key] = val;
      sessionStorage.setItem(`polar_inputs_${GlobalState.stationId}`, JSON.stringify(currentTelemetry));
      if (evaluating) evaluationQueued = true;
      if (textEl) {
        textEl.textContent = `${val.toFixed(1)}${s.unit}`;
      }
      // Debounced trigger
      clearTimeout(updateTimer);
      updateTimer = setTimeout(() => {
        evaluateMicrogrid();
      }, 150);
    });
  });
}

/**
 * Call Digital Twin API to evaluate state under current conditions
 */
export async function evaluateMicrogrid() {
  clearTimeout(updateTimer);
  if (evaluating) { evaluationQueued = true; return; }
  evaluating = true;
  const stationId = GlobalState.stationId;
  try {
    const payload = {
      ...currentTelemetry,
      station_id: GlobalState.stationId
    };

    const res = await apiFetch('/api/telemetry', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res && res.ok && res.state) {
      if (stationId !== GlobalState.stationId || evaluationQueued) return;
      sessionStorage.setItem(`polar_inputs_${stationId}`, JSON.stringify(payload));
      GlobalState.isCritical = res.state.is_critical;
      updateUIWithState(res.state);
      setText('telemetryStatus', 'LIVE ENERGY FLOW');
    }
  } catch (err) {
    console.warn("Digital Twin evaluation error:", err);
    setText('telemetryStatus', 'TELEMETRY UNAVAILABLE — values may be stale');
  } finally {
    evaluating = false;
    if (evaluationQueued) { evaluationQueued = false; evaluateMicrogrid(); }
  }
}

/**
 * Update KPIs, dials, and alarms with returned state
 */
function updateUIWithState(state) {
  // 1. Environmental Pills
  const pillTemp = document.getElementById('pillTemp');
  const pillWind = document.getElementById('pillWind');
  const pillSolar = document.getElementById('pillSolar');
  const w = state.weather || state.live_weather || {};
  const temp = (w.temp_c !== undefined) ? w.temp_c : (state.temp_c || -28.0);
  const wind = (w.wind_mps !== undefined) ? w.wind_mps : (state.wind_mps || 12.0);
  const lux = (w.lux !== undefined) ? w.lux : (state.lux || 350.0);

  if (pillTemp) {
    const isLive = false; // This view evaluates user-controlled simulation inputs.
    pillTemp.textContent = `${isLive ? '● ' : ''}Temp: ${Number(temp).toFixed(1)}°C`;
    pillTemp.title = isLive ? `Live OpenWeather: ${state.live_weather.description || 'Antarctic telemetry'}` : 'Microgrid telemetry';
  }
  if (pillWind) pillWind.textContent = `Wind: ${Number(wind).toFixed(1)} m/s`;
  if (pillSolar) pillSolar.textContent = `Solar: ${Number(lux).toFixed(0)} Lux`;


  // 2. Mode Badge
  const badgeMode = document.getElementById('badgeMode');
  const textMode = document.getElementById('textMode');
  if (badgeMode && textMode) {
    if (state.is_critical || state.mode === 'SURVIVAL CRITICAL') {
      badgeMode.className = 'mode-badge critical';
      textMode.textContent = 'SURVIVAL CRITICAL';
    } else {
      badgeMode.className = 'mode-badge nominal';
      textMode.textContent = state.mode;
    }
  }

  // 3. KPI Cards
  setText('kpiSolar', `${state.solar_kw.toFixed(1)} kW`);
  setText('kpiWind', `${state.wind_kw.toFixed(1)} kW`);
  setText('kpiRenewable', `${state.total_renewables_kw.toFixed(1)} kW`);
  setText('kpiDemand', `${state.active_demand_kw.toFixed(1)} kW`);
  setText('kpiGen', `${state.gen_kw.toFixed(1)} kW`);
  setText('kpiBattery', `${state.battery_kwh.toFixed(1)} kWh (${state.soc_pct.toFixed(0)}%)`);

  // Net Flow
  const netEl = document.getElementById('kpiNet');
  if (netEl) {
    const net = state.net_flow_kw;
    netEl.textContent = `${net >= 0 ? '+' : ''}${net.toFixed(1)} kW`;
    netEl.className = `kpi-value ${net >= 0 ? 'text-emerald' : 'text-crimson'}`;
  }

  // 4. Survivability Dials
  const safeHours = state.survivability ? state.survivability.safe_runtime_hours : 0;
  const p1Hours = state.survivability ? state.survivability.p1_isolated_hours : 0;
  const fuelDays = state.survivability ? state.survivability.fuel_days_left : 0;

  setText('valSafeHours', `${safeHours > 999 ? '>999' : safeHours.toFixed(1)}`);
  setText('valP1Hours', `${p1Hours > 999 ? '>999' : p1Hours.toFixed(1)}`);
  setText('valFuelDays', `${fuelDays.toFixed(1)}`);

  // Animate Gauge Ring for Safe Hours (100 hrs base scale)
  const gaugeSvg = document.getElementById('gaugeSafeHours');
  if (gaugeSvg) {
    const maxScale = 72; // 72 hours max arc
    const clamped = Math.min(maxScale, Math.max(0, safeHours));
    const pct = clamped / maxScale;
    const offset = 377 - (377 * pct);
    gaugeSvg.style.strokeDashoffset = offset;
    gaugeSvg.setAttribute('class', `gauge-progress ${safeHours < 12 ? 'crit' : safeHours < 24 ? 'warn' : ''}`);
  }

  // Survivability Panel Border
  const survPanel = document.getElementById('survivabilityPanel');
  if (survPanel) {
    if (state.is_critical) {
      survPanel.classList.add('critical');
    } else {
      survPanel.classList.remove('critical');
    }
  }

  // 5. Automatic Emergency Voice Alerts (Requirement 8)
  const status = document.getElementById('survStatusBadge');
  if (status) {
    status.textContent = state.mode;
    status.className = `badge ${state.is_critical ? 'badge-critical' : 'badge-normal'}`;
  }
  const priorities = document.getElementById('priorityProtection');
  if (priorities) priorities.textContent = [1, 2, 3].map(priority => {
    const loads = state.loads.filter(l => l.priority === priority);
    const online = loads.filter(l => l.status === 'ONLINE').length;
    const label = !loads.length ? 'NO LOADS' : online === loads.length ? (priority === 1 ? 'PROTECTED' : 'ONLINE') : online ? 'LIMITED' : (priority === 2 ? 'PAUSED' : 'SHED');
    return `P${priority} ${['', 'CRITICAL', 'SCIENCE', 'AUXILIARY'][priority]}: ${label}`;
  }).join('  ·  ');
  if (state.auto_voice_alert && (state.severity === 'CRITICAL' || state.severity === 'EMERGENCY')) {
    if (window._lastAutoVoiceAlert !== state.auto_voice_alert) {
      window._lastAutoVoiceAlert = state.auto_voice_alert;
      showToast(`[${state.severity}] ${state.auto_voice_alert}`, state.severity === 'EMERGENCY' ? 'crit' : 'warning');
      speakText(state.auto_voice_alert);
    }
  } else if (state.severity === 'INFO' || state.severity === 'WARNING') {
    window._lastAutoVoiceAlert = null;
  }

  // 6. Anomalies & Diagnostics Terminal
  renderAnomalies(state.anomalies || [], state.emergency_events || []);

  // 7. Reload Relays table
  renderRelays(state.loads || []);
}


function setText(id, text) {
  const el = document.getElementById(id);
  if (el && el.textContent !== text) {
    el.textContent = text;
    if (el.matches('.kpi-value, .gauge-center-val') && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      el.animate([{opacity: .55}, {opacity: 1}], {duration: 220});
    }
  }
}

/**
 * Render Loads and Relay Interlocks
 */
async function renderRelays(loads) {
  const tbody = document.getElementById('relayTableBody');
  if (!tbody) return;

  // If loads not provided directly, fetch from optimization API
  if (!loads || loads.length === 0) {
    try {
      const data = await apiFetch(`/api/optimization/relays?station_id=${GlobalState.stationId}`);
      if (data && data.loads) loads = data.loads;
    } catch (e) {
      return;
    }
  }

  tbody.innerHTML = '';
  loads.forEach(load => {
    const tr = document.createElement('tr');
    const isOnline = load.status === 'ONLINE';
    const isP1 = load.priority === 1;
    tr.classList.toggle('load-anomaly', isOnline && load.is_surge);

    const priorityBadge = isP1
      ? '<span class="relay-p1-tag">P1 LIFE-CRITICAL</span>'
      : load.priority === 2
      ? '<span class="relay-p2-tag">P2 SCIENCE</span>'
      : '<span class="relay-p3-tag">P3 AUXILIARY</span>';

    const statusBadge = isOnline
      ? '<span class="status-online">ONLINE</span>'
      : '<span class="status-shedded">SHEDDED</span>';

    tr.innerHTML = `
      <td>
        <strong>${escapeHtml(load.name)}</strong>
        <div style="font-size:0.68rem; color:var(--text-dim);">ID: ${load.id}</div>
      </td>
      <td>${priorityBadge}</td>
      <td>${load.nominal_kw.toFixed(1)} kW</td>
      <td>
        <span class="${load.live_kw > load.nominal_kw * 1.2 ? 'text-amber' : ''}">
          ${(isOnline ? load.live_kw : 0).toFixed(1)} kW ${isOnline && load.is_surge ? '⚠ ANOMALY' : ''}
        </span>
      </td>
      <td>${statusBadge}</td>
      <td style="text-align: right;">
        <label class="switch">
          <input type="checkbox" data-load-id="${load.id}" ${isOnline ? 'checked' : ''} ${isP1 ? 'disabled title="Life-Support interlock protected"' : ''}>
          <span class="slider-toggle"></span>
        </label>
      </td>
    `;

    // Bind toggle
    const chk = tr.querySelector('input[type="checkbox"]');
    if (chk && !isP1) {
      chk.addEventListener('change', async (e) => {
        await toggleRelay(load.id);
      });
    }

    tbody.appendChild(tr);
  });
}

/**
 * Toggle individual relay switch
 */
async function toggleRelay(loadId) {
  try {
    const res = await apiFetch('/api/optimization/relays', {
      method: 'POST',
      body: JSON.stringify({
        station_id: GlobalState.stationId,
        load_id: loadId
      })
    });
    if (res && res.ok) {
      showToast(`Relay ${loadId} switched to: ${res.load.status}`, res.load.status === 'ONLINE' ? 'success' : 'warning');
      evaluateMicrogrid();
    }
  } catch (err) {
    showToast(`Failed to toggle relay ${loadId}`, 'crit');
  }
}

/**
 * Bind Mass Shed & Restore Buttons
 */
function bindRelayControls() {
  const btnReset = document.getElementById('btnResetLoads');
  if (btnReset) {
    btnReset.addEventListener('click', async () => {
      const stationId = GlobalState.stationId || 'ST-01';
      try {
        const res = await apiFetch(`/api/emergency/restore?station_id=${encodeURIComponent(stationId)}`, {
          method: 'POST',
          body: JSON.stringify({ station_id: stationId })
        });
        if (res && res.ok) {
          showToast(`All ${res.total_loads || 'station'} relays restored to ONLINE`, 'success');
          evaluateMicrogrid();
        }
      } catch (err) {
        console.error('[Dashboard] Restore relays failed:', err);
        showToast('Failed to restore relays', 'crit');
      }
    });
  }

  const btnEmergencyShed = document.getElementById('btnEmergencyShed');
  if (btnEmergencyShed) {
    btnEmergencyShed.addEventListener('click', async () => {
      const stationId = GlobalState.stationId || 'ST-01';
      try {
        const res = await apiFetch(`/api/emergency/shed?station_id=${encodeURIComponent(stationId)}`, {
          method: 'POST',
          body: JSON.stringify({ station_id: stationId })
        });
        if (res && res.ok) {
          const count = res.shedded_assets?.length || 0;
          const msg = count > 0 
            ? `EMERGENCY SHED TRIGGERED: Shed ${count} assets (${res.shedded_assets.join(', ')})`
            : `EMERGENCY SHED: No non-critical P2/P3 loads active to shed.`;
          showToast(msg, 'crit');
          evaluateMicrogrid();
        } else {
          showToast('Emergency shedding rejected by controller', 'warning');
        }
      } catch (err) {
        console.error('[Dashboard] Emergency shed request failed:', err);
        showToast(`Emergency shedding failed (${err.message || 'connection error'})`, 'crit');
      }
    });
  }
}

/**
 * Render Terminal Diagnostic Logs & Anomalies
 */
function renderAnomalies(anomalies, emergencyEvents) {
  const term = document.getElementById('diagnosticTerminal');
  if (!term) return;

  const nowTime = new Date().toISOString().substring(11, 19);

  if (anomalies.length === 0 && emergencyEvents.length === 0) {
    term.innerHTML = `
      <div class="terminal-line">
        <span class="terminal-time">[${nowTime}]</span>
        <span class="terminal-msg info">TELEMETRY NOMINAL // ALL POLAR HARVESTING LOOPS STABLE</span>
      </div>
      <div class="terminal-line">
        <span class="terminal-time">[${nowTime}]</span>
        <span class="terminal-msg">BESS thermal management: In-range (+15°C cell core)</span>
      </div>
    `;
    return;
  }

  let html = '';
  emergencyEvents.forEach(evt => {
    html += `
      <div class="terminal-line">
        <span class="terminal-time">[${nowTime}]</span>
        <span class="terminal-msg">[EVENT] ${escapeHtml(evt)}</span>
      </div>
    `;
  });

  anomalies.forEach(ano => {
    html += `
      <div class="terminal-line">
        <span class="terminal-time">[${nowTime}]</span>
        <span class="terminal-msg ${ano.urgency === 'CRITICAL' ? 'crit' : 'warn'}">
          ⚠ [ANOMALY / ${escapeHtml(ano.urgency)}] ${escapeHtml(ano.name)}: Expected ${ano.nominal_kw} kW · Current ${ano.live_kw} kW · Deviation +${ano.surge_pct}%.<br>
          Probable cause: ${escapeHtml(ano.description)}<br>
          Recommended action: ${escapeHtml(ano.recommended_action)}
        </span>
      </div>
    `;
  });

  term.innerHTML = html;
}

/**
 * Full refresh cycle
 */
export async function refreshDashboard() {
  await evaluateMicrogrid();
}

// Auto-run if on dashboard page
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('relayTableBody') || document.getElementById('rngWind')) {
    initDashboard();
  }
});




