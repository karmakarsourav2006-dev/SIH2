from pydantic import BaseModel
from typing import Optional

class StationBase(BaseModel):
    name: str
    coordinates: Optional[str] = None
    country: Optional[str] = "India"
    battery_capacity_kwh: float = 160.0
    generator_rating_kw: float = 40.0
    base_thermal_rating_kw: float = 14.0
    status: str = "ONLINE"

class Station(StationBase):
    id: str

class StationStatus(BaseModel):
    station_id: str
    station_name: str
    mode: str
    is_survival: bool
    battery_soc_pct: float
    battery_kwh: float
    total_generation_kw: float
    solar_kw: float
    wind_kw: float
    gen_kw: float
    active_demand_kw: float
    net_flow_kw: float
    safe_runtime_hours: float
    p1_isolated_hours: float
    active_loads_count: int
    total_loads_count: int

