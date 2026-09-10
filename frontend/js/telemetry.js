/**
 * BOREAS AI Microgrid - Telemetry & Relays Engine
 */

const API_BASE = (window.location.port === '3000') ? 'http://127.0.0.1:8000' : window.location.origin;

let isTelemetryPending = false;
let currentTelemetryData = null;

// DOM Selectors
const el = {
  // Mode & Clock
  badgeMode: document.getElementById('badgeMode'),
  textMode: document.getElementById('textMode'),
  liveClock: document.getElementById('liveClock'),
  btnResetLoads: document.getElementById('btnResetLoads'),

  // Environment Pills
  pillTemp: document.getElementById('pillTemp'),
  pillWind: document.getElementById('pillWind'),
  pillSolar: document.getElementById('pillSolar'),

  // Sliders & Readouts
  rngWind: document.getElementById('rngWind'),
  rngLux: document.getElementById('rngLux'),
  rngTemp: document.getElementById('rngTemp'),
  rngBattery: document.getElementById('rngBattery'),
  rngGen: document.getElementById('rngGen'),
  txtWind: document.getElementById('txtWind'),
  txtLux: document.getElementById('txtLux'),
  txtTemp: document.getElementById('txtTemp'),
  txtBattery: document.getElementById('txtBattery'),
  txtGen: document.getElementById('txtGen'),

  // Metric Displays
  netFlowVal: document.getElementById('netFlowVal'),
  netFlowSub: document.getElementById('netFlowSub'),
  totalGenVal: document.getElementById('totalGenVal'),
  totalGenSub: document.getElementById('totalGenSub'),
  activeDemandVal: document.getElementById('activeDemandVal'),
  activeDemandSub: document.getElementById('activeDemandSub'),
  socVal: document.getElementById('socVal'),
  socBar: document.getElementById('socBar'),
  socSub: document.getElementById('socSub'),

  // Survivability
  stationSurvHrs: document.getElementById('stationSurvHrs'),
  stationSurvDesc: document.getElementById('stationSurvDesc'),
  p1SurvHrs: document.getElementById('p1SurvHrs'),

  // Tables & Feed
  relayTableBody: document.getElementById('relayTableBody'),
  diagnosticsFeed: document.getElementById('diagnosticsFeed')
};

export function initTelemetry() {
  // Bind slider events with immediate readout on input
  bindSlider(el.rngWind, el.txtWind, v => `${parseFloat(v).toFixed(1)} m/s`);
  bindSlider(el.rngLux, el.txtLux, v => `${v} Lux`);
  bindSlider(el.rngTemp, el.txtTemp, v => `${parseFloat(v).toFixed(1)} °C`);
  bindSlider(el.rngBattery, el.txtBattery, v => `${parseFloat(v).toFixed(0)} kWh`);
  bindSlider(el.rngGen, el.txtGen, v => `${parseFloat(v).toFixed(1)} kW`);

  // Global Reset button
  if (el.btnResetLoads) {
    el.btnResetLoads.addEventListener('click', async () => {
      try {
        await fetch(`${API_BASE}/api/loads/reset`, { method: 'POST' });
        triggerTelemetryUpdate();
      } catch (err) {
        console.error('Failed to reset loads:', err);
      }
    });
  }

  // Initial fetch
  triggerTelemetryUpdate();
}

function bindSlider(slider, readout, formatter) {
  if (!slider || !readout) return;
  slider.addEventListener('input', () => {
    readout.textContent = formatter(slider.value);
    triggerTelemetryUpdate();
  });
}

export async function triggerTelemetryUpdate() {
  if (isTelemetryPending) return;
  isTelemetryPending = true;

  const payload = {
    wind_mps: parseFloat(el.rngWind.value),
    lux: parseFloat(el.rngLux.value),
    temp_c: parseFloat(el.rngTemp.value),
    battery_kwh: parseFloat(el.rngBattery.value),
    gen_kw: parseFloat(el.rngGen.value)
  };

  try {
    const res = await fetch(`${API_BASE}/api/telemetry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    currentTelemetryData = data;
    renderTelemetry(data);
    
    // Notify custom event for scheduler / assistant integration
    window.dispatchEvent(new CustomEvent('polar:telemetryUpdated', { detail: data }));
  } catch (err) {
    console.error('Telemetry update error:', err);
  } finally {
    isTelemetryPending = false;
  }
}

function renderTelemetry(d) {
  // 1. Station Mode Badge
  if (d.is_critical) {
    el.badgeMode.className = 'mode-badge critical';
    el.textMode.textContent = 'SURVIVAL CRITICAL';
  } else {
    el.badgeMode.className = 'mode-badge nominal';
    el.textMode.textContent = 'NORMAL OPTIMIZATION';
  }

  // 2. Environmental Pills
  if (el.pillTemp) el.pillTemp.textContent = `Temp: ${d.environment.temp_c.toFixed(1)}°C`;
  if (el.pillWind) el.pillWind.textContent = `Wind: ${d.environment.wind_mps.toFixed(1)} m/s`;
  if (el.pillSolar) el.pillSolar.textContent = `Solar: ${d.environment.lux.toFixed(0)} Lux`;

  // 3. Power Balances
  const net = d.power.net_flow_kw;
  el.netFlowVal.textContent = `${net >= 0 ? '+' : ''}${net.toFixed(2)} kW`;
  if (net > 0) {
    el.netFlowVal.className = 'metric-number positive-flow';
    el.netFlowSub.textContent = 'Surplus: Charging Battery Bank';
  } else if (net < 0) {
    el.netFlowVal.className = 'metric-number negative-flow';
    el.netFlowSub.textContent = 'Deficit: Discharging Battery Bank';
  } else {
    el.netFlowVal.className = 'metric-number';
    el.netFlowSub.textContent = 'Equilibrium: Balanced Bus';
  }

  el.totalGenVal.textContent = `${d.power.total_generation_kw.toFixed(2)} kW`;
  el.totalGenSub.textContent = `Solar: ${d.power.solar_kw.toFixed(1)} kW | Wind: ${d.power.wind_kw.toFixed(1)} kW | Gen: ${d.power.generator_kw.toFixed(1)} kW`;

  el.activeDemandVal.textContent = `${d.power.active_demand_kw.toFixed(2)} kW`;
  const activeCount = d.loads.filter(l => l.status === 'ONLINE').length;
  el.activeDemandSub.textContent = `${activeCount} of ${d.loads.length} loads online (Thermal baseline: ${d.power.thermal_heating_baseline_kw.toFixed(1)} kW)`;

  // 4. Battery SoC
  el.socVal.textContent = `${d.environment.soc_pct.toFixed(1)}%`;
  el.socBar.style.width = `${d.environment.soc_pct}%`;
  if (d.environment.soc_pct < 25) {
    el.socBar.style.backgroundColor = 'var(--terracotta)';
  } else if (d.environment.soc_pct < 50) {
    el.socBar.style.backgroundColor = 'var(--ochre-amber)';
  } else {
    el.socBar.style.backgroundColor = 'var(--pine-green)';
  }
  el.socSub.textContent = `${d.environment.battery_kwh.toFixed(1)} / ${d.environment.battery_capacity_kwh.toFixed(0)} kWh Available`;

  // 5. Survivability Runways
  el.stationSurvHrs.textContent = `${d.survivability.station_survival_hrs.toFixed(1)} Hrs`;
  el.p1SurvHrs.textContent = `${d.survivability.p1_isolated_hrs.toFixed(1)} Hrs`;

  // 6. Relays Table
  renderRelayTable(d.loads);

  // 7. Diagnostics Feed
  renderDiagnostics(d);
}

function renderRelayTable(loads) {
  if (!el.relayTableBody) return;
  el.relayTableBody.innerHTML = '';

  loads.forEach(load => {
    const tr = document.createElement('tr');
    
    // Priority Pill
    let pClass = 'p3';
    let pText = 'P3 Aux';
    if (load.priority === 1) { pClass = 'p1'; pText = 'P1 Core'; }
    else if (load.priority === 2) { pClass = 'p2'; pText = 'P2 Science'; }

    // Status Badge
    const isOnline = String(load.status).toUpperCase() === 'ONLINE';
    const sClass = isOnline ? 'online' : 'shedded';

    // Live Draw with surge alert
    let liveMarkup = `<span style="font-family:var(--font-mono); font-weight:600;">${load.live_kw.toFixed(1)} kW</span>`;
    if (load.is_surge) {
      liveMarkup = `
        <span class="surge-alert-inline" style="font-family:var(--font-mono);" title="Surge Anomaly: +${load.excess_kw} kW (+${load.surge_pct}%)">
          ${load.live_kw.toFixed(1)} kW ⚠
        </span>
      `;
    }

    // Toggle Button
    const btnClass = isOnline ? 'btn-polar btn-shed' : 'btn-polar btn-restore';
    const btnLabel = isOnline ? 'Shed' : 'Restore';

    tr.innerHTML = `
      <td>
        <div class="asset-cell">
          <span>${load.name}</span>
          ${load.priority === 1 ? '<span title="Ring-Fenced Core Life-Critical" style="color:var(--pine-green); font-size:0.75rem;">🔒</span>' : ''}
        </div>
      </td>
      <td><span class="priority-pill ${pClass}">${pText}</span></td>
      <td><span style="font-family:var(--font-mono); color:var(--text-muted);">${load.nominal_kw.toFixed(1)} kW</span></td>
      <td>${liveMarkup}</td>
      <td><span class="status-badge-inline ${sClass}">● ${load.status}</span></td>
      <td style="text-align:right;">
        <button class="${btnClass}" data-id="${load.id}">${btnLabel}</button>
      </td>
    `;

    const btn = tr.querySelector('button');
    btn.addEventListener('click', async () => {
      await toggleLoad(load.id);
    });

    el.relayTableBody.appendChild(tr);
  });
}

async function toggleLoad(id) {
  try {
    await fetch(`${API_BASE}/api/loads/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    });
    triggerTelemetryUpdate();
  } catch (err) {
    console.error('Failed to toggle load:', err);
  }
}

function renderDiagnostics(d) {
  if (!el.diagnosticsFeed) return;
  const time = new Date().toTimeString().split(' ')[0];
  let html = '';

  // Emergency Events
  if (d.emergency_events && d.emergency_events.length > 0) {
    d.emergency_events.forEach(evt => {
      html += `
        <div class="diag-entry emergency">
          <span class="diag-time">[${time}]</span> [SURVIVAL EMERGENCY] ${evt}
        </div>
      `;
    });
  }

  // Anomalies
  if (d.anomalies && d.anomalies.length > 0) {
    d.anomalies.forEach(ano => {
      html += `
        <div class="diag-entry surge">
          <span class="diag-time">[${time}]</span> [SURGE DETECTED] <strong>${ano.name}</strong>: Drawing ${ano.live_kw} kW (+${ano.excess_kw} kW / +${ano.surge_pct}%). Wasting ~${ano.wasted_kwh_per_hr} kWh/hr.<br>
          <span style="font-size:0.72rem; color:var(--text-muted); margin-top:2px; display:block;">Cause: ${ano.probable_cause}</span>
        </div>
      `;
    });
  } else {
    html += `
      <div class="diag-entry nominal">
        <span class="diag-time">[${time}]</span> [AI AUDIT] Power signatures across all active relays are within nominal calibrated tolerance (≤ 125%).
      </div>
    `;
  }

  // Bus Overview
  html += `
    <div class="diag-entry">
      <span class="diag-time">[${time}]</span> [GRID BUS] Renewables: ${d.power.total_renewables_kw.toFixed(2)} kW | Demand: ${d.power.active_demand_kw.toFixed(2)} kW | Net Delta: ${d.power.net_flow_kw.toFixed(2)} kW | P1 Runway: ${d.survivability.p1_isolated_hrs.toFixed(1)}h
    </div>
  `;

  el.diagnosticsFeed.innerHTML = html;
}

export function getCurrentTelemetry() {
  return currentTelemetryData;
}




