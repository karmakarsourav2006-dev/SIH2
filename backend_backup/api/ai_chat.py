from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from backend.llm.ollama_service import OllamaService
from backend.services.digital_twin import DigitalTwin

router = APIRouter(prefix="/api/ai_chat", tags=["AI Operational Assistant"])

class ChatMessage(BaseModel):
    query: str
    station_id: Optional[str] = "ST-01"

@router.post("")
def chat_with_agent(msg: ChatMessage):
    # Retrieve current microgrid context
    state = DigitalTwin.evaluate_state(station_id=msg.station_id)
    context = {
        "mode": state["mode"],
        "is_critical": state["is_critical"],
        "soc_pct": state["soc_pct"],
        "net_flow_kw": state["net_flow_kw"],
        "safe_runtime_hours": state["survivability"]["safe_runtime_hours"],
        "p1_isolated_hours": state["survivability"]["p1_isolated_hours"],
        "anomalies": len(state["anomalies"])
    }

    response = OllamaService.query(msg.query, context)
    return {"ok": True, "response": response}

