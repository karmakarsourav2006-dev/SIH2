from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.services.station_service import StationService
from backend.database.init_db import init_database
from backend.database import get_db

router = APIRouter(prefix="/api/admin", tags=["Admin & Station Config"])

class HardwareConfigUpdate(BaseModel):
    station_id: str = "ST-01"
    battery_capacity_kwh: Optional[float] = None
    generator_rating_kw: Optional[float] = None
    base_thermal_rating_kw: Optional[float] = None

@router.get("/config")
def get_station_config(station_id: str = "ST-01"):
    station = StationService.get_station_by_id(station_id)
    return {
        "ok": True,
        "station": station,
        "llm_provider": "Ollama / Deterministic Rule Engine",
        "thresholds": {
            "critical_soc_pct": 20.0,
            "max_net_deficit_kw": -12.0,
            "anomaly_surge_ratio": 1.25
        }
    }

@router.post("/config")
def update_station_config(payload: HardwareConfigUpdate):
    updates = {}
    if payload.battery_capacity_kwh is not None:
        updates["battery_capacity_kwh"] = payload.battery_capacity_kwh
    if payload.generator_rating_kw is not None:
        updates["generator_rating_kw"] = payload.generator_rating_kw
    if payload.base_thermal_rating_kw is not None:
        updates["base_thermal_rating_kw"] = payload.base_thermal_rating_kw

    updated = StationService.update_station(payload.station_id, updates)
    return {"ok": True, "station": updated}

@router.post("/reset-db")
def reset_database():
    import os
    from backend.config import settings
    # Re-initialize DB
    if os.path.exists(settings.DB_PATH):
        try:
            os.remove(settings.DB_PATH)
        except Exception:
            pass
    init_database(settings.DB_PATH)
    return {"ok": True, "message": "Database restored to clean seed state."}

@router.get("/logs")
def get_system_logs(limit: int = 50):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM energy_records ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return {"ok": True, "logs": [dict(r) for r in rows]}

