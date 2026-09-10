import os
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "polar_station.db"))

class Settings(BaseModel):
    BASE_DIR: str = BASE_DIR
    APP_NAME: str = "Polar Energy AI - Mission Operations"
    VERSION: str = "2.0.0"
    DEBUG: bool = True
    DB_PATH: str = DB_PATH
    HOST: str = os.environ.get("HOST", "127.0.0.1")
    PORT: int = int(os.environ.get("PORT", 8000))
    OLLAMA_URL: str = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
    OLLAMA_MODEL: str = os.environ.get("OLLAMA_MODEL", "gemma3:270m")
    OLLAMA_FALLBACK_MODEL: str = os.environ.get("OLLAMA_FALLBACK_MODEL", "llama3.2:latest")
    OLLAMA_EMBED_MODEL: str = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    OLLAMA_TIMEOUT: float = float(os.environ.get("OLLAMA_TIMEOUT", "15.0"))
    RESEARCH_DIR: str = os.environ.get("RESEARCH_DIR", os.path.join(BASE_DIR, "backend", "research_docs"))

    # Polar Grid Constants
    NOMINAL_BESS_CAPACITY_KWH: float = 160.0
    MIN_SURVIVAL_SOC_PCT: float = 20.0
    NET_DEFICIT_THRESHOLD_KW: float = -12.0
    MAX_SURGE_RATIO: float = 1.25

settings = Settings()

