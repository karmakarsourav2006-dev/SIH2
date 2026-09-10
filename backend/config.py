import os
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load .env if present in root or backend dir
def _load_env_file():
    for candidate in [os.path.join(BASE_DIR, ".env"), os.path.join(BASE_DIR, "backend", ".env")]:
        if os.path.exists(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

_load_env_file()

DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "polar_station.db"))

class Settings(BaseModel):
    BASE_DIR: str = BASE_DIR
    APP_NAME: str = "Polar Energy AI - Mission Operations"
    VERSION: str = "2.0.0"
    DEBUG: bool = True
    DB_PATH: str = DB_PATH
    HOST: str = os.environ.get("HOST", "127.0.0.1")
    PORT: int = int(os.environ.get("PORT", 8000))

    # Ollama LLM Configuration
    OLLAMA_URL: str = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.environ.get("OLLAMA_MODEL", "qwen3:1.7b")
    OLLAMA_TIMEOUT: float = float(os.environ.get("OLLAMA_TIMEOUT", "60.0"))

    # Weather Provider Configuration
    WEATHER_PROVIDER: str = os.environ.get("WEATHER_PROVIDER", "openweather")
    OPENWEATHER_API_KEY: str = os.environ.get("OPENWEATHER_API_KEY", "")
    OPENWEATHER_BASE_URL: str = os.environ.get("OPENWEATHER_BASE_URL", "https://api.openweathermap.org/data/2.5")
    WEATHER_CACHE_TTL_SECONDS: int = int(os.environ.get("WEATHER_CACHE_TTL_SECONDS", "600"))

    # Station Default Geocoordinates (Maitri Base: -70.7661, 11.7322)
    DEFAULT_STATION_ID: str = os.environ.get("DEFAULT_STATION_ID", "ST-01")
    DEFAULT_STATION_LAT: float = float(os.environ.get("STATION_LAT", "-70.7661"))
    DEFAULT_STATION_LON: float = float(os.environ.get("STATION_LON", "11.7322"))

    # Polar Grid Constants
    NOMINAL_BESS_CAPACITY_KWH: float = 160.0
    MIN_SURVIVAL_SOC_PCT: float = 20.0
    NET_DEFICIT_THRESHOLD_KW: float = -12.0
    MAX_SURGE_RATIO: float = 1.25

settings = Settings()

