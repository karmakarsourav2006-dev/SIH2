from backend.api.stations import router as stations_router
from backend.api.weather import router as weather_router
from backend.api.emergency import router as emergency_router
from backend.api.optimization import router as optimization_router
from backend.api.simulation import router as simulation_router
from backend.api.forecasting import router as forecasting_router
from backend.api.activities import router as activities_router
from backend.api.alerts import router as alerts_router
from backend.api.admin import router as admin_router
from backend.api.ai_chat import router as ai_chat_router
from backend.api.voice import router as voice_router

__all__ = [
    "stations_router",
    "weather_router",
    "emergency_router",
    "optimization_router",
    "simulation_router",
    "forecasting_router",
    "activities_router",
    "alerts_router",
    "admin_router",
    "ai_chat_router",
    "voice_router"
]

