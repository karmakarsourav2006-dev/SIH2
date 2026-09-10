from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class TelemetryInput(BaseModel):
    wind_mps: float = Field(default=12.0, ge=0.0, le=50.0, description="Wind velocity in m/s")
    lux: float = Field(default=350.0, ge=0.0, le=2000.0, description="Solar irradiance in Lux / W/m²")
    temp_c: float = Field(default=-28.0, ge=-70.0, le=20.0, description="Ambient polar temperature in °C")
    battery_kwh: float = Field(default=85.0, ge=5.0, le=160.0, description="Battery energy storage reserve in kWh")
    gen_kw: float = Field(default=0.0, ge=0.0, le=40.0, description="Secondary diesel generator output in kW")

class LoadToggleInput(BaseModel):
    id: str

class ExperimentScheduleInput(BaseModel):
    id: str
    action: str = Field(default="run", description="Action to perform: run, defer, or queue")

class AssistantQueryInput(BaseModel):
    query: str

