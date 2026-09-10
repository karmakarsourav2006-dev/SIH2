/**
 * POLAR ENERGY AI - WHAT-IF STRESS SIMULATION ENGINE
 * Polar Blizzard, Generator Trip, Midnight Sun & Winter Night Scenario Runner
 */

import { apiFetch, showToast } from './app.js';
import { evaluateMicrogrid } from './dashboard.js';

export function initSimulation() {
  bindScenarioButtons();
}

/**
 * Bind scenario cards / buttons
 */
function bindScenarioButtons() {
  const buttons = document.querySelectorAll('[data-scenario]');
  buttons.forEach(btn => {
    btn.addEventListener('click', async () => {
      const scenarioKey = btn.getAttribute('data-scenario');
      await runScenario(scenarioKey);
    });
  });
}

/**
 * Execute scenario against backend engine and sync sliders
 */
export async function runScenario(scenarioKey) {
  try {
    const res = await apiFetch(`/api/simulation/scenario/${scenarioKey}?battery_kwh=65.0`, {
      method: 'POST'
    });

    if (res && res.ok && res.simulation) {
      const sim = res.simulation;
      const weather = sim.scenario_applied;

      // Update Dashboard range sliders if on dashboard
      setSliderVal('rngWind', 'txtWind', weather.wind_mps, ' m/s');
      setSliderVal('rngLux', 'txtLux', weather.lux, ' Lux');
      setSliderVal('rngTemp', 'txtTemp', weather.temp_c, ' °C');
      if (weather.gen_kw !== undefined) {
        setSliderVal('rngGen', 'txtGen', weather.gen_kw, ' kW');
      }

      showToast(`SIMULATION ACTIVE: ${sim.scenario_name}`, sim.state.is_critical ? 'crit' : 'info');

      // Re-evaluate Digital Twin
      if (typeof evaluateMicrogrid === 'function') {
        evaluateMicrogrid();
      }
    }
  } catch (err) {
    showToast(`Simulation scenario "${scenarioKey}" failed`, 'crit');
  }
}

function setSliderVal(sliderId, textId, value, unit) {
  const el = document.getElementById(sliderId);
  const textEl = document.getElementById(textId);
  if (el) {
    el.value = value;
    // Dispatch input event to sync internal telemetry state
    el.dispatchEvent(new Event('input'));
  }
  if (textEl) {
    textEl.textContent = `${value.toFixed(1)}${unit}`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initSimulation();
});

