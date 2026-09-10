from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from backend.llm.conversation_manager import ConversationManager
from backend.llm.ollama_client import OllamaClient
from backend.rag.research_rag import ResearchRAG

router = APIRouter(prefix="/api/ai_chat", tags=["AI Operational Assistant"])

class ChatMessage(BaseModel):
    query: str
    station_id: Optional[str] = "ST-01"
    session_id: Optional[str] = "default_session"
    context: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None

@router.get("/health")
def ai_health():
    """Returns local Ollama engine status, loaded models, and RAG index status."""
    ollama_info = OllamaClient.check_health()
    rag_count = len(ResearchRAG._chunks)
    return {
        "ok": True,
        "ollama": ollama_info,
        "rag_indexed_chunks": rag_count,
        "active_station": "ST-01"
    }

@router.post("")
def chat_with_agent(msg: ChatMessage):
    """Multi-turn conversation endpoint with context awareness, tool calling, and RAG."""
    result = ConversationManager.handle_query(
        query=msg.query,
        session_id=msg.session_id or "default_session",
        station_id=msg.station_id or "ST-01",
        context_override=msg.context,
        request_id=msg.request_id
    )

    # Compatible envelope for existing frontend scripts
    return {
        "ok": True,
        "request_id": result.get("request_id"),
        "response": {
            "intent": result.get("intent", "OPERATIONAL"),
            "resolved_query": result.get("resolved_query", msg.query),
            "explanation": result.get("explanation", ""),
            "voice_text": result.get("voice_text", ""),
            "provider": result.get("provider", "Local Assistant"),
            "actions": [f"Intent resolved: {result.get('intent')}"],
            "rag_included": result.get("rag_included", False),
            "tool_results": result.get("tool_results", {})
        }
    }

