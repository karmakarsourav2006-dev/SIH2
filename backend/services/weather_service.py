from typing import List, Dict, Any, Optional
from backend.database import get_db
from backend.services.openweather_client import OpenWeatherClient

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

    @classmethod
    def get_latest_weather(cls, station_id: str = "ST-01", refresh_live: bool = True) -> Dict[str, Any]:
        """
        Retrieves weather for station.
        If refresh_live is True, queries OpenWeather (with caching).
        Persists live samples to SQLite and falls back gracefully to DB history if unreachable.
        """
        if refresh_live:
            try:
                from backend.services.station_service import StationService
                station = StationService.get_station_by_id(station_id)
                live = OpenWeatherClient.fetch_current_weather(station_id=station_id, station_info=station)
                if live:
                    # Persist reading if not just serving from memory cache
                    if not live.get("cached", False):
                        try:
                            cls.record_weather(
                                station_id=station_id,
                                temp_c=live["temp_c"],
                                wind_mps=live["wind_mps"],
                                lux=live["lux"],
                                blizzard_severity=live["blizzard_severity"]
                            )
                        except Exception:
                            pass
                    return live
            except Exception:
                pass

        # Fallback to local DB record
        with get_db() as conn:
            row = conn.execute("SELECT * FROM weather WHERE station_id = ? ORDER BY id DESC LIMIT 1", (station_id,)).fetchone()
            if row:
                res = dict(row)
                res["provider"] = "Local Station Telemetry DB"
                res["is_live"] = False
                res["cached"] = True
                return res

        # Station baseline fallback
        return OpenWeatherClient._generate_fallback(station_id, "No live or database telemetry available")

    @classmethod
    def get_forecast(cls, station_id: str = "ST-01", bypass_cache: bool = False) -> Dict[str, Any]:
        """Fetches 24-48h forecast for station via OpenWeather."""
        try:
            from backend.services.station_service import StationService
            station = StationService.get_station_by_id(station_id)
            return OpenWeatherClient.fetch_forecast(station_id=station_id, station_info=station, bypass_cache=bypass_cache)
        except Exception as e:
            return OpenWeatherClient._generate_fallback_forecast(station_id, str(e))


