# Polar Energy AI (SIH 26061) - Walkthrough & Verification Guide

## Executive Summary
The **Polar Energy AI** platform (Smart India Hackathon SIH 26061, Team Spidey_Force) has been rebuilt into a complete, modular full-stack system with:
1. **Expedition Command Aesthetic**: Deep navy slate background (`#090d16` / `#0d131f`), structural carbon cards (`#151d2d`), glacier cyan indicators (`#38bdf8`), emerald telemetry readouts (`#10b981`), amber advisories (`#f59e0b`), and crimson emergency triggers (`#ef4444`).
2. **Single-Command Startup**: Fully configured to boot with `npm run dev` (`concurrently` running Uvicorn on port 8000 and `live-server` on port 3000 with automatic `/api` proxying).
3. **Multi-Module Microgrid Architecture**: 11 dedicated API routers, aerodynamic Betz wind forecasting, sub-zero enhanced bi-facial solar modeling, thermal loss estimation, 3-tier priority load shedding, what-if stress simulation, green window science allocation, Ollama AI chat with fallback rules, and browser Web Speech voice synthesis/recognition.
4. **Zero Stubs or Placeholders**: 4 complete HTML pages (`index.html`, `dashboard.html`, `researcher.html`, `admin.html`) connected to 7 modular JS client scripts and 3 CSS stylesheets.

---

## Repository Tree Layout
```
polar-energy-ai/
├── package.json
├── requirements.txt
├── docker-compose.yml
├── polar_station.db
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── init_db.py
│   │   └── seed_data.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── station.py
│   │   ├── weather.py
│   │   ├── energy.py
│   │   ├── activity.py
│   │   ├── alert.py
│   │   └── user.py
│   ├── forecasting/
│   │   ├── __init__.py
│   │   ├── solar_forecast.py
│   │   ├── wind_forecast.py
│   │   ├── heating_forecast.py
│   │   ├── demand_forecast.py
│   │   └── model_manager.py
│   ├── optimization/
│   │   ├── __init__.py
│   │   └── energy_optimizer.py
│   ├── anomaly/
│   │   ├── __init__.py
│   │   └── detector.py
│   ├── simulation/
│   │   ├── __init__.py
│   │   └── simulator.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── agent_fallback.py
│   │   └── ollama_service.py
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── stt.py
│   │   └── tts.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── station_service.py
│   │   ├── weather_service.py
│   │   ├── energy_service.py
│   │   ├── digital_twin.py
│   │   └── agent_tools.py
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── background_tasks.py
│   └── api/
│       ├── __init__.py
│       ├── stations.py
│       ├── weather.py
│       ├── emergency.py
│       ├── optimization.py
│       ├── simulation.py
│       ├── forecasting.py
│       ├── activities.py
│       ├── alerts.py
│       ├── admin.py
│       ├── ai_chat.py
│       └── voice.py
└── frontend/
    ├── index.html
    ├── dashboard.html
    ├── researcher.html
    ├── admin.html
    ├── css/
    │   ├── main.css
    │   ├── components.css
    │   └── dashboard.css
    └── js/
        ├── app.js
        ├── dashboard.js
        ├── researcher.js
        ├── admin.js
        ├── simulation.js
        ├── voice.js
        └── map.js
```

---

## 4 Frontend Portals

### 1. Overview Hub (`index.html`)
- Antarctic research stations status overview:
  - **Station Maitri (ST-01)**: Primary Indian research base in Queen Maud Land (160 kWh BESS, 30 kW Wind, 22 kW PV).
  - **Station Bharati (ST-02)**: Larsemann Hills coastal base (200 kWh BESS, 36 kW Wind, 30 kW PV).
  - **Amundsen-Scott (ST-03)**: Geographic South Pole (300 kWh BESS, 80 kW Wind, 40 kW PV).
  - **Concordia Base (ST-04)**: High-altitude Dome C Plateau (180 kWh BESS, 30 kW Wind, 25 kW PV).
- Platform architectural pillars: Aerodynamic Wind Betz Modeling, Sub-zero Boosted Bi-facial Solar, 3-Tier Protected Shedding, Green Window Science Allocation.

### 2. Command Deck (`dashboard.html`)
- Live modulation sliders: Wind Velocity (0-30 m/s), Solar Irradiance (0-1000 Lux), Ambient Temperature (-50 to 0°C), Battery Reserve (5-160 kWh), Secondary Diesel Genset (0-45 kW).
- Primary KPI Cards: Solar kW, Wind kW, Total Renewables kW, Demand kW, Secondary Genset kW, BESS Reserve & SoC %, Net Power Balance kW.
- Autonomous Survivability Radar: Circular progress gauges for Safe Autonomy Runway, P1 Isolated Life-Support Runtime, and Fuel Autonomy Days.
- Station Vector Microgrid Schematic (`js/map.js`): Interactive SVG map animating power conduits and asset telemetry tooltips.
- 3-Tier Load Shedding & Relay Contactor Matrix:
  - **P1 (Life-Critical)**: Habitat Thermal Core & Emergency Satellite Beacon (hard-interlocked against accidental shedding).
  - **P2 (Science Operations)**: Sub-Ice Drill & Cryo-Spectrometry Bay (individually toggled or shed).
  - **P3 (Auxiliary)**: Aux Drone Port (first shed in deficit).
  - One-click buttons: `🚨 Emergency Shed` and `↺ Restore All Relays`.
- What-If Stress Scenarios:
  - **Blizzard Warning**: 28 m/s wind cut-out, 15 Lux snow cover, -45°C freeze.
  - **Generator Trip**: Secondary diesel forced to 0 kW during severe baseline cold.
  - **Midnight Sun Surplus**: 850 Lux, 14 m/s wind, -12°C high renewable margin.
  - **Polar Winter Night**: 0 Lux, 6 m/s wind, -55°C peak heating demand.
- Tactical Diagnostics Terminal: Real-time telemetry feed and automated fault classification (e.g. Cryo-Spectrometry Bay +85% surge anomaly).

### 3. Science Scheduler (`researcher.html`)
- 24-Hour Renewable Surplus Forecast Windows: Algorithmically identifies green slots where surplus wind/solar covers energy requirements.
- Register Science Operation Form: Schedules heavy experiments (e.g. Ice-Core Deep Drill, LIDAR) with duration, required kWh, and deadline.
- Science Allocation Queue: Displays queue status (`QUEUED`, `RUNNING`, `DEFERRED`, `COMPLETED`), continuous kW requirement, and AI advisor recommendations.

### 4. Admin Console (`admin.html`)
- Hardware Calibration: Updates BESS storage capacity (kWh), secondary genset peak rating (kW), and base habitat thermal core rating (kW).
- Emergency Blackout Prevention: Manual system-wide contactor shedding and restoration triggers.
- Clean Database Re-Seed: One-click restoration to pristine hackathon factory seed state.
- System Telemetry Historical Audit Trail: Persisted energy records with timestamp, solar kW, wind kW, demand kW, battery SoC %, and net power flow.

---

## Tactical Voice Copilot (`js/voice.js`)
- Floating microphone FAB button on all pages.
- Web Speech API integration (`SpeechRecognition` / `webkitSpeechRecognition` and `SpeechSynthesisUtterance`).
- Connects directly to `/api/ai_chat` (powered by Ollama or deterministic polar rules fallback).
- Speech queries speak back natural operational summaries, battery horizons, and safety advisories.

---

## Automated Verification Results
All 12 validation tests pass cleanly with HTTP 200:
```
1. GET / -> status: 200
2. GET /api/stations -> status: 200 (4 stations seeded)
3. POST /api/telemetry -> status: 200 (mode: NORMAL RUN / SURVIVAL CRITICAL)
4. GET /api/optimization/green-windows -> status: 200 (3 surplus windows calculated)
5. GET /api/activities -> status: 200 (4 science activities active)
6. GET /api/admin/config -> status: 200 (Maitri Station hardware config)
7. POST /api/ai_chat -> status: 200 (Structured reasoning + voice synthesis payload)
8. POST /api/simulation/scenario/blizzard -> status: 200 (is_critical: True detected)
9. POST /api/emergency/shed -> status: 200 (P2/P3 assets isolated)
10. POST /api/emergency/restore -> status: 200 (All 6 loads restored ONLINE)
11. POST /api/optimization/relays -> status: 200 (Interlocked relay toggled)
12. Static HTML routes (/, /dashboard, /researcher, /admin) -> all status: 200
```

---

## How to Run
Run the single command:
```bash
npm run dev
```
This boots:
- Backend: `http://127.0.0.1:8000` (FastAPI with SQLite, OpenAPI docs at `/docs`)
- Frontend: `http://localhost:3000` (Live reload development server with `/api` proxy)

