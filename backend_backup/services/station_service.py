from typing import List, Dict, Any, Optional
from backend.database import get_db

class StationService:
    @staticmethod
    def get_all_stations() -> List[Dict[str, Any]]:
        with get_db() as conn:
            rows = conn.execute("SELECT * FROM stations").fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_station_by_id(station_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM stations WHERE id = ?", (station_id,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_station(station_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            fields = []
            values = []
            for k, v in updates.items():
                if k in ("name", "coordinates", "battery_capacity_kwh", "generator_rating_kw", "base_thermal_rating_kw", "status"):
                    fields.append(f"{k} = ?")
                    values.append(v)
            if not fields:
                return StationService.get_station_by_id(station_id)

            values.append(station_id)
            conn.execute(f"UPDATE stations SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()
            return StationService.get_station_by_id(station_id)

