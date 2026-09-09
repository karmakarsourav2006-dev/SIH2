from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class WeatherInput(BaseModel):
    station_id: str = "ST-01"
    temp_c: float = Field(default=-28.0, ge=-75.0, le=20.0)
    wind_mps: float = Field(default=12.0, ge=0.0, le=60.0)
    lux: float = Field(default=350.0, ge=0.0, le=2000.0)
    blizzard_severity: float = Field(default=0.1, ge=0.0, le=1.0)

class WeatherRecord(WeatherInput):
    id: Optional[int] = None
    timestamp: Optional[str] = None

