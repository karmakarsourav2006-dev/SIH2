from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.services.energy_service import EnergyService
from backend.services.digital_twin import DigitalTwin

router = APIRouter(prefix="/api/emergency", tags=["Survival Emergency"])

class EmergencyActionRequest(BaseModel):
    station_id: Optional[str] = "ST-01"

@router.get("/status")
def get_emergency_status(station_id: str = "ST-01", battery_kwh: float = 85.0, gen_kw: float = 0.0):
    state = DigitalTwin.evaluate_state(station_id=station_id, battery_kwh=battery_kwh, gen_kw=gen_kw)
    return {
        "ok": True,
        "mode": state["mode"],
        "is_critical": state["is_critical"],
        "safe_runtime_hours": state["survivability"]["safe_runtime_hours"],
        "p1_isolated_hours": state["survivability"]["p1_isolated_hours"],
        "emergency_events": state["emergency_events"]
    }

@router.post("/shed")
def trigger_emergency_shed(payload: Optional[EmergencyActionRequest] = None, station_id: Optional[str] = None):
    sid = (payload.station_id if payload and payload.station_id else None) or station_id or "ST-01"
    loads = EnergyService.get_station_loads(sid)
    shedded = []
    for l in loads:
        if l["priority"] in (2, 3) and l["status"] == "ONLINE":
            EnergyService.set_load_status(l["id"], "SHEDDED", sid)
            shedded.append(l["name"])
    return {
        "ok": True,
        "mode": "SURVIVAL CRITICAL",
        "action": "EMERGENCY_PRIORITY_SHED",
        "shedded_assets": shedded
    }

@router.post("/restore")
def restore_all(payload: Optional[EmergencyActionRequest] = None, station_id: Optional[str] = None):
    sid = (payload.station_id if payload and payload.station_id else None) or station_id or "ST-01"
    loads = EnergyService.reset_all_loads(sid)
    return {
        "ok": True,
        "mode": "NORMAL RUN",
        "action": "RESTORE_ALL_RELAYS",
        "total_loads": len(loads)
    }


