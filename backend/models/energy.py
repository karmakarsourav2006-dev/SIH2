from pydantic import BaseModel, Field
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

