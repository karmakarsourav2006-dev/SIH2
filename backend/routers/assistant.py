from fastapi import APIRouter
from backend.models import AssistantQueryInput
from backend.database import get_db
from backend.llm.ollama_service import OllamaService
from backend.services.digital_twin import DigitalTwin

router = APIRouter(prefix="/api/assistant", tags=["Voice & Operational AI Advisor"])

@router.post("/query")
def process_assistant_query(payload: AssistantQueryInput):
    query = (payload.query or "").strip()
    station_id = "ST-01"

    # Evaluate dynamic microgrid context
    state = DigitalTwin.evaluate_state(station_id=station_id)
    context = {
        "station_id": station_id,
        "station_name": state.get("station", {}).get("name", "Maitri Station"),
        "mode": state["mode"],
        "is_critical": state["is_critical"],
        "soc_pct": state["soc_pct"],
        "net_flow_kw": state["net_flow_kw"],
        "safe_runtime_hours": state["survivability"]["safe_runtime_hours"],
        "p1_isolated_hours": state["survivability"]["p1_isolated_hours"],
        "anomalies": len(state["anomalies"])
    }

    resp = OllamaService.query(query, context)
    return {
        "ok": True,
        "query": query,
        "category": resp.get("intent", "OPERATIONAL_INQUIRY"),
        "triage_priority": resp.get("priority", "ADVISORY"),
        "explanation": resp.get("explanation", ""),
        "actions_taken": resp.get("actions", []),
        "voice_script": resp.get("voice_text", resp.get("explanation", ""))
    }

