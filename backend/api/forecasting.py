from fastapi import APIRouter
from backend.forecasting.model_manager import ModelManager
from backend.services.energy_service import EnergyService

router = APIRouter(prefix="/api/forecasting", tags=["Forecasting"])

@router.get("/microgrid")
def get_forecast(wind_mps: float = 12.0, lux: float = 350.0, temp_c: float = -28.0, gen_kw: float = 0.0, station_id: str = "ST-01"):
    loads = EnergyService.get_station_loads(station_id)
    forecast = ModelManager.forecast_microgrid(
        wind_mps=wind_mps,
        lux=lux,
        temp_c=temp_c,
        gen_kw=gen_kw,
        loads=loads,
        experiments=[]
    )
    return {"ok": True, "forecast": forecast}

@router.get("/timeline")
def get_24h_timeline(temp_c: float = -28.0, base_wind: float = 12.0, station_id: str = "ST-01", use_weather_forecast: bool = True):
    # Retrieve real weather forecast if requested
    forecast_data = None
    if use_weather_forecast:
        try:
            from backend.services.weather_service import WeatherService
            fc = WeatherService.get_forecast(station_id)
            if fc and fc.get("slots"):
                forecast_data = fc["slots"]
        except Exception:
            pass

    hours = []
    for h in range(24):
        # Match with forecast slot if available
        slot = None
        if forecast_data:
            slot_idx = min(len(forecast_data) - 1, h // 3)
            slot = forecast_data[slot_idx]

        hour_temp = slot["temp_c"] if slot else temp_c
        hour_wind = slot["wind_mps"] if slot else max(4.0, min(24.0, base_wind + (h % 5 - 2) * 2.5))
        hour_lux = slot["lux"] if slot else (max(0.0, 750.0 * (1.0 - abs(h - 13.0) / 10.0)) if 4 <= h <= 22 else 0.0)

        solar = round(max(0.0, (hour_lux / 1000.0) * 25.0 * 0.88), 2)
        wind_p = round(max(0.0, 0.5 * 1.34 * 16.0 * (min(hour_wind, 12.0) ** 3) * 0.00042), 2)
        demand = 18.5 + (abs(min(0.0, hour_temp)) * 0.15)
        surplus = round((solar + wind_p) - demand, 2)

        hours.append({
            "hour": f"{h:02d}:00 UTC",
            "solar_kw": solar,
            "wind_kw": wind_p,
            "demand_kw": round(demand, 2),
            "surplus_kw": surplus,
            "temp_c": hour_temp,
            "wind_mps": hour_wind
        })
    return {"ok": True, "timeline": hours, "source": "OpenWeather Forecast" if forecast_data else "Seasonal Polar Model"}


