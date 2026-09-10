from backend.models.station import Station, StationStatus
from backend.models.weather import WeatherInput, WeatherRecord
from backend.models.energy import LoadRelay, RelayToggleRequest, EnergySimulationStep
from backend.models.activity import Activity, ActivityCreate
from backend.models.alert import Alert, AlertCreate
from backend.models.user import User

try:
    from backend.models_root import (
        AssistantQueryInput,
        TelemetryInput,
        LoadToggleInput,
        ExperimentScheduleInput
    )
except ImportError:
    from pydantic import BaseModel
    class AssistantQueryInput(BaseModel):
        query: str
    class TelemetryInput(BaseModel):
        pass
    class LoadToggleInput(BaseModel):
        id: str
    class ExperimentScheduleInput(BaseModel):
        id: str

__all__ = [
    "Station", "StationStatus",
    "WeatherInput", "WeatherRecord",
    "LoadRelay", "RelayToggleRequest", "EnergySimulationStep",
    "Activity", "ActivityCreate",
    "Alert", "AlertCreate",
    "User",
    "AssistantQueryInput",
    "TelemetryInput",
    "LoadToggleInput",
    "ExperimentScheduleInput"
]


