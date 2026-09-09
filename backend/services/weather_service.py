from typing import List, Dict, Any
from backend.database import get_db

class WeatherService:
    @staticmethod
    def record_weather(station_id: str, temp_c: float, wind_mps: float, lux: float, blizzard_severity: float) -> Dict[str, Any]:
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO weather (station_id, temp_c, wind_mps, lux, blizzard_severity) VALUES (?, ?, ?, ?, ?)",
                (station_id, temp_c, wind_mps, lux, blizzard_severity)
            )
            conn.commit()
            record_id = cursor.lastrowid
            row = conn.execute("SELECT * FROM weather WHERE id = ?", (record_id,)).fetchone()
            return dict(row)

    @staticmethod
    def get_latest_weather(station_id: str = "ST-01") -> Dict[str, Any]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM weather WHERE station_id = ? ORDER BY id DESC LIMIT 1", (station_id,)).fetchone()
            if row:
                return dict(row)
            return {
                "station_id": station_id,
                "temp_c": -28.0,
                "wind_mps": 12.0,
                "lux": 350.0,
                "blizzard_severity": 0.1
            }

