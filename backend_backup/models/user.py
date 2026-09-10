from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    id: str
    name: str
    role: str
    callsign: Optional[str] = None
    station_id: Optional[str] = "ST-01"

