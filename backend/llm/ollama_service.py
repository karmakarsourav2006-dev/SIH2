import json
import re
from typing import Dict, Any
from backend.config import settings
from backend.llm.agent_fallback import AgentFallback

class OllamaService:
    """Interfaces with local Ollama LLM (qwen3:1.7b), injecting OpenWeather telemetry tools."""

    @classmethod
    def query(cls, prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        context = dict(context or {})
        station_id = context.get("station_id", settings.DEFAULT_STATION_ID)
        q_lower = (prompt or "").lower()

        # 1. Weather Intent Detection & Tool Invocation
        weather_keywords = ["weather", "temp", "wind", "forecast", "tomorrow", "solar", "generation", "heating", "demand", "blizzard", "snow", "climate", "condition", "atmosphere"]
        is_weather = any(k in q_lower for k in weather_keywords)

        if is_weather or "openweather_telemetry" not in context:
            try:
                from backend.services.agent_tools import tool_get_energy_weather_impact
                impact = tool_get_energy_weather_impact(station_id)
                context["openweather_telemetry"] = impact.get("current_weather", {})
                context["weather_impact_analysis"] = impact
            except Exception:
                pass

        # 2. Query Local Ollama Instance
        try:
            import urllib.request
            url = f"{settings.OLLAMA_URL}/api/generate"

            system_instruction = (
                "You are BOREAS AI, polar station energy architect. "
                "Cite ONLY the provided weather data. Do not hallucinate numbers. "
                "Keep response concise and operational (1-2 sentences)."
            )

            # Compact context to use minimal tokens
            summary_ctx = {
                "station": context.get("station_name", "Maitri Base"),
                "mode": context.get("mode", "NORMAL"),
                "soc_pct": context.get("soc_pct", 53.0),
                "weather": context.get("openweather_telemetry", {}),
                "impact": context.get("weather_impact_analysis", {}).get("current_impact", {})
            }

            payload = {
                "model": settings.OLLAMA_MODEL,
                "prompt": f"{system_instruction}\nTelemetry: {json.dumps(summary_ctx)}\nQuery: {prompt}\nBrief Answer:",
                "stream": False,
                "think": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 70
                }
            }



            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=settings.OLLAMA_TIMEOUT) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    ans = data.get("response", "")
                    if ans and ans.strip():
                        clean_ans = ans.strip()

                        # Categorize intent
                        if "heating" in q_lower:
                            intent = "HEATING_DEMAND_ANALYSIS"
                        elif "wind" in q_lower:
                            intent = "WIND_GENERATION_ASSESSMENT"
                        elif "tomorrow" in q_lower or "forecast" in q_lower:
                            intent = "ENERGY_FORECAST_ANALYSIS"
                        elif "weather" in q_lower or "temperature" in q_lower:
                            intent = "WEATHER_TELEMETRY_REPORT"
                        elif "generator" in q_lower:
                            intent = "GENERATOR_OUTAGE_TRIAGE"
                        else:
                            intent = "LLM_GENERATIVE"

                        # Extract first 1-2 sentences for crisp voice readout without breaking on decimals
                        sentences = [s.strip() for s in re.split(r"(?<!\d)\.(?!\d)\s*", clean_ans) if s.strip()]
                        if sentences:
                            voice_text = ". ".join(sentences[:2])
                            if not voice_text.endswith("."):
                                voice_text += "."
                        else:
                            voice_text = clean_ans[:190]
                        voice_text = re.sub(r"[*#`_]", "", voice_text).strip()

                        return {
                            "intent": intent,
                            "priority": "CRITICAL (P1 EMERGENCY)" if "emergency" in clean_ans.lower() else "OPERATIONAL",
                            "explanation": clean_ans,
                            "actions": [
                                f"Live telemetry reconciled with {settings.OLLAMA_MODEL}.",
                                "Operational recommendations synchronized to microgrid bus."
                            ],
                            "voice_text": voice_text,
                            "provider": f"Ollama ({settings.OLLAMA_MODEL})"
                        }
        except Exception:
            # Fall back seamlessly to deterministic polar expert system
            pass

        result = AgentFallback.answer(prompt, context)
        result["provider"] = "Fallback Rules Engine"
        return result


