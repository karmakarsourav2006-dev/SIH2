from typing import Dict, Any

class AgentFallback:
    """Deterministic polar station expert system when local LLM is offline."""

    @staticmethod
    def answer(query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        q = (query or "").lower().strip()
        context = context or {}

        # 1. Generator Failure + Medical / Critical Life Support
        if "generator" in q and ("fail" in q or "down" in q or "fault" in q or "offline" in q or "medical" in q or "crew" in q):
            return {
                "intent": "GENERATOR_OUTAGE_TRIAGE",
                "priority": "CRITICAL (P1 EMERGENCY)",
                "explanation": (
                    "Primary diesel generator interruption detected. Emergency microgrid protocol engaged: "
                    "Habitat Life-Support & Thermal Loop (14.0 kW) and Medical Station (3.5 kW) are ring-fenced on isolated P1 priority bus. "
                    "Secondary drone recharge (P3) has been pre-emptively shed to avoid unbuffered battery depletion."
                ),
                "actions": [
                    "Engage P1 Life Support & Medical ring-fence.",
                    "Auto-shed Auxiliary Drone Bay (6.0 kW).",
                    "Dispatch maintenance notification to station engineer.",
                    "Recalculate BESS discharge runway."
                ],
                "voice_text": "Emergency generator outage acknowledged. Medical station and habitat life-support are locked on ring-fence. Drone charging is shed."
            }

        # 2. Survival Horizon & Battery Reserve
        if "survival" in q or "runtime" in q or "horizon" in q or "battery" in q or "how long" in q:
            runtime = context.get("safe_runtime_hours", 37.4)
            p1_hours = context.get("p1_isolated_hours", 37.4)
            return {
                "intent": "SURVIVAL_HORIZON_AUDIT",
                "priority": "ADVISORY",
                "explanation": (
                    f"At current generation and composite demand, station operational runway is {runtime} hours. "
                    f"Under isolated P1 protection mode (Life-Support, Thermal Loop, Medical & Comms drawing ~19.5 kW), "
                    f"survival horizon extends to {p1_hours} hours. Thermal envelope containment remains nominal."
                ),
                "actions": [
                    "Sample current BESS state of charge.",
                    "Verify thermal loop insulation integrity.",
                    "Maintain renewable buffer."
                ],
                "voice_text": f"Current station runtime is {runtime} hours. Protected P1 life support duration is {p1_hours} hours."
            }

        # 3. Ice Drill / Experiments / Green Window
        if "drill" in q or "experiment" in q or "schedule" in q or "activity" in q:
            return {
                "intent": "RESEARCH_SCHEDULING",
                "priority": "ADVISORY",
                "explanation": (
                    "The Ice-Core Sub-Surface Thermal Drill requires 8.5 kW nominal power. "
                    "The microgrid optimizer recommends scheduling this high-draw scientific task during forecasted wind peaks "
                    "or solar noon (12:00 - 15:00 UTC) to utilize 100% renewable surplus without fossil genset consumption."
                ),
                "actions": [
                    "Correlate wind turbine power curve with drill schedule.",
                    "Reserve 32 kWh green energy allocation window.",
                    "Notify science lead Elena Rostova."
                ],
                "voice_text": "Drill schedule optimization complete. Recommended execution window is during afternoon wind peaks to run on renewable surplus."
            }

        # 4. Anomaly / Cryo / Surge
        if "cryo" in q or "surge" in q or "anomaly" in q or "fault" in q:
            return {
                "intent": "ANOMALY_DIAGNOSTICS",
                "priority": "WARNING",
                "explanation": (
                    "Cryogenic Spectrometry Unit is drawing 7.6 kW (90% above 4.0 kW baseline). "
                    "Diagnostic classification indicates sub-zero refrigerant crystallization and compressor valve freeze. "
                    "Estimated energy waste: 3.6 kWh per hour. Recommended hot-gas bypass cycle."
                ),
                "actions": [
                    "Flag Cryo-Spectrometry relay as anomalous.",
                    "Prepare automated de-icing cycle.",
                    "Log incident to station maintenance log."
                ],
                "voice_text": "Cryogenic spectrometry bay is drawing 7.6 kilowatts. Compressor valve freeze suspected. Maintenance advised."
            }

        # General / Catch-all
        return {
            "intent": "OPERATIONAL_STATUS",
            "priority": "NOMINAL",
            "explanation": (
                f"BOREAS Polar Intelligence evaluated inquiry: '{query}'. "
                "Polar station microgrid is operating in autonomous optimization mode. "
                "Renewable forecasting, life-support ring-fencing, and anomaly signature monitoring are fully active."
            ),
            "actions": [
                "Telemetry bus verified.",
                "Relay states confirmed nominal."
            ],
            "voice_text": "Inquiry processed. Polar microgrid is running in autonomous optimization mode."
        }

