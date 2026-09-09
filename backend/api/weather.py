from fastapi import APIRouter
from backend.models.weather import WeatherInput
from backend.services.weather_service import WeatherService

router = APIRouter(prefix="/api/weather", tags=["Weather"])

@router.get("")
def get_weather(station_id: str = "ST-01"):
    weather = WeatherService.get_latest_weather(station_id)
    return {"ok": True, "weather": weather}

@router.post("")
def post_weather(input_data: WeatherInput):
    record = WeatherService.record_weather(
        station_id=input_data.station_id,
        temp_c=input_data.temp_c,
        wind_mps=input_data.wind_mps,
        lux=input_data.lux,
        blizzard_severity=input_data.blizzard_severity
    )
    return {"ok": True, "recorded": record}

