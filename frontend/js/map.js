/**
 * POLAR ENERGY AI - INTERACTIVE STATION SCHEMATIC & DIGITAL TWIN MAP
 * Vector SVG Station Layout, Power Flow Animation & Asset Telemetry Inspection
 */

import { apiFetch, GlobalState, showToast } from './app.js';

export function initStationMap() {
  const container = document.getElementById('stationSchematicContainer');
  if (!container) return;

  renderSchematic(container);
  bindMapInteractions();
}

/**
 * Render the vector SVG polar base schematic
 */
function renderSchematic(container) {
  const svgMarkup = `
    <svg class="schematic-svg" viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="hubGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="var(--glacier)" stop-opacity="0.3"/>
          <stop offset="100%" stop-color="var(--glacier)" stop-opacity="0"/>
        </radialGradient>
        <radialGradient id="bessGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="var(--emerald)" stop-opacity="0.3"/>
          <stop offset="100%" stop-color="var(--emerald)" stop-opacity="0"/>
        </radialGradient>
      </defs>

      <!-- Background Polar Grid Lines -->
      <line x1="50" y1="50" x2="750" y2="50" stroke="var(--chart-grid)" stroke-width="1" stroke-dasharray="4 4"/>
      <line x1="50" y1="200" x2="750" y2="200" stroke="var(--chart-grid)" stroke-width="1" stroke-dasharray="4 4"/>
      <line x1="50" y1="350" x2="750" y2="350" stroke="var(--chart-grid)" stroke-width="1" stroke-dasharray="4 4"/>
      <line x1="200" y1="30" x2="200" y2="370" stroke="var(--chart-grid)" stroke-width="1" stroke-dasharray="4 4"/>
      <line x1="400" y1="30" x2="400" y2="370" stroke="var(--chart-grid)" stroke-width="1" stroke-dasharray="4 4"/>
      <line x1="600" y1="30" x2="600" y2="370" stroke="var(--chart-grid)" stroke-width="1" stroke-dasharray="4 4"/>

      <!-- Power Conduits Connecting to Central Station Hub -->
      <!-- Wind Turbine to BESS -->
      <line class="conduit-line conduit-active" x1="120" y1="100" x2="280" y2="200"/>
      <!-- Solar Array to BESS -->
      <line class="conduit-line conduit-active" x1="120" y1="300" x2="280" y2="200"/>
      <!-- BESS to Central Hub -->
      <line class="conduit-line conduit-active" x1="280" y1="200" x2="420" y2="200" stroke-width="4"/>
      <!-- Diesel Generator to Central Hub -->
      <line class="conduit-line" id="conduitGen" x1="420" y1="60" x2="420" y2="200"/>
      <!-- Central Hub to Life Support / Habitat Core -->
      <line class="conduit-line conduit-active" x1="420" y1="200" x2="600" y2="120"/>
      <!-- Central Hub to Science Drill & Cryo Rig -->
      <line class="conduit-line conduit-active" id="conduitScience" x1="420" y1="200" x2="650" y2="250"/>
      <!-- Central Hub to Aux Drone Port -->
      <line class="conduit-line conduit-active" id="conduitDrone" x1="420" y1="200" x2="520" y2="330"/>

      <!-- 1. Wind Turbine Array Node -->
      <g class="schematic-node" data-asset="WIND_FIELD" transform="translate(120, 100)">
        <circle r="36" fill="var(--bg-surface-elevated)" stroke="var(--glacier)" stroke-width="2"/>
        <text y="-8" text-anchor="middle" fill="var(--glacier)" font-size="12" font-weight="bold" font-family="monospace">WIND</text>
        <text y="10" text-anchor="middle" fill="var(--text-main)" font-size="10" font-family="monospace">15 kW Betz</text>
        <text y="24" text-anchor="middle" fill="var(--text-dim)" font-size="8" font-family="monospace">Turbine Field</text>
      </g>

      <!-- 2. Solar PV Bi-facial Node -->
      <g class="schematic-node" data-asset="SOLAR_FIELD" transform="translate(120, 300)">
        <circle r="36" fill="var(--bg-surface-elevated)" stroke="var(--amber)" stroke-width="2"/>
        <text y="-8" text-anchor="middle" fill="var(--amber)" font-size="12" font-weight="bold" font-family="monospace">SOLAR</text>
        <text y="10" text-anchor="middle" fill="var(--text-main)" font-size="10" font-family="monospace">22 kW PV</text>
        <text y="24" text-anchor="middle" fill="var(--text-dim)" font-size="8" font-family="monospace">Bi-facial Array</text>
      </g>

      <!-- 3. Battery Storage (BESS) Node -->
      <g class="schematic-node" data-asset="BESS_BANK" transform="translate(280, 200)">
        <circle r="44" fill="url(#bessGlow)"/>
        <circle r="38" fill="var(--bg-surface-elevated)" stroke="var(--emerald)" stroke-width="2.5"/>
        <text y="-10" text-anchor="middle" fill="var(--emerald)" font-size="13" font-weight="bold" font-family="monospace">BESS</text>
        <text y="8" text-anchor="middle" fill="var(--text-main)" font-size="11" font-family="monospace" id="mapBessKwh">85.0 kWh</text>
        <text y="22" text-anchor="middle" fill="var(--text-dim)" font-size="8" font-family="monospace">LiFePO4 Core</text>
      </g>

      <!-- 4. Backup Diesel Generator -->
      <g class="schematic-node" data-asset="DIESEL_GEN" transform="translate(420, 60)">
        <rect x="-35" y="-22" width="70" height="44" rx="4" fill="var(--bg-surface-elevated)" stroke="var(--amber)" stroke-width="2"/>
        <text y="-4" text-anchor="middle" fill="var(--amber)" font-size="11" font-weight="bold" font-family="monospace">GENSET</text>
        <text y="12" text-anchor="middle" fill="var(--text-dim)" font-size="9" font-family="monospace" id="mapGenKw">STANDBY</text>
      </g>

      <!-- 5. Central Station Hub -->
      <g class="schematic-node" data-asset="CENTRAL_HUB" transform="translate(420, 200)">
        <circle r="52" fill="url(#hubGlow)"/>
        <circle r="44" fill="var(--bg-deep)" stroke="var(--glacier)" stroke-width="3"/>
        <text y="-12" text-anchor="middle" fill="var(--glacier)" font-size="12" font-weight="bold" font-family="monospace">STATION HUB</text>
        <text y="6" text-anchor="middle" fill="var(--text-main)" font-size="10" font-family="monospace">Microgrid Core</text>
        <text y="22" text-anchor="middle" fill="var(--emerald)" font-size="9" font-family="monospace" id="mapNetFlow">STABLE</text>
      </g>

      <!-- 6. P1 Habitat & Thermal Core -->
      <g class="schematic-node" data-asset="HABITAT_CORE" transform="translate(600, 120)">
        <circle r="34" fill="var(--bg-surface-elevated)" stroke="var(--glacier)" stroke-width="2"/>
        <text y="-8" text-anchor="middle" fill="var(--glacier)" font-size="11" font-weight="bold" font-family="monospace">HABITAT</text>
        <text y="8" text-anchor="middle" fill="var(--text-main)" font-size="9" font-family="monospace">P1 Critical</text>
        <text y="20" text-anchor="middle" fill="var(--text-dim)" font-size="8" font-family="monospace">14.0 kW</text>
      </g>

      <!-- 7. P2 Science & Deep Core Drill -->
      <g class="schematic-node" data-asset="SCIENCE_BAY" transform="translate(650, 250)">
        <circle r="34" fill="var(--bg-surface-elevated)" stroke="var(--amber)" stroke-width="2"/>
        <text y="-8" text-anchor="middle" fill="var(--amber)" font-size="11" font-weight="bold" font-family="monospace">SCIENCE</text>
        <text y="8" text-anchor="middle" fill="var(--text-main)" font-size="9" font-family="monospace">P2 Deep Drill</text>
        <text y="20" text-anchor="middle" fill="var(--text-dim)" font-size="8" font-family="monospace">8.5 kW</text>
      </g>

      <!-- 8. P3 Aux Drone & Sensor Bay -->
      <g class="schematic-node" data-asset="AUX_BAY" transform="translate(520, 330)">
        <circle r="28" fill="var(--bg-surface-elevated)" stroke="var(--text-dim)" stroke-width="1.5"/>
        <text y="-4" text-anchor="middle" fill="var(--text-dim)" font-size="10" font-family="monospace">AUX BAY</text>
        <text y="10" text-anchor="middle" fill="var(--text-main)" font-size="8" font-family="monospace">P3 Drone</text>
      </g>
    </svg>
  `;

  container.innerHTML = svgMarkup;
}

/**
 * Handle clicks and tooltips on schematic nodes
 */
function bindMapInteractions() {
  const nodes = document.querySelectorAll('.schematic-node');
  nodes.forEach(node => {
    node.addEventListener('click', () => {
      const asset = node.getAttribute('data-asset');
      const messages = {
        'WIND_FIELD': 'Wind Array: 3-Blade Aerodynamic Turbine with pitch brake cutoff at 25 m/s.',
        'SOLAR_FIELD': 'Solar Field: Vertical Antarctic bi-facial PVs capturing direct sunlight and ground snow albedo.',
        'BESS_BANK': 'Battery Energy Storage (BESS): 160 kWh LiFePO4 bank conditioned at +15°C internal cell temp.',
        'DIESEL_GEN': 'Emergency Genset: Fast-crank diesel backup synchronized with priority bus dispatch.',
        'CENTRAL_HUB': 'Central Microgrid Inverter: Autonomous AI power router handling load shedding and phase balance.',
        'HABITAT_CORE': 'Habitat & Life Support: P1 Protected Core. Interlocked against accidental shedding.',
        'SCIENCE_BAY': 'Science Drill & Cryo: P2 Science asset subject to green energy window scheduling.',
        'AUX_BAY': 'Auxiliary Drone Port: P3 asset prioritized for early shedding during deficit.'
      };
      showToast(messages[asset] || `Inspecting ${asset}`, 'info');
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initStationMap();
});




