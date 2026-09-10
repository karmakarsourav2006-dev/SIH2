import re
import json
from typing import Dict, Any, Optional
from backend.llm.ollama_client import OllamaClient

class IntentClassifier:
    """
    Dedicated Structured Intent Classifier for Polar Energy AI.
    Strictly separates intent classification from response generation.
    Never relies on stale state or prior intent outputs.
    """

    INTENTS = [
        "GENERAL_CONVERSATION",
        "SCHEDULE_MODIFICATION_POLICY",
        "GET_CURRENT_ENERGY",
        "GET_BATTERY_STATUS",
        "GET_SCHEDULE",
        "GET_ACTIVITY_DETAILS",
        "GET_ACTIVITY_ENERGY",
        "GET_ACTIVITY_POWER",
        "GET_ENERGY_FORECAST",
        "GET_WEATHER",
        "GET_HEATING_STATUS",
        "GET_ALERTS",
        "GET_ANOMALIES",
        "SIMULATE_SCENARIO",
        "COMPARE_OPTIONS",
        "RECOMMEND_ACTION",
        "CREATE_ACTIVITY",
        "UPDATE_ACTIVITY",
        "DELETE_ACTIVITY",
        "RESCHEDULE_ACTIVITY",
        "RESEARCH_RAG",
        "GET_STATION_STATUS"
    ]

    @classmethod
    def classify(cls, query: str, session: Optional[Any] = None) -> Dict[str, Any]:
        """
        Primary classification entry point.
        Uses the CURRENT user message as the primary signal.
        Returns a structured dictionary:
        {
            "intent": str,
            "entities": dict,
            "requires_tool": bool,
            "selected_tool": str or None,
            "confidence": float
        }
        """
        q = query.lower().strip()

        # Clean polite greetings/prefixes to uncover the core request underneath
        # e.g., "Hello, how much energy do we have?" -> "how much energy do we have?"
        q_core = re.sub(
            r"^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening)|please|can you tell me|could you tell me|tell me|what about|check)\b\s*[,:\-]?\s*",
            "",
            q
        ).strip()

        # 1. GENERAL_CONVERSATION: Identity, Capabilities, Small Talk, Greetings
        # Examples: "Tell me about yourself.", "Who are you?", "What can you do?", "How can you help me?", "Hello"
        if re.search(r"\b(tell me about yourself|about yourself|who are you|what are you|what can you do|your capabilities|how can you help|help me with|introduce yourself)\b", q):
            return {
                "intent": "GENERAL_CONVERSATION",
                "entities": {"topic": "identity"},
                "requires_tool": False,
                "selected_tool": None,
                "confidence": 0.99
            }

        if not q_core or re.search(r"^(hi|hello|hey|greetings|good morning|good afternoon|good evening|thanks|thank you|how are you)\b", q):
            # Only if no other operational question followed
            if not any(kw in q_core for kw in ["battery", "energy", "schedule", "weather", "power", "solar", "wind", "temp", "alert", "drill"]):
                return {
                    "intent": "GENERAL_CONVERSATION",
                    "entities": {"topic": "greeting"},
                    "requires_tool": False,
                    "selected_tool": None,
                    "confidence": 0.95
                }

        # 2. SCHEDULE_MODIFICATION_POLICY: "Can I change the schedule?", "Can we move an experiment?"
        # Distinguish informational vs. modifiability policy vs. actual execution
        if re.search(r"\b(can i change the schedule|can we change the schedule|how to change the schedule|how can i change the schedule|can i reschedule|can we reschedule|can i move the experiment|can we move an experiment|is it possible to reschedule|modify schedule policy)\b", q):
            return {
                "intent": "SCHEDULE_MODIFICATION_POLICY",
                "entities": {"aspect": "policy"},
                "requires_tool": False,
                "selected_tool": None,
                "confidence": 0.98
            }

        # 3. RESEARCH_RAG: Academic literature, research documents, papers
        if re.search(r"\b(research paper|research papers|papers you have|scholar|literature|study|studies|pdf|academic|scientific paper)\b", q):
            return {
                "intent": "RESEARCH_RAG",
                "entities": {"query": query},
                "requires_tool": True,
                "selected_tool": "research_rag",
                "confidence": 0.95
            }

        # 4. SIMULATE_SCENARIO: Hypotheticals BEFORE committing
        if re.search(r"\b(what if|simulate|simulation|hypothetical|could we run|can we run|if we add|if we run|if we turn on|suppose)\b", q):
            return {
                "intent": "SIMULATE_SCENARIO",
                "entities": {"hypothetical": True},
                "requires_tool": True,
                "selected_tool": "simulate_activity_impact",
                "confidence": 0.95
            }

        # 5. ACTUAL ACTIONS: Mutating database activities
        if re.search(r"\b(reschedule|move activity|move experiment|postpone|delay)\b", q) and not re.search(r"\b(can i|can we|how do i)\b", q):
            return {
                "intent": "RESCHEDULE_ACTIVITY",
                "entities": {},
                "requires_tool": True,
                "selected_tool": "reschedule_activity",
                "confidence": 0.95
            }
        if re.search(r"\b(create activity|add activity|new activity|register experiment|schedule new)\b", q):
            return {
                "intent": "CREATE_ACTIVITY",
                "entities": {},
                "requires_tool": True,
                "selected_tool": "create_activity",
                "confidence": 0.95
            }
        if re.search(r"\b(delete activity|remove activity|cancel activity|abort activity)\b", q):
            return {
                "intent": "DELETE_ACTIVITY",
                "entities": {},
                "requires_tool": True,
                "selected_tool": "delete_activity",
                "confidence": 0.95
            }
        if re.search(r"\b(update activity|modify activity|change priority)\b", q):
            return {
                "intent": "UPDATE_ACTIVITY",
                "entities": {},
                "requires_tool": True,
                "selected_tool": "update_activity",
                "confidence": 0.95
            }

        # 6. SPECIFIC ACTIVITY ENERGY / POWER (Only when referring to a specific experiment!)
        has_pronoun = bool(re.search(r"\b(it|this|that|this activity|the activity|the experiment|the drill|the lidar|the radar)\b", q))
        has_specific_experiment = any(exp in q for exp in ["drill", "lidar", "radar", "sounder", "spectrometry", "sounding", "sweep"])

        if (has_pronoun or has_specific_experiment) and re.search(r"\b(how much energy|energy consume|energy consumption|energy require|energy need|energy will it|will it consume)\b", q):
            return {
                "intent": "GET_ACTIVITY_ENERGY",
                "entities": {"target": "active_activity"},
                "requires_tool": True,
                "selected_tool": "get_activity_energy",
                "confidence": 0.92
            }
        if (has_pronoun or has_specific_experiment) and re.search(r"\b(how much power|power draw|continuous power|average power|kw draw|power demand|will it draw)\b", q):
            return {
                "intent": "GET_ACTIVITY_POWER",
                "entities": {"target": "active_activity"},
                "requires_tool": True,
                "selected_tool": "get_activity_power",
                "confidence": 0.92
            }

        # 7. STATION ENERGY & POWER (Station total reserve, available power, renewable generation)
        # Examples: "How much energy do we have?", "What's our energy amount?", "How much energy is available?", "What's the current energy?"
        if re.search(r"\b(how much energy do we have|how much energy is available|what is our energy amount|what's our energy amount|current energy|energy amount|energy do we have|energy available|total energy left|renewable energy|how much power do we have|power generation|generating power|energy reserve)\b", q):
            return {
                "intent": "GET_CURRENT_ENERGY",
                "entities": {"scope": "station"},
                "requires_tool": True,
                "selected_tool": "get_current_energy",
                "confidence": 0.96
            }

        # 8. BATTERY STATUS
        # Examples: "What is the battery level?", "How much battery is available?", "Battery status", "SoC"
        if re.search(r"\b(battery|batteries|soc|state of charge|battery charge|battery level|battery status|how much battery|bess|battery reserve)\b", q):
            return {
                "intent": "GET_BATTERY_STATUS",
                "entities": {"scope": "battery"},
                "requires_tool": True,
                "selected_tool": "get_battery_status",
                "confidence": 0.98
            }

        # 9. SCHEDULE INQUIRY
        # Examples: "What is today's schedule?", "Tell me about the schedule.", "What activities are planned?"
        if re.search(r"\b(schedule|schedules|tell me about the schedule|what is the schedule|what's the schedule|activities planned|experiments planned|operations queue|what is planned|queue)\b", q):
            return {
                "intent": "GET_SCHEDULE",
                "entities": {"scope": "schedule"},
                "requires_tool": True,
                "selected_tool": "get_current_schedule",
                "confidence": 0.98
            }

        # 10. WEATHER & TEMPERATURE
        # Examples: "What is the weather?", "What is the temperature?", "How cold is it?"
        if re.search(r"\b(weather|temperature|temp|cold|blizzard|wind speed|wind velocity|ambient|outside|celsius|degrees|katabatic)\b", q):
            return {
                "intent": "GET_WEATHER",
                "entities": {"scope": "weather"},
                "requires_tool": True,
                "selected_tool": "get_weather_forecast",
                "confidence": 0.98
            }

        # 11. HEATING STATUS
        if re.search(r"\b(heating|heat|heater|thermal|habitat|warmth|hvac|thermal loss|building heat)\b", q):
            return {
                "intent": "GET_HEATING_STATUS",
                "entities": {"scope": "heating"},
                "requires_tool": True,
                "selected_tool": "get_heating_forecast",
                "confidence": 0.95
            }

        # 12. ALERTS, WARNINGS & SAFETY
        if re.search(r"\b(alert|alerts|alarm|alarms|warning|warnings|critical|emergency|danger|safe|safety)\b", q):
            return {
                "intent": "GET_ALERTS",
                "entities": {"scope": "alerts"},
                "requires_tool": True,
                "selected_tool": "get_alerts",
                "confidence": 0.95
            }

        # 13. EQUIPMENT ANOMALIES & FAULTS
        if re.search(r"\b(anomal|fault|faults|surge|abnormal|spike|freeze|frozen|binding|failure)\b", q):
            return {
                "intent": "GET_ANOMALIES",
                "entities": {"scope": "anomalies"},
                "requires_tool": True,
                "selected_tool": "get_anomalies",
                "confidence": 0.95
            }

        # 14. FORECAST / TOMORROW
        if re.search(r"\b(forecast|tomorrow|green window|green windows|future generation|peak solar|peak wind)\b", q):
            if session and session.last_topic == "battery":
                return {
                    "intent": "GET_BATTERY_STATUS",
                    "entities": {"temporal": "tomorrow"},
                    "requires_tool": True,
                    "selected_tool": "get_battery_status",
                    "confidence": 0.85
                }
            return {
                "intent": "GET_ENERGY_FORECAST",
                "entities": {"temporal": "tomorrow"},
                "requires_tool": True,
                "selected_tool": "get_energy_forecast",
                "confidence": 0.95
            }

        # 15. ACTIVITY DETAILS LOOKUP
        if re.search(r"\b(details of|tell me about the activity|tell me about the experiment)\b", q):
            return {
                "intent": "GET_ACTIVITY_DETAILS",
                "entities": {},
                "requires_tool": True,
                "selected_tool": "get_activity",
                "confidence": 0.90
            }

        # 16. OVERALL STATION STATUS
        if re.search(r"\b(station status|system status|microgrid status|how is the station|telemetry|overview|current state|all systems)\b", q):
            return {
                "intent": "GET_STATION_STATUS",
                "entities": {"scope": "station"},
                "requires_tool": True,
                "selected_tool": "get_station_status",
                "confidence": 0.95
            }

        # 17. Structured LLM Classifier Fallback for Ambiguous / Complex Inputs
        llm_classified = cls._classify_with_llm(query)
        if llm_classified:
            return llm_classified

        # Safe Default: General Conversation (Never dump telemetry on unrecognized inputs!)
        return {
            "intent": "GENERAL_CONVERSATION",
            "entities": {"topic": "general"},
            "requires_tool": False,
            "selected_tool": None,
            "confidence": 0.70
        }

    @classmethod
    def _classify_with_llm(cls, query: str) -> Optional[Dict[str, Any]]:
        """Structured JSON classifier utilizing local Ollama."""
        prompt = (
            f"Classify the following query into exactly ONE intent from: {json.dumps(cls.INTENTS)}.\n"
            f"Query: \"{query}\"\n\n"
            f"Output ONLY a valid JSON object matching this schema:\n"
            f'{{"intent": "INTENT_NAME", "requires_tool": true_or_false, "confidence": 0.9}}'
        )
        try:
            raw = OllamaClient.generate(prompt=prompt, format="json", temperature=0.0)
            if not raw:
                return None
            data = json.loads(raw)
            intent = data.get("intent")
            if intent in cls.INTENTS:
                return {
                    "intent": intent,
                    "entities": data.get("entities", {}),
                    "requires_tool": data.get("requires_tool", intent not in ["GENERAL_CONVERSATION", "SCHEDULE_MODIFICATION_POLICY"]),
                    "selected_tool": cls._map_intent_to_tool(intent),
                    "confidence": float(data.get("confidence", 0.85))
                }
        except Exception:
            pass
        return None

    @staticmethod
    def _map_intent_to_tool(intent: str) -> Optional[str]:
        mapping = {
            "GET_CURRENT_ENERGY": "get_current_energy",
            "GET_BATTERY_STATUS": "get_battery_status",
            "GET_SCHEDULE": "get_current_schedule",
            "GET_ACTIVITY_ENERGY": "get_activity_energy",
            "GET_ACTIVITY_POWER": "get_activity_power",
            "GET_WEATHER": "get_weather_forecast",
            "GET_HEATING_STATUS": "get_heating_forecast",
            "GET_ALERTS": "get_alerts",
            "GET_ANOMALIES": "get_anomalies",
            "GET_ENERGY_FORECAST": "get_energy_forecast",
            "SIMULATE_SCENARIO": "simulate_activity_impact",
            "GET_STATION_STATUS": "get_station_status",
            "RESEARCH_RAG": "research_rag"
        }
        return mapping.get(intent)
