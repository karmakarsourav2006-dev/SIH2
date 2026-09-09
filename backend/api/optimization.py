from fastapi import APIRouter, HTTPException
from backend.models.energy import RelayToggleRequest
from backend.services.energy_service import EnergyService
from backend.optimization.energy_optimizer import EnergyOptimizer

router = APIRouter(prefix="/api/optimization", tags=["Optimization & Relays"])

@router.get("/relays")
def get_relays(station_id: str = "ST-01"):
    loads = EnergyService.get_station_loads(station_id)
    return {"ok": True, "loads": loads}

@router.post("/relays")
def toggle_relay(payload: RelayToggleRequest):
    updated = EnergyService.toggle_load_relay(payload.load_id, payload.station_id)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Load '{payload.load_id}' not found")
    return {"ok": True, "load": updated}

@router.get("/green-windows")
def get_green_windows(required_kwh: float = 20.0, duration_hrs: float = 3.0):
    # Simulated 24-hr forecast windows based on solar/wind variation
    timeline = [
        {"time_label": "00:00 - 04:00 UTC", "surplus_kw": 0.0},
        {"time_label": "04:00 - 08:00 UTC", "surplus_kw": 4.5},
        {"time_label": "08:00 - 12:00 UTC", "surplus_kw": 12.8},
        {"time_label": "12:00 - 16:00 UTC (Solar Noon)", "surplus_kw": 19.5},
        {"time_label": "16:00 - 20:00 UTC (Wind Peak)", "surplus_kw": 16.2},
        {"time_label": "20:00 - 24:00 UTC", "surplus_kw": 5.0}
    ]
    windows = EnergyOptimizer.calculate_green_windows(timeline, required_kwh, duration_hrs)
    return {
        "ok": True,
        "required_kwh": required_kwh,
        "duration_hrs": duration_hrs,
        "avg_kw_needed": round(required_kwh / max(0.5, duration_hrs), 2),
        "windows": windows
    }

