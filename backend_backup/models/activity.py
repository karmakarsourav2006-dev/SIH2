from pydantic import BaseModel, Field
from typing import Optional

class ActivityCreate(BaseModel):
    name: str
    station_id: str = "ST-01"
    required_kwh: float = Field(gt=0)
    duration_hrs: float = Field(gt=0)
    deadline_hrs: Optional[float] = 24.0
    priority: int = Field(default=2, ge=1, le=3)

class Activity(ActivityCreate):
    id: str
    approval_status: str = "APPROVED"
    execution_status: str = "QUEUED"
    recommended_slot: Optional[str] = None
    avg_power_kw: Optional[float] = 0.0
    safe_to_run: Optional[bool] = False
    ai_recommendation: Optional[str] = None

