from pydantic import BaseModel
from typing import Optional

class AlertCreate(BaseModel):
    station_id: str = "ST-01"
    severity: str = "INFO"  # CRITICAL, WARNING, INFO
    category: str = "SYSTEM"  # ANOMALY, SURVIVAL, SYSTEM, EXPERIMENT
    message: str
    root_cause: Optional[str] = None

class Alert(AlertCreate):
    id: int
    timestamp: str
    acknowledged: int = 0

