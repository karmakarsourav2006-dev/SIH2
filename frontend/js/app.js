/**
 * POLAR ENERGY AI - CORE APPLICATION & API BRIDGE
 * Global State, Network Client, Station Selector, Mission Clock & Toasts
 */

export const API_BASE = (window.location.port !== '8000' || window.location.protocol === 'file:')
  ? 'http://127.0.0.1:8000'
  : '';


// Global State
export const GlobalState = {
  stationId: localStorage.getItem('polar_station_id') || 'ST-01',
  stations: [],
  currentWeather: null,
  isCritical: false,
  subscribers: []
};

export function subscribeState(callback) {
  GlobalState.subscribers.push(callback);
}

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
}

export function simulationInputs() {
  try { return JSON.parse(sessionStorage.getItem(`polar_inputs_${GlobalState.stationId}`)) || {}; }
  catch { return {}; }
}

function notifySubscribers() {
  GlobalState.subscribers.forEach(cb => {
    try { cb(GlobalState); } catch(e) { console.error("Subscriber error:", e); }
  });
}

/**
 * Universal API fetch bridge with error handling and fallback
 */
export async function apiFetch(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      },
      ...options
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`HTTP ${res.status}: ${errText}`);
    }
    return await res.json();
  } catch (err) {
    console.warn(`[API Bridge] Fetch failed for ${url}:`, err.message);
    throw err;
  }
}

/**
 * Toast Notification System
 */
export function showToast(message, type = 'info') {
  let toastContainer = document.getElementById('toastContainer');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toastContainer';
    toastContainer.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 10px;
      pointer-events: none;
    `;
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement('div');
  const borderColors = {
    info: 'var(--glacier, #38bdf8)',
    success: 'var(--emerald, #10b981)',
    warning: 'var(--amber, #f59e0b)',
    crit: 'var(--crimson, #ef4444)'
  };
  const bgColors = {
    info: 'rgba(15, 23, 42, 0.95)',
    success: 'rgba(6, 78, 59, 0.95)',
    warning: 'rgba(120, 53, 15, 0.95)',
    crit: 'rgba(127, 29, 29, 0.95)'
  };

  toast.style.cssText = `
    background: ${bgColors[type] || bgColors.info};
    border-left: 4px solid ${borderColors[type] || borderColors.info};
    color: #f8fafc;
    padding: 12px 18px;
    border-radius: 4px;
    font-family: var(--font-mono, monospace);
    font-size: 0.78rem;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.5);
    max-width: 380px;
    pointer-events: auto;
    animation: toast-in 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  `;
  toast.textContent = `[POLAR-SYS] ${message}`;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

/**
 * Initialize Navigation & Mission Clock
 */
export function initAppShell() {
  // 1. Mission Clock
  const clockEl = document.getElementById('liveClock');
  if (clockEl) {
    function tick() {
      const now = new Date();
      const utcStr = now.toISOString().substring(11, 19);
      clockEl.textContent = `UTC ${utcStr} // POLAR`;
    }
    tick();
    setInterval(tick, 1000);
  }

  // 2. Active navigation link indicator
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.nav-link');
  navLinks.forEach(link => {
    const href = link.getAttribute('href');
    if (href && (currentPath.endsWith(href) || (currentPath === '/' && href === 'index.html'))) {
      link.classList.add('active');
    }
  });

  // 3. Populate and bind global station selector
  initStationSelector();

  // 4. Bind Global Header Controls (Emergency Shed, Restore, Environmental Telemetry Pills)
  initHeaderControls();
}

/**
 * Global Header Controls (Emergency Shed, Restore, and live telemetry updates)
 */
function initHeaderControls() {
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
          updateGlobalTelemetryPills();
          notifySubscribers();
        }
      } catch (err) {
        console.error('[Header] Restore relays failed:', err);
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
          updateGlobalTelemetryPills();
          notifySubscribers();
        } else {
          showToast('Emergency shedding rejected by controller', 'warning');
        }
      } catch (err) {
        console.error('[Header] Emergency shed request failed:', err);
        showToast(`Emergency shedding failed (${err.message || 'connection error'})`, 'crit');
      }
    });
  }

  // Initial and periodic header telemetry update
  updateGlobalTelemetryPills();
  setInterval(updateGlobalTelemetryPills, 5000);
}

/**
 * Fetch telemetry and update global header pills and mode badge
 */
export async function updateGlobalTelemetryPills() {
  // The dashboard owns its sliders and polling; a second default request races it.
  if (document.getElementById('rngWind')) return;
  const pillTemp = document.getElementById('pillTemp');
  const pillWind = document.getElementById('pillWind');
  const pillSolar = document.getElementById('pillSolar');
  const badgeMode = document.getElementById('badgeMode');
  const textMode = document.getElementById('textMode');

  // If none of these exist on the current page, skip
  if (!pillTemp && !pillWind && !pillSolar && !badgeMode) return;

  try {
    const stationId = GlobalState.stationId || 'ST-01';
    const res = await apiFetch('/api/telemetry', {
      method: 'POST',
      body: JSON.stringify({
        station_id: stationId,
        wind_mps: 12.0,
        lux: 350.0,
        temp_c: -28.0,
        battery_kwh: 85.0,
        gen_kw: 0.0,
        ...simulationInputs()
      })
    });

    if (res && res.ok && res.state) {
      if (stationId !== GlobalState.stationId) return;
      const s = res.state;
      const overview = document.querySelector('.overview-page');
      if (overview) {
        const values = {kpiBattery: `${s.battery_kwh.toFixed(1)} kWh / ${s.soc_pct.toFixed(0)}%`, kpiRenewable: `${s.total_renewables_kw.toFixed(1)} kW`, kpiDemand: `${s.active_demand_kw.toFixed(1)} kW`, valSafeHours: `${s.survivability.safe_runtime_hours.toFixed(1)} hrs`, overviewStationName: s.station.name};
        Object.entries(values).forEach(([id, value]) => { const node = document.getElementById(id); if (node) node.textContent = value; });
      }
      if (pillTemp && s.temp_c !== undefined) pillTemp.textContent = `Temp: ${s.temp_c.toFixed(1)}°C`;
      if (pillWind && s.wind_mps !== undefined) pillWind.textContent = `Wind: ${s.wind_mps.toFixed(1)} m/s`;
      if (pillSolar && s.lux !== undefined) pillSolar.textContent = `Solar: ${s.lux.toFixed(0)} Lux`;

      if (badgeMode && textMode) {
        if (s.is_critical || s.mode === 'SURVIVAL CRITICAL') {
          badgeMode.className = 'badge badge-critical';
          textMode.textContent = 'SURVIVAL CRITICAL';
        } else {
          badgeMode.className = 'badge badge-normal';
          textMode.textContent = s.mode === 'GREEN OPTIMIZATION' ? 'GREEN OPTIMIZATION' : 'OPTIMAL DISPATCH';
        }
      }
    }
  } catch (e) {
    // Graceful fallback for background network jitter
  }
}

/**
 * Station selector setup
 */
async function initStationSelector() {
  const selectEl = document.getElementById('globalStationSelect');
  try {
    const data = await apiFetch('/api/stations');
    if (data && data.stations) {
      GlobalState.stations = data.stations;
      renderStationDiscovery();
      if (selectEl) {
        selectEl.innerHTML = '';
        data.stations.forEach(st => {
          const opt = document.createElement('option');
          opt.value = st.id;
          opt.textContent = `${st.id}: ${st.name}`;
          if (st.id === GlobalState.stationId) {
            opt.selected = true;
          }
          selectEl.appendChild(opt);
        });

        selectEl.addEventListener('change', (e) => {
          GlobalState.stationId = e.target.value;
          localStorage.setItem('polar_station_id', GlobalState.stationId);
          renderStationDiscovery();
          showToast(`Active base switched to: ${e.target.options[e.target.selectedIndex].text}`, 'info');
          updateGlobalTelemetryPills();
          notifySubscribers();
        });
      }
    }
  } catch (err) {
    console.warn("Could not load station list from backend:", err);
    const grid = document.getElementById('stationDiscovery');
    if (grid) grid.textContent = 'Station network unavailable. Refresh to reconnect.';
  }
}

function renderStationDiscovery() {
  const grid = document.getElementById('stationDiscovery');
  if (!grid) return;
  grid.innerHTML = GlobalState.stations.map(st => `<a class="station-card" href="dashboard.html" data-station="${escapeHtml(st.id)}"><div class="station-heading"><span class="station-id">${escapeHtml(st.id)}</span><span class="station-state">${st.id === GlobalState.stationId ? 'Selected station' : escapeHtml(st.status)}</span></div><h3>${escapeHtml(st.name)}</h3><p class="station-location">${escapeHtml(st.coordinates)}</p><div class="station-capacity"><strong>${escapeHtml(st.battery_capacity_kwh)}</strong><span>kWh battery capacity</span></div><div class="card-reveal">Generator backup: ${escapeHtml(st.generator_rating_kw)} kW<span>Open command deck &#8599;</span></div></a>`).join('');
  grid.querySelectorAll('[data-station]').forEach(card => card.addEventListener('click', () => {
    localStorage.setItem('polar_station_id', card.dataset.station);
  }));
}

function initOverviewExperience() {
  if (!document.querySelector('.overview-page')) return;
  document.querySelector('[data-open-advisor]')?.addEventListener('click', event => {
    event.preventDefault();
    if (!document.getElementById('voiceModal')?.classList.contains('open')) document.getElementById('btnVoiceFab')?.click();
  });
  try { if (sessionStorage.getItem('polar_intro_seen')) return; sessionStorage.setItem('polar_intro_seen', 'true'); } catch { /* Storage restrictions must not block access. */ }
  const intro = document.createElement('dialog');
  intro.className = 'polar-intro';
  intro.setAttribute('aria-labelledby', 'introIdentity');
  intro.innerHTML = `<button class="intro-skip btn" type="button" autofocus>Skip intro &#8599;</button><div class="intro-composition"><svg class="intro-globe" viewBox="0 0 400 400" role="img" aria-label="Stylized Earth with an Antarctic research focus"><defs><clipPath id="polarGlobeClip"><circle cx="200" cy="200" r="114"/></clipPath></defs><g class="globe-orbits" fill="none" stroke="currentColor"><ellipse cx="200" cy="200" rx="168" ry="53" transform="rotate(-25 200 200)"/><circle cx="200" cy="200" r="145" stroke-dasharray="2 12"/></g><circle class="globe-sphere" cx="200" cy="200" r="114"/><g clip-path="url(#polarGlobeClip)" fill="none" stroke="currentColor" opacity=".35"><ellipse cx="200" cy="200" rx="54" ry="114"/><ellipse cx="200" cy="200" rx="94" ry="114"/><ellipse cx="200" cy="200" rx="114" ry="45"/><path d="M86 200h228M100 145h200M100 255h200M200 86v228"/></g><g class="globe-land" clip-path="url(#polarGlobeClip)"><path d="m127 110 24 8 8 22-16 14-1 24 23 15 10 25-12 16 10 26-12 22-10-36-17-18-5-29-21-14-17-37Zm95-11 42 18 27 28-23 9-10-14-21 9 8 25-16 10-10 41-18 13-17-31 5-35-15-11 8-25 29-6Zm28 129 24 4 17 26-21 12-20-16Z"/><path class="antarctic-focus" d="m112 283 24-9 24 7 20-6 22 9 21-7 21 9 23-5 25 13-23 19H136Z"/></g><circle class="polar-marker" cx="201" cy="291" r="5"/><path class="polar-pointer" d="M207 291h91l23-23" fill="none" stroke="currentColor"/></svg><div class="intro-identity"><p class="eyebrow">A mission at the edge of the world</p><h2 id="introIdentity">Polar Energy AI</h2><p>AI-Driven Smart Energy Management<br>for Polar Research Stations</p><small>Predict &middot; Optimize &middot; Protect &middot; Sustain</small></div></div>`;
  document.body.appendChild(intro);
  intro.showModal();
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let timer;
  const finish = () => { clearTimeout(timer); intro.close(); intro.remove(); };
  intro.querySelector('button').addEventListener('click', finish, {once: true});
  intro.addEventListener('cancel', event => { event.preventDefault(); finish(); }, {once: true});
  window.addEventListener('pagehide', finish, {once: true});
  timer = setTimeout(finish, reduced ? 1000 : 3700);
}

// Auto-run on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  initOverviewExperience();
  initAppShell();
});

window.addEventListener('pageshow', event => {
  if (!event.persisted) return;
  const stationId = localStorage.getItem('polar_station_id') || 'ST-01';
  if (stationId !== GlobalState.stationId) {
    GlobalState.stationId = stationId;
    const select = document.getElementById('globalStationSelect');
    if (select) select.value = stationId;
    renderStationDiscovery();
    updateGlobalTelemetryPills();
    notifySubscribers();
  }
});



