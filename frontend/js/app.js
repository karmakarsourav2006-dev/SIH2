/**
 * POLAR ENERGY AI - CORE APPLICATION & API BRIDGE
 * Global State, Network Client, Station Selector, Mission Clock & Toasts
 */

export const API_BASE = (window.location.port === '3000' || window.location.protocol === 'file:')
  ? 'http://127.0.0.1:8000'
  : window.location.origin;

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
  toast.innerHTML = `<strong>[POLAR-SYS]</strong> ${message}`;
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
          showToast(`Active base switched to: ${e.target.options[e.target.selectedIndex].text}`, 'info');
          notifySubscribers();
        });
      }
    }
  } catch (err) {
    console.warn("Could not load station list from backend:", err);
  }
}

// Auto-run on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  initAppShell();
});



