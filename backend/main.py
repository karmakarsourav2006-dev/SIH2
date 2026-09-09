import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database.init_db import init_database
from backend.scheduler.background_tasks import BackgroundScheduler

from backend.api import (
    stations_router,
    weather_router,
    emergency_router,
    optimization_router,
    simulation_router,
    forecasting_router,
    activities_router,
    alerts_router,
    admin_router,
    ai_chat_router,
    voice_router
)

from backend.services.digital_twin import DigitalTwin
from backend.services.energy_service import EnergyService
from pydantic import BaseModel

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    await BackgroundScheduler.start()
    yield
    await BackgroundScheduler.stop()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Smart India Hackathon SIH 26061 // Autonomous Polar Microgrid Platform",
    lifespan=lifespan
)

# Global CORS enabled
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all 11 blueprint routers
app.include_router(stations_router)
app.include_router(weather_router)
app.include_router(emergency_router)
app.include_router(optimization_router)
app.include_router(simulation_router)
app.include_router(forecasting_router)
app.include_router(activities_router)
app.include_router(alerts_router)
app.include_router(admin_router)
app.include_router(ai_chat_router)
app.include_router(voice_router)

# Compatibility root endpoints for frontend telemetry & load switches
class TelemetryCompat(BaseModel):
    wind_mps: float = 12.0
    lux: float = 350.0
    temp_c: float = -28.0
    battery_kwh: float = 85.0
    gen_kw: float = 0.0
    station_id: str = "ST-01"

@app.post("/api/telemetry")
def telemetry_compat(payload: TelemetryCompat):
    state = DigitalTwin.evaluate_state(
        station_id=payload.station_id,
        wind_mps=payload.wind_mps,
        lux=payload.lux,
        temp_c=payload.temp_c,
        battery_kwh=payload.battery_kwh,
        gen_kw=payload.gen_kw
    )
    return {"ok": True, "state": state}

class ToggleCompat(BaseModel):
    id: str
    station_id: str = "ST-01"

@app.post("/api/loads/toggle")
def toggle_compat(payload: ToggleCompat):
    updated = EnergyService.toggle_load_relay(payload.id, payload.station_id)
    return {"ok": True, "load": updated}

@app.post("/api/loads/reset")
def reset_compat(station_id: str = "ST-01"):
    loads = EnergyService.reset_all_loads(station_id)
    return {"ok": True, "loads": loads}

# Static file serving & frontend routes
FRONTEND_DIR = os.path.join(settings.BASE_DIR, "frontend")

@app.get("/")
def serve_index():
    idx = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(idx):
        return FileResponse(idx)
    return {"status": "online", "message": "Polar Energy AI API Active"}

@app.get("/dashboard")
def serve_dashboard():
    dash = os.path.join(FRONTEND_DIR, "dashboard.html")
    if os.path.exists(dash):
        return FileResponse(dash)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/researcher")
def serve_researcher():
    res = os.path.join(FRONTEND_DIR, "researcher.html")
    if os.path.exists(res):
        return FileResponse(res)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/admin")
def serve_admin():
    adm = os.path.join(FRONTEND_DIR, "admin.html")
    if os.path.exists(adm):
        return FileResponse(adm)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# Mount CSS & JS static directories
if os.path.exists(FRONTEND_DIR):
    css_dir = os.path.join(FRONTEND_DIR, "css")
    js_dir = os.path.join(FRONTEND_DIR, "js")
    if os.path.exists(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
