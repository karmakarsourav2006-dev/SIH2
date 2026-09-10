import json
import logging
import math
import re
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from backend.config import settings

logger = logging.getLogger("openweather_client")

# Known station coordinates fallback mapping (lat, lon)
STATION_COORDINATES: Dict[str, Tuple[float, float]] = {
    "ST-01": (-70.7661, 11.7322),   # Maitri Base
    "ST-02": (-69.4078, 76.1872),   # Bharati Base
    "ST-03": (-90.0000, 0.0000),    # Amundsen-Scott South Pole
    "ST-04": (-75.1000, 123.3333),  # Concordia Station
}

def parse_dms_coordinates(coord_str: str) -> Optional[Tuple[float, float]]:
    """Parses strings like '70°45′58″S 11°43′56″E' or '-70.766, 11.732' into (lat, lon)."""
    if not coord_str or not isinstance(coord_str, str):
        return None
    coord_str = coord_str.strip()

    # Direct decimal check: "-70.766, 11.732"
    dec_match = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)$", coord_str)
    if dec_match:
        return float(dec_match.group(1)), float(dec_match.group(2))

    # DMS pattern check: DD [deg] MM [min] SS [sec] [NSEW]
    dms_pattern = r"(\d+)[\u00b0?\s]+(\d+)[\u2032?'\s]+(?:(\d+(?:\.\d+)?)[\u2033?\"\s]*)?([NSEWnsew])"
    matches = re.findall(dms_pattern, coord_str)
    if len(matches) == 2:
        coords = []
        for d, m, s, direction in matches:
            deg = float(d) + float(m) / 60.0 + (float(s) if s else 0.0) / 3600.0
            if direction.upper() in ("S", "W"):
                deg = -deg
            coords.append(deg)
        return coords[0], coords[1]

    return None

class OpenWeatherClient:
    """Production client for OpenWeather API with caching, retry-safety, and polar normalization."""

    _cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_station_coords(cls, station_id: str, station_info: Optional[Dict[str, Any]] = None) -> Tuple[float, float]:
        """Resolves latitude and longitude for a station."""
        if station_info and station_info.get("coordinates"):
            parsed = parse_dms_coordinates(station_info["coordinates"])
            if parsed:
                return parsed

        if station_id in STATION_COORDINATES:
            return STATION_COORDINATES[station_id]

        return (settings.DEFAULT_STATION_LAT, settings.DEFAULT_STATION_LON)

    @classmethod
    def is_configured(cls) -> bool:
        """Checks if a valid API key is present without exposing the key value."""
        key = (settings.OPENWEATHER_API_KEY or "").strip()
        return bool(key and key != "your_api_key_here")

    @classmethod
    def _fetch_url(cls, url: str, timeout: float = 6.0) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Fetches JSON from URL with timeout and sanitizes errors."""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "PolarEnergyAI/2.0 (Mission Operations)"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw), None
                return None, f"HTTP status {resp.status}"
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return None, "INVALID_API_KEY: OpenWeather unauthorized. Check configured key."
            elif e.code == 429:
                return None, "RATE_LIMITED: OpenWeather API query limit reached."
            return None, f"HTTP_{e.code}"
        except urllib.error.URLError as e:
            return None, f"NETWORK_UNAVAILABLE: {e.reason}"
        except Exception as e:
            return None, f"FETCH_FAILED: {str(e)}"

    @classmethod
    def fetch_current_weather(
        cls,
        station_id: str = "ST-01",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        station_info: Optional[Dict[str, Any]] = None,
        bypass_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Fetches and normalizes current weather for a station.
        Returns unified weather dict guaranteed to contain all polar microgrid fields.
        """
        cache_key = f"current_{station_id}"
        now = time.time()

        # Check Cache
        if not bypass_cache and cache_key in cls._cache:
            entry = cls._cache[cache_key]
            if (now - entry["cached_at"]) < settings.WEATHER_CACHE_TTL_SECONDS:
                cached_data = dict(entry["data"])
                cached_data["cached"] = True
                return cached_data

        if lat is None or lon is None:
            lat, lon = cls.get_station_coords(station_id, station_info)

        if not cls.is_configured():
            return cls._generate_fallback(
                station_id=station_id,
                reason="API key not configured. Set OPENWEATHER_API_KEY in .env"
            )

        api_key = settings.OPENWEATHER_API_KEY.strip()
        url = f"{settings.OPENWEATHER_BASE_URL}/weather?lat={lat:.4f}&lon={lon:.4f}&appid={api_key}&units=metric"

        data, err = cls._fetch_url(url)
        if err or not data:
            logger.warning(f"OpenWeather fetch failed for {station_id}: {err}")
            return cls._generate_fallback(station_id=station_id, reason=err or "Unknown API error")

        # Normalize OpenWeather response
        normalized = cls._normalize_current(station_id, data, lat, lon)

        # Store in cache
        cls._cache[cache_key] = {
            "cached_at": now,
            "data": normalized
        }

        return normalized

    @classmethod
    def fetch_forecast(
        cls,
        station_id: str = "ST-01",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        station_info: Optional[Dict[str, Any]] = None,
        bypass_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Fetches 5-day / 3-hour forecast and aggregates next 24-48 hours.
        """
        cache_key = f"forecast_{station_id}"
        now = time.time()

        if not bypass_cache and cache_key in cls._cache:
            entry = cls._cache[cache_key]
            if (now - entry["cached_at"]) < settings.WEATHER_CACHE_TTL_SECONDS:
                cached_data = dict(entry["data"])
                cached_data["cached"] = True
                return cached_data

        if lat is None or lon is None:
            lat, lon = cls.get_station_coords(station_id, station_info)

        if not cls.is_configured():
            return cls._generate_fallback_forecast(station_id, "API key not configured")

        api_key = settings.OPENWEATHER_API_KEY.strip()
        url = f"{settings.OPENWEATHER_BASE_URL}/forecast?lat={lat:.4f}&lon={lon:.4f}&appid={api_key}&units=metric"

        data, err = cls._fetch_url(url)
        if err or not data:
            return cls._generate_fallback_forecast(station_id, err or "Forecast API error")

        normalized_forecast = cls._normalize_forecast(station_id, data)

        cls._cache[cache_key] = {
            "cached_at": now,
            "data": normalized_forecast
        }

        return normalized_forecast

    @classmethod
    def _normalize_current(cls, station_id: str, raw: Dict[str, Any], lat: float, lon: float) -> Dict[str, Any]:
        """Normalizes OpenWeather raw JSON into polar microgrid schema."""
        main = raw.get("main", {})
        wind = raw.get("wind", {})
        weather_list = raw.get("weather", [{}])
        weather_0 = weather_list[0] if weather_list else {}
        clouds = raw.get("clouds", {}).get("all", 20)
        snow = raw.get("snow", {}).get("1h", 0.0)

        temp_c = float(main.get("temp", -28.0))
        humidity = float(main.get("humidity", 75))
        pressure_hpa = float(main.get("pressure", 990))
        wind_mps = float(wind.get("speed", 12.0))
        wind_deg = float(wind.get("deg", 180))
        wind_gust = float(wind.get("gust", wind_mps * 1.3))

        condition = weather_0.get("main", "Clear")
        description = weather_0.get("description", "clear sky")
        icon = weather_0.get("icon", "01d")

        # Solar Lux estimation from polar sun position and cloud occlusion
        lux = cls._estimate_polar_lux(clouds=clouds, lat=lat)

        # Blizzard severity index calculation (0.0 to 1.0)
        # Severity increases with wind speed > 15 m/s, snow presence, low visibility (< 1000m)
        visibility = raw.get("visibility", 10000)
        blizzard_severity = cls._compute_blizzard_severity(wind_mps, snow, visibility, condition)

        return {
            "station_id": station_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "temp_c": round(temp_c, 1),
            "wind_mps": round(wind_mps, 1),
            "lux": round(lux, 0),
            "blizzard_severity": round(blizzard_severity, 2),
            "humidity": round(humidity, 1),
            "pressure_hpa": round(pressure_hpa, 1),
            "wind_deg": wind_deg,
            "wind_gust": round(wind_gust, 1),
            "clouds_pct": clouds,
            "condition": condition,
            "description": description.capitalize(),
            "icon": icon,
            "is_live": True,
            "provider": "OpenWeather Live",
            "cached": False
        }

    @classmethod
    def _normalize_forecast(cls, station_id: str, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes 5-day / 3-hour list into 24-48h forecast slots."""
        items = raw.get("list", [])
        slots = []
        
        # Take next 8 periods (24 hours)
        for it in items[:8]:
            dt_txt = it.get("dt_txt", "")
            main = it.get("main", {})
            wind = it.get("wind", {})
            weather_0 = it.get("weather", [{}])[0]
            clouds = it.get("clouds", {}).get("all", 20)

            t_c = float(main.get("temp", -28.0))
            w_mps = float(wind.get("speed", 12.0))
            lux = max(0.0, 750.0 * (1.0 - (clouds / 150.0)))
            
            slots.append({
                "datetime": dt_txt,
                "time_label": dt_txt.split(" ")[-1][:5] if " " in dt_txt else dt_txt,
                "temp_c": round(t_c, 1),
                "wind_mps": round(w_mps, 1),
                "lux": round(lux, 0),
                "condition": weather_0.get("main", "Clear"),
                "description": weather_0.get("description", "").capitalize()
            })

        # Calculate 24h summary
        avg_temp = round(sum(s["temp_c"] for s in slots) / max(1, len(slots)), 1) if slots else -28.0
        max_wind = round(max((s["wind_mps"] for s in slots), default=12.0), 1)
        avg_wind = round(sum(s["wind_mps"] for s in slots) / max(1, len(slots)), 1) if slots else 12.0

        return {
            "ok": True,
            "station_id": station_id,
            "provider": "OpenWeather Forecast",
            "summary_24h": {
                "avg_temp_c": avg_temp,
                "avg_wind_mps": avg_wind,
                "max_wind_mps": max_wind,
                "wind_favorability": "Favorable for turbine generation" if 4.0 <= avg_wind <= 22.0 else "Low / Cut-out risk"
            },
            "slots": slots,
            "cached": False
        }

    @staticmethod
    def _estimate_polar_lux(clouds: float, lat: float) -> float:
        """Estimates surface illumination (Lux) accounting for clouds."""
        now_hour = datetime.utcnow().hour
        # Diurnal solar cycle in polar regions
        solar_elevation = math.sin(math.radians((now_hour - 6) * 15))
        if solar_elevation <= 0:
            base_lux = 15.0 # Twilight / polar night minimum
        else:
            base_lux = 15.0 + (solar_elevation * 750.0)

        # Cloud derating
        cloud_factor = max(0.15, 1.0 - (clouds / 120.0))
        return round(max(0.0, base_lux * cloud_factor), 0)

    @staticmethod
    def _compute_blizzard_severity(wind_mps: float, snow: float, visibility: float, condition: str) -> float:
        """Computes 0.0-1.0 severity score for blizzard hazard alert."""
        severity = 0.0
        if wind_mps > 15.0:
            severity += min(0.5, (wind_mps - 15.0) * 0.035)
        if "snow" in condition.lower() or snow > 0.0:
            severity += 0.3
        if visibility < 2000:
            severity += min(0.2, (2000 - visibility) / 10000.0)
        return min(1.0, max(0.0, severity))

    @classmethod
    def _generate_fallback(cls, station_id: str, reason: str = "Offline") -> Dict[str, Any]:
        """Graceful polar station fallback if OpenWeather is unconfigured or unreachable."""
        return {
            "station_id": station_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "temp_c": -28.0,
            "wind_mps": 12.0,
            "lux": 350.0,
            "blizzard_severity": 0.1,
            "humidity": 75.0,
            "pressure_hpa": 990.0,
            "wind_deg": 180.0,
            "wind_gust": 15.5,
            "clouds_pct": 25,
            "condition": "Snow",
            "description": "Sub-zero Antarctic baseline",
            "icon": "13d",
            "is_live": False,
            "provider": "Fallback Station Baseline",
            "note": reason,
            "cached": False
        }

    @classmethod
    def _generate_fallback_forecast(cls, station_id: str, reason: str) -> Dict[str, Any]:
        """Synthetic 24h timeline fallback."""
        slots = []
        for h in range(0, 24, 3):
            slots.append({
                "datetime": f"{h:02d}:00 UTC",
                "time_label": f"{h:02d}:00",
                "temp_c": -28.0 + (1.5 if 9 <= h <= 15 else -1.5),
                "wind_mps": 12.0 + (h % 3),
                "lux": 350.0 if 6 <= h <= 18 else 20.0,
                "condition": "Snow",
                "description": "Antarctic seasonal baseline"
            })
        return {
            "ok": True,
            "station_id": station_id,
            "provider": "Fallback Station Baseline",
            "summary_24h": {
                "avg_temp_c": -28.0,
                "avg_wind_mps": 12.5,
                "max_wind_mps": 14.0,
                "wind_favorability": "Favorable for turbine generation"
            },
            "slots": slots,
            "note": reason,
            "cached": False
        }
