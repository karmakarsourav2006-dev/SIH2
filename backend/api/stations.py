from fastapi import APIRouter, HTTPException
from backend.services.station_service import StationService
from backend.services.digital_twin import DigitalTwin

router = APIRouter(prefix="/api/stations", tags=["Stations"])

@router.get("")
def list_stations():
    stations = StationService.get_all_stations()
    return {"ok": True, "stations": stations}

@router.get("/{station_id}")
def get_station(station_id: str):
    station = StationService.get_station_by_id(station_id)
    if not station:
        raise HTTPException(status_code=404, detail=f"Station '{station_id}' not found")
    return {"ok": True, "station": station}

@router.get("/{station_id}/status")
def get_station_status(station_id: str, wind_mps: float = 12.0, lux: float = 350.0, temp_c: float = -28.0, battery_kwh: float = 85.0, gen_kw: float = 0.0):
    state = DigitalTwin.evaluate_state(
        station_id=station_id,
        wind_mps=wind_mps,
        lux=lux,
        temp_c=temp_c,
        battery_kwh=battery_kwh,
        gen_kw=gen_kw
    )
    return {"ok": True, "state": state}

