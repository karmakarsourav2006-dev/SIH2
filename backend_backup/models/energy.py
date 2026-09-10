from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class EquipmentSignature(BaseModel):
    device_id: str
    name: str
    subsystem: str
    priority_tier: str
    nominal_kw: float
    tolerance_percent: float
    duty_cycle: float
    status: str = "NORMAL"

class EquipmentTelemetryLog(BaseModel):
    id: Optional[int] = None
    device_id: str
    timestamp: datetime
    observed_kw: float
    deviation_percent: float
    anomaly_score: float
    flagged: bool
    diagnosis: str
from typing import Optional, List, Dict, Any

class LoadRelay(BaseModel):
    id: str
    station_id: str = "ST-01"
    name: str
    priority: int = Field(ge=1, le=3)
    nominal_kw: float
    live_kw: float
    status: str = "ONLINE"
    is_surge: Optional[bool] = False
    excess_kw: Optional[float] = 0.0
    surge_pct: Optional[float] = 0.0

class RelayToggleRequest(BaseModel):
    load_id: str
    station_id: Optional[str] = "ST-01"

class EnergySimulationStep(BaseModel):
    station_id: str = "ST-01"
    wind_mps: float = 12.0
    lux: float = 350.0
    temp_c: float = -28.0
    battery_kwh: float = 85.0
    gen_kw: float = 0.0

