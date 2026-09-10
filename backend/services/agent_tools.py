"""Operational tools executable by AI assistant or operators."""
from typing import Dict, Any
from backend.services.energy_service import EnergyService
from backend.services.digital_twin import DigitalTwin
from backend.services.weather_service import WeatherService
from backend.forecasting.solar_forecast import compute_solar_power
from backend.forecasting.wind_forecast import compute_wind_power
from backend.forecasting.heating_forecast import compute_thermal_heating

def tool_shed_non_critical(station_id: str = "ST-01") -> Dict[str, Any]:
    loads = EnergyService.get_station_loads(station_id)
    shed_count = 0
    for l in loads:
        if l["priority"] in (2, 3) and l["status"] == "ONLINE":
            EnergyService.set_load_status(l["id"], "SHEDDED", station_id)
            shed_count += 1
    return {"status": "success", "shed_loads_count": shed_count}

def tool_restore_all(station_id: str = "ST-01") -> Dict[str, Any]:
    loads = EnergyService.reset_all_loads(station_id)
    return {"status": "success", "restored_loads_count": len(loads)}

def tool_get_telemetry(station_id: str = "ST-01") -> Dict[str, Any]:
    return DigitalTwin.evaluate_state(station_id=station_id)

def tool_get_current_weather(station_id: str = "ST-01") -> Dict[str, Any]:
    """Retrieves live normalized weather data from OpenWeather for the station."""
    w = WeatherService.get_latest_weather(station_id=station_id, refresh_live=True)
    return {
        "status": "success",
        "station_id": station_id,
        "temperature_celsius": w.get("temp_c"),
        "wind_speed_mps": w.get("wind_mps"),
        "solar_irradiance_lux": w.get("lux"),
        "humidity_pct": w.get("humidity", 75.0),
        "pressure_hpa": w.get("pressure_hpa", 990.0),
        "condition": w.get("condition", "Clear"),
        "description": w.get("description", "Clear"),
        "blizzard_severity": w.get("blizzard_severity", 0.0),
        "is_live": w.get("is_live", False),
        "provider": w.get("provider", "OpenWeather")
    }

def tool_get_weather_forecast(station_id: str = "ST-01") -> Dict[str, Any]:
    """Retrieves 24-48h forecast from OpenWeather for the station."""
    return WeatherService.get_forecast(station_id=station_id)

def tool_get_energy_weather_impact(station_id: str = "ST-01") -> Dict[str, Any]:
    """
    Correlates actual OpenWeather data with polar microgrid generation and demand physics:
    - Aerodynamic wind turbine generation
    - Bifacial sub-zero solar PV generation
    - Thermodynamic habitat heating load
    - Tomorrow's energy generation trend
    """
    w = WeatherService.get_latest_weather(station_id=station_id, refresh_live=True)
    temp_c = float(w.get("temp_c", -28.0))
    wind_mps = float(w.get("wind_mps", 12.0))
    lux = float(w.get("lux", 350.0))

    solar_kw = compute_solar_power(lux=lux, temp_c=temp_c)
    wind_kw = compute_wind_power(wind_mps=wind_mps)
    heating_kw = compute_thermal_heating(temp_c=temp_c, wind_mps=wind_mps)
    total_renewables_kw = round(solar_kw + wind_kw, 2)

    # Favorability assessments
    if wind_mps < 3.0:
        wind_status = "Sub-cut-in (calm, zero wind output)"
    elif 4.0 <= wind_mps <= 20.0:
        wind_status = f"Highly favorable aerodynamic generation ({wind_kw:.1f} kW output)"
    elif 20.0 < wind_mps <= 25.0:
        wind_status = f"Near rated maximum, approaching safety cut-out limit ({wind_kw:.1f} kW output)"
    else:
        wind_status = "Storm cut-out safety shutdown (>25 m/s, turbine feathered to prevent mechanical damage)"

    # Solar status
    if lux <= 20.0:
        solar_status = "Low solar influx / polar twilight"
    else:
        solar_status = f"Active solar harvesting ({solar_kw:.1f} kW output, sub-zero silicon boost active)"

    # Heating status
    heating_status = f"Habitat heating draw is ~{heating_kw:.1f} kW due to {temp_c:.1f}°C ambient and {wind_mps:.1f} m/s convective windchill"

    # Forecast summary
    fc = WeatherService.get_forecast(station_id=station_id)
    summary_24h = fc.get("summary_24h", {})
    avg_wind_next_24h = summary_24h.get("avg_wind_mps", wind_mps)
    avg_temp_next_24h = summary_24h.get("avg_temp_c", temp_c)
    tomorrow_wind_kw = compute_wind_power(wind_mps=avg_wind_next_24h)
    tomorrow_heating_kw = compute_thermal_heating(temp_c=avg_temp_next_24h, wind_mps=avg_wind_next_24h)

    return {
        "status": "success",
        "station_id": station_id,
        "current_weather": {
            "temp_c": temp_c,
            "wind_mps": wind_mps,
            "lux": lux,
            "condition": w.get("condition"),
            "description": w.get("description"),
            "provider": w.get("provider")
        },
        "current_impact": {
            "solar_power_kw": solar_kw,
            "wind_power_kw": wind_kw,
            "total_renewables_kw": total_renewables_kw,
            "thermal_heating_demand_kw": heating_kw,
            "wind_favorability": wind_status,
            "solar_condition": solar_status,
            "heating_impact": heating_status
        },
        "forecast_impact_tomorrow": {
            "forecast_avg_temp_c": avg_temp_next_24h,
            "forecast_avg_wind_mps": avg_wind_next_24h,
            "estimated_wind_generation_kw": tomorrow_wind_kw,
            "estimated_heating_demand_kw": tomorrow_heating_kw,
            "outlook": f"Tomorrow expected avg wind {avg_wind_next_24h:.1f} m/s will provide ~{tomorrow_wind_kw:.1f} kW wind generation. Heating demand projected at ~{tomorrow_heating_kw:.1f} kW."
        }
    }


