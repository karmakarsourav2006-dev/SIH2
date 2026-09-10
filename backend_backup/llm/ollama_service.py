import json
from typing import Dict, Any
from backend.config import settings
from backend.llm.agent_fallback import AgentFallback

class OllamaService:
    """Interfaces with local Ollama LLM if available, falling back to deterministic expert system."""

    @classmethod
    def query(cls, prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            import urllib.request
            url = f"{settings.OLLAMA_URL}/api/generate"
            payload = {
                "model": settings.OLLAMA_MODEL,
                "prompt": f"You are BOREAS AI, the autonomous polar station energy architect. Context: {json.dumps(context or {})}. Query: {prompt}. Give concise operational triage advice.",
                "stream": False
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=1.5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    ans = data.get("response", "")
                    if ans:
                        return {
                            "intent": "LLM_GENERATIVE",
                            "priority": "OPERATIONAL",
                            "explanation": ans.strip(),
                            "actions": ["LLM synthesized recommendations applied."],
                            "voice_text": ans.strip()[:180],
                            "provider": "Ollama"
                        }
        except Exception:
            # Fall back seamlessly
            pass

        result = AgentFallback.answer(prompt, context)
        result["provider"] = "Fallback Rules Engine"
        return result

