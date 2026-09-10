from typing import Optional, Literal
from fastapi import APIRouter
from pydantic import BaseModel, Field
from backend.services.equipment import evaluate_equipment_telemetry, list_signatures, live_anomalies, equipment_action
from backend.config import settings
import sqlite3

router = APIRouter(prefix="/api/equipment", tags=["equipment"])
class Evaluation(BaseModel):
    device_id: str
    observed_kw: float = Field(ge=0)
    timestamp: Optional[str] = None
class Action(BaseModel):
    action: Literal["ISOLATE", "RESET", "RECALIBRATE"]

@router.get("/signatures")
def signatures(): return list_signatures()
@router.post("/evaluate")
def evaluate(payload: Evaluation):
    result = evaluate_equipment_telemetry(payload.device_id, payload.observed_kw, payload.timestamp)
    if result["status"] == "CRITICAL_MALFUNCTION" and result["priority_tier"] in ("P1", "P2"):
        conn = sqlite3.connect(settings.DB_PATH)
        conn.execute("INSERT INTO alerts (station_id,severity,category,message,root_cause,acknowledged) VALUES (?,?,?,?,?,0)", ("ST-01", "CRITICAL", "EQUIPMENT", f"{result['name']} malfunction: {result['observed_kw']} kW ({result['deviation_percent']}%)", result["diagnosis"]))
        conn.commit(); conn.close()
    return result
@router.post("/{device_id}/action")
def action(device_id: str, payload: Action): return equipment_action(device_id, payload.action)
@router.get("/anomalies/live")
def anomalies_live(): return live_anomalies()
