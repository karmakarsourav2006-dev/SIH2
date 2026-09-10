from typing import List, Dict, Any, Optional
from backend.database import get_db

class EnergyService:
    @staticmethod
    def get_station_loads(station_id: str = "ST-01") -> List[Dict[str, Any]]:
        with get_db() as conn:
            rows = conn.execute("SELECT * FROM loads WHERE station_id = ? ORDER BY priority ASC, id ASC", (station_id,)).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def toggle_load_relay(load_id: str, station_id: str = "ST-01") -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM loads WHERE id = ? AND station_id = ?", (load_id, station_id)).fetchone()
            if not row:
                return None
            current = str(row["status"]).upper()
            target = "SHEDDED" if current == "ONLINE" else "ONLINE"
            conn.execute("UPDATE loads SET status = ? WHERE id = ? AND station_id = ?", (target, load_id, station_id))
            conn.commit()
            updated = conn.execute("SELECT * FROM loads WHERE id = ? AND station_id = ?", (load_id, station_id)).fetchone()
            return dict(updated)

    @staticmethod
    def reset_all_loads(station_id: str = "ST-01") -> List[Dict[str, Any]]:
        with get_db() as conn:
            conn.execute("UPDATE loads SET status = 'ONLINE' WHERE station_id = ?", (station_id,))
            conn.commit()
            return EnergyService.get_station_loads(station_id)

    @staticmethod
    def set_load_status(load_id: str, status: str, station_id: str = "ST-01") -> bool:
        with get_db() as conn:
            conn.execute("UPDATE loads SET status = ? WHERE id = ? AND station_id = ?", (status.upper(), load_id, station_id))
            conn.commit()
            return True

    @staticmethod
    def record_telemetry(
        station_id: str,
        solar_kw: float,
        wind_kw: float,
        gen_kw: float,
        demand_kw: float,
        soc_pct: float,
        net_flow_kw: float,
        mode: str
    ):
        with get_db() as conn:
            conn.execute("""
                INSERT INTO energy_records (station_id, solar_kw, wind_kw, gen_kw, active_demand_kw, battery_soc_pct, net_flow_kw, mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (station_id, solar_kw, wind_kw, gen_kw, demand_kw, soc_pct, net_flow_kw, mode))
            conn.commit()

