import re
import uuid
import datetime
from typing import Dict, Any, List, Optional
from backend.config import settings
from backend.services.ai_tools import AITools
from backend.rag.research_rag import ResearchRAG
from backend.llm.ollama_client import OllamaClient
from backend.llm.agent_fallback import AgentFallback
from backend.llm.intent_classifier import IntentClassifier

class RequestContext:
    """
    Isolated, request-scoped context tracking all parameters for a single query.
    Prevents cross-request variable leaks or state contamination.
    """
    def __init__(self, request_id: str, user_message: str, session_id: str, station_id: str = "ST-01"):
        self.request_id = request_id
        self.user_message = user_message
        self.session_id = session_id
        self.station_id = station_id
        self.detected_intent: str = "GENERAL_CONVERSATION"
        self.entities: Dict[str, Any] = {}
        self.requires_tool: bool = False
        self.selected_tool: Optional[str] = None
        self.tool_arguments: Dict[str, Any] = {}
        self.tool_result: Dict[str, Any] = {}
        self.final_response: str = ""
        self.voice_text: str = ""
        self.rag_included: bool = False

class ConversationSession:
    """Maintains conversational entity references, active topics, and clean history turns."""
    def __init__(self, session_id: str, station_id: str = "ST-01"):
        self.session_id = session_id
        self.station_id = station_id
        self.turns: List[Dict[str, str]] = []
        self.last_activity_id: Optional[str] = None
        self.last_activity_name: Optional[str] = None
        self.last_topic: Optional[str] = None
        self.last_intent: Optional[str] = None
        self.created_at = datetime.datetime.now(datetime.timezone.utc)
        self.updated_at = self.created_at

    def add_turn(self, role: str, content: str):
        self.turns.append({"role": role, "content": content})
        if len(self.turns) > 16:
            self.turns = self.turns[-16:]
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)

class ConversationManager:
    """Multi-turn conversation engine with structured intent routing, request isolation, and tool dispatch."""

    _sessions: Dict[str, ConversationSession] = {}

    @classmethod
    def get_session(cls, session_id: str, station_id: str = "ST-01") -> ConversationSession:
        if session_id not in cls._sessions:
            cls._sessions[session_id] = ConversationSession(session_id, station_id)
        session = cls._sessions[session_id]
        if station_id:
            session.station_id = station_id
        return session

    @classmethod
    def resolve_anaphora(cls, query: str, session: ConversationSession) -> str:
        """
        Resolves references such as 'it', 'that', 'this', 'the experiment', 'tomorrow'.
        Strictly gated: Only resolves activity references if an active activity is tracked.
        """
        resolved = query
        lower_q = query.lower()

        # Activity references (e.g. "how much energy will it consume?")
        if session.last_activity_name:
            pronoun_patterns = [
                r"\b(it|this activity|the activity|this experiment|the experiment|the operation|the previous activity)\b"
            ]
            for pat in pronoun_patterns:
                if re.search(pat, lower_q):
                    resolved = re.sub(pat, f"'{session.last_activity_name}'", resolved, count=1, flags=re.IGNORECASE)
                    break

        # Temporal references
        tomorrow_iso = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        resolved = re.sub(r"\btomorrow\b", f"tomorrow ({tomorrow_iso})", resolved, flags=re.IGNORECASE)
        resolved = re.sub(r"\btoday\b", f"today ({datetime.date.today().strftime('%Y-%m-%d')})", resolved, flags=re.IGNORECASE)

        return resolved

    @classmethod
    def handle_query(
        cls,
        query: str,
        session_id: str = "default_session",
        station_id: str = "ST-01",
        context_override: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main request execution pipeline.
        Creates an isolated RequestContext for every invocation.
        Never reuses previous assistant responses, intents, or tool outputs.
        """
        # Step 1: Initialize fresh, isolated request context
        req_id = request_id or ("req_" + uuid.uuid4().hex[:10])
        req_ctx = RequestContext(
            request_id=req_id,
            user_message=query,
            session_id=session_id,
            station_id=station_id
        )

        session = cls.get_session(session_id, station_id)

        # Step 2: Intent Classification using dedicated IntentClassifier
        # Current user message is the primary signal!
        classified = IntentClassifier.classify(query, session=session)
        req_ctx.detected_intent = classified["intent"]
        req_ctx.entities = classified.get("entities", {})
        req_ctx.requires_tool = classified.get("requires_tool", False)
        req_ctx.selected_tool = classified.get("selected_tool")

        # Step 3: Gated Anaphora Resolution
        # Only substitute activity names if the query is an activity-targeted calculation/simulation
        if req_ctx.detected_intent in ["GET_ACTIVITY_ENERGY", "GET_ACTIVITY_POWER", "SIMULATE_SCENARIO"]:
            resolved_query = cls.resolve_anaphora(query, session)
        else:
            resolved_query = query
        session.add_turn("user", query)

        # Step 4: Tool Selection and Execution (Isolated per request)
        if req_ctx.requires_tool and req_ctx.selected_tool:
            req_ctx.tool_arguments = {"station_id": station_id}

            if req_ctx.selected_tool == "get_current_energy":
                req_ctx.tool_result = AITools.get_current_energy(station_id)
                session.last_topic = "energy"

            elif req_ctx.selected_tool == "get_battery_status":
                req_ctx.tool_result = AITools.get_battery_status(station_id)
                session.last_topic = "battery"

            elif req_ctx.selected_tool == "get_current_schedule":
                sch = AITools.get_current_schedule(station_id)
                req_ctx.tool_result = sch
                session.last_topic = "schedule"
                if sch:
                    session.last_activity_id = sch[0].get("id")
                    session.last_activity_name = sch[0].get("name")

            elif req_ctx.selected_tool == "get_activity_energy":
                act_name = req_ctx.entities.get("activity_name") or session.last_activity_name or resolved_query
                req_ctx.tool_arguments["activity"] = act_name
                req_ctx.tool_result = AITools.get_activity_energy(act_name, station_id)
                session.last_topic = "activity"

            elif req_ctx.selected_tool == "get_activity_power":
                act_name = req_ctx.entities.get("activity_name") or session.last_activity_name or resolved_query
                req_ctx.tool_arguments["activity"] = act_name
                req_ctx.tool_result = AITools.get_activity_power(act_name, station_id)
                session.last_topic = "activity"

            elif req_ctx.selected_tool == "get_weather_forecast":
                req_ctx.tool_result = AITools.get_weather_forecast(station_id)
                session.last_topic = "weather"

            elif req_ctx.selected_tool == "get_heating_forecast":
                req_ctx.tool_result = AITools.get_heating_forecast(station_id)
                session.last_topic = "heating"

            elif req_ctx.selected_tool == "get_alerts":
                req_ctx.tool_result = AITools.get_alerts(station_id)
                session.last_topic = "alerts"

            elif req_ctx.selected_tool == "get_anomalies":
                req_ctx.tool_result = AITools.get_anomalies(station_id)
                session.last_topic = "anomalies"

            elif req_ctx.selected_tool == "get_energy_forecast":
                req_ctx.tool_result = AITools.get_energy_forecast(station_id, hours=24)
                session.last_topic = "forecast"

            elif req_ctx.selected_tool in ("simulate_activity_impact", "simulate_activity"):
                act_name = session.last_activity_name or "High-Power Science Load"
                req_ctx.tool_result = AITools.simulate_activity(station_id=station_id, name=act_name, required_kwh=30.0, duration_hrs=3.0)
                session.last_topic = "simulation"

            elif req_ctx.selected_tool == "get_station_status":
                req_ctx.tool_result = AITools.get_station_status(station_id)
                session.last_topic = "station_status"

            elif req_ctx.selected_tool == "research_rag":
                req_ctx.tool_result = {"query": resolved_query}
                session.last_topic = "research"

        # Step 5: Research RAG retrieval (only for academic research inquiries)
        rag_context = ""
        if req_ctx.detected_intent == "RESEARCH_RAG":
            rag_context = ResearchRAG.format_context_for_prompt(resolved_query, top_k=2)
            req_ctx.rag_included = bool(rag_context)

        # Step 6: Response Generation (Strictly Scoped)
        system_prompt = "Directly answer the question in 1-2 concise sentences using the provided polar station data. State the exact figures. Never repeat canned greetings."
        user_content = f"User Question: {resolved_query}\nDirect Answer:"

        if req_ctx.detected_intent == "GENERAL_CONVERSATION":
            # For identity / capabilities / greetings: NO station tools or telemetry!
            system_prompt = (
                f"You are BOREAS AI, the autonomous energy management copilot for Antarctic Research Station {station_id}. "
                f"Answer the user's question directly in 1-2 professional, concise sentences about your identity or capabilities. "
                f"You monitor live microgrid telemetry, optimize battery storage, forecast solar/wind windows, "
                f"schedule polar research activities, and manage emergency load shedding. Do not recite station telemetry numbers."
            )
            user_content = f"User Question: {resolved_query}\nAnswer directly in 1-2 sentences:"

        elif req_ctx.detected_intent == "SCHEDULE_MODIFICATION_POLICY":
            # Policy explanation: NO station status numbers!
            system_prompt = (
                f"You are BOREAS AI. Explain the schedule modification policy directly in 1-2 sentences: "
                f"Yes, researchers can reschedule or defer Priority 2 and Priority 3 science activities via the Science Schedule console "
                f"or by voice command. Core life-support and habitat heating (Priority 1) are locked and cannot be unscheduled."
            )
            user_content = f"User Question: {resolved_query}\nDirect Answer in 1-2 sentences:"

        elif req_ctx.detected_intent == "GET_CURRENT_ENERGY":
            e = req_ctx.tool_result
            data_str = (
                f"Stored Battery Reserve: {e.get('stored_energy_kwh')} kWh ({e.get('soc_pct')}% SoC), "
                f"Total Generation: {e.get('generation_power_kw')} kW (Solar: {e.get('solar_kw')} kW, Wind: {e.get('wind_kw')} kW), "
                f"Station Demand: {e.get('demand_kw')} kW, Net Flow: {e.get('net_flow_kw')} kW, "
                f"Safe Runtime: {e.get('safe_runtime_hours')} hours."
            )
            user_content = f"Station Energy Data:\n{data_str}\n\nQuestion: {resolved_query}\nDirect Answer in 1-2 sentences:"

        elif req_ctx.detected_intent == "GET_BATTERY_STATUS":
            b = req_ctx.tool_result
            data_str = f"SoC: {b.get('soc_pct')}%, Reserve: {b.get('current_reserve_kwh')} kWh, Capacity: {b.get('capacity_kwh')} kWh, Safe Runway: {b.get('safe_runtime_hours')} hours, Cell Temp: {b.get('cell_temperature_c')}°C."
            user_content = f"Battery Data:\n{data_str}\n\nQuestion: {resolved_query}\nDirect Answer in 1 sentence:"

        elif req_ctx.detected_intent == "GET_SCHEDULE":
            sch = req_ctx.tool_result if isinstance(req_ctx.tool_result, list) else []
            items = [f"- {a.get('name')}: {a.get('required_kwh')} kWh, {a.get('duration_hrs')}h ({a.get('execution_status')})" for a in sch[:3]]
            data_str = "\n".join(items) if items else "No active activities queued."
            user_content = f"Station Operations Schedule:\n{data_str}\n\nQuestion: {resolved_query}\nDirect Answer in 1-2 sentences:"

        elif req_ctx.detected_intent == "GET_ACTIVITY_ENERGY":
            e = req_ctx.tool_result
            data_str = f"Activity '{e.get('name', 'Requested Activity')}' requires {e.get('required_kwh')} kWh (runtime: {e.get('duration_hrs')} hours)."
            user_content = f"Activity Energy Data:\n{data_str}\n\nQuestion: {resolved_query}\nDirect Answer in 1-2 sentences:"

        elif req_ctx.detected_intent == "GET_ACTIVITY_POWER":
            p = req_ctx.tool_result
            data_str = f"Activity '{p.get('name', 'Requested Activity')}' draws an average continuous power of {p.get('continuous_power_kw')} kW ({p.get('required_kwh')} kWh over {p.get('duration_hrs')}h)."
            user_content = f"Activity Power Data:\n{data_str}\n\nQuestion: {resolved_query}\nDirect Answer in 1-2 sentences:"

        elif req_ctx.detected_intent == "GET_WEATHER":
            w = req_ctx.tool_result
            data_str = f"Temperature: {w.get('temp_c')}°C, Wind: {w.get('wind_mps')} m/s ({w.get('wind_knots')} knots), Solar Irradiance: {w.get('lux')} Lux. Advisory: {w.get('advisory')}."
            user_content = f"Polar Weather Telemetry:\n{data_str}\n\nQuestion: {resolved_query}\nDirect Answer in 1 sentence:"

        elif req_ctx.detected_intent == "GET_ENERGY_FORECAST":
            f = req_ctx.tool_result
            data_str = f"24-hour forecast identifies {f.get('green_windows_count')} green renewable surplus windows with peak solar and wind generation."
            user_content = f"Energy Forecast Data:\n{data_str}\n\nQuestion: {resolved_query}\nDirect Answer in 1-2 sentences:"

        elif req_ctx.detected_intent == "GET_HEATING_STATUS":
            h = req_ctx.tool_result
            data_str = f"Habitat Heating Demand: {h.get('thermal_heating_kw')} kW, Outdoor Temp: {h.get('ambient_temp_c')}°C, Heat Loss: {h.get('thermal_loss_kw')} kW, Status: {h.get('heating_status')}."
            user_content = f"Heating Telemetry:\n{data_str}\n\nQuestion: {resolved_query}\nDirect Answer in 1 sentence:"

        elif req_ctx.detected_intent == "GET_ALERTS":
            al = req_ctx.tool_result
            items = [f"- [{a.get('severity')}] {a.get('message')}" for a in al] if isinstance(al, list) else []
            data_str = "\n".join(items) if items else "Zero active emergency alerts. All microgrid systems nominal."
            user_content = f"Station Alerts Report:\n{data_str}\n\nQuestion: {resolved_query}\nDirect Answer in 1-2 sentences:"

        elif req_ctx.detected_intent == "GET_ANOMALIES":
            anom = req_ctx.tool_result if isinstance(req_ctx.tool_result, list) else []
            if anom:
                items = [f"- {a.get('name')}: +{a.get('surge_pct')}% surge ({a.get('fault_type')})" for a in anom]
                data_str = "\n".join(items)
            else:
                data_str = "All equipment nominal. Zero electrical surge anomalies detected."
            user_content = f"Equipment Anomaly Report:\n{data_str}\n\nQuestion: {resolved_query}\nDirect Answer in 1-2 sentences:"

        elif req_ctx.detected_intent == "SIMULATE_SCENARIO":
            sim = req_ctx.tool_result
            data_str = f"Operation '{sim.get('name')}' ({sim.get('required_kwh')} kWh) adds {sim.get('added_power_kw')} kW continuous draw. Projected safe runway: {sim.get('projected_safe_runway_hours')} hrs. Recommendation: {sim.get('recommendation')}."
            user_content = f"Simulation Results:\n{data_str}\n\nQuestion: {resolved_query}\nDirect Answer in 1-2 sentences:"

        elif req_ctx.detected_intent == "RESEARCH_RAG":
            system_prompt = f"Summarize the retrieved academic research literature on polar microgrids in 2-3 concise sentences."
            user_content = f"Retrieved Literature:\n{rag_context}\n\nQuestion: {resolved_query}\nSummary:"

        elif req_ctx.detected_intent == "GET_STATION_STATUS":
            st = req_ctx.tool_result
            gen = st.get("generation", {})
            data_str = (
                f"Station: {st.get('station_name')}, Mode: {st.get('mode')}, "
                f"Battery: {st.get('battery_kwh')} kWh ({st.get('soc_pct')}%), "
                f"Solar Generation: {gen.get('solar_kw', 0)} kW, "
                f"Wind Generation: {gen.get('wind_kw', 0)} kW, "
                f"Total Generation: {gen.get('total_generation_kw', 0)} kW, "
                f"Active Demand: {st.get('demand', {}).get('active_demand_kw')} kW, "
                f"Net Flow: {st.get('net_flow_kw')} kW, "
                f"Safe Runway: {st.get('survivability', {}).get('safe_runtime_hours')} hrs."
            )
            user_content = f"Live Station Telemetry:\n{data_str}\n\nQuestion: {resolved_query}\nDirect Answer in 1-2 sentences:"

        # Only pass conversation history if BOTH conditions are satisfied:
        # 1. The current query is actually detected as a follow-up.
        # 2. The detected intent genuinely requires conversational history.
        # Never leak previous turns into standalone intents like GENERAL_CONVERSATION,
        # SCHEDULE_MODIFICATION_POLICY, GET_WEATHER, GET_BATTERY_STATUS, or GET_CURRENT_ENERGY!
        STANDALONE_INTENTS = {
            "GENERAL_CONVERSATION",
            "SCHEDULE_MODIFICATION_POLICY",
            "GET_WEATHER",
            "GET_BATTERY_STATUS",
            "GET_CURRENT_ENERGY",
        }
        intent_requires_history = req_ctx.detected_intent not in STANDALONE_INTENTS

        messages = [{"role": "system", "content": system_prompt}]
        is_follow_up = bool(re.search(r"\b(it|this|that|tomorrow|and what about|how about|also)\b", query.lower()))
        should_include_history = is_follow_up and intent_requires_history

        if should_include_history and len(session.turns) > 1:
            for turn in session.turns[-3:-1]:
                messages.append({"role": turn["role"], "content": turn["content"][:150]})
        messages.append({"role": "user", "content": user_content})

        # Step 7: Call local Ollama LLM
        llm_response = OllamaClient.chat(messages=messages, temperature=0.1)
        provider = f"Ollama Local ({settings.OLLAMA_MODEL})"

        if not llm_response:
            fallback = AgentFallback.answer(resolved_query, req_ctx.tool_result)
            llm_response = fallback.get("explanation", "Operational telemetry analyzed.")
            provider = "Deterministic Rule Supervisor"

        req_ctx.final_response = llm_response.strip()

        # Voice text: first sentence under 180 characters (preserves decimals like 53.1% or 16.5 kW)
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', req_ctx.final_response) if s.strip()]
        first_sentence = sentences[0] if sentences else req_ctx.final_response
        voice_summary = re.sub(r"[*#_`~]", "", first_sentence).strip()
        if not voice_summary.endswith((".", "!", "?")):
            voice_summary += "."
        if len(voice_summary) > 180:
            voice_summary = voice_summary[:177] + "..."
        req_ctx.voice_text = voice_summary

        session.add_turn("assistant", req_ctx.final_response)
        session.last_intent = req_ctx.detected_intent

        # Step 8: Debug Logging
        print(f"[DEBUG PIPELINE] request_id={req_ctx.request_id} | user_message='{req_ctx.user_message}' | detected_intent={req_ctx.detected_intent} | selected_tool={req_ctx.selected_tool} | tool_arguments={req_ctx.tool_arguments} | final_response='{req_ctx.final_response}'")

        return {
            "ok": True,
            "request_id": req_ctx.request_id,
            "session_id": session_id,
            "station_id": station_id,
            "intent": req_ctx.detected_intent,
            "resolved_query": resolved_query,
            "explanation": req_ctx.final_response,
            "voice_text": req_ctx.voice_text,
            "provider": provider,
            "tool_results": req_ctx.tool_result,
            "rag_included": req_ctx.rag_included
        }
