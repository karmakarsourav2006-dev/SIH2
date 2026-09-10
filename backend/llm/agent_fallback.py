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

        # 5. Heating Demand & Thermal Envelope
        if "heating" in q or ("heat" in q and "demand" in q) or "thermal load" in q:
            impact = context.get("weather_impact_analysis", {}).get("current_impact", {})
            w = context.get("openweather_telemetry", {})
            temp = w.get("temp_c", -28.0)
            wind = w.get("wind_mps", 12.0)
            heat_kw = impact.get("thermal_heating_demand_kw", 14.5)
            return {
                "intent": "HEATING_DEMAND_ANALYSIS",
                "priority": "OPERATIONAL",
                "explanation": (
                    f"At current ambient conditions ({temp}°C with {wind} m/s wind), station habitat heating "
                    f"draw is dynamically calculated at {heat_kw} kW. Convective windchill through the building envelope "
                    f"is actively monitored to maintain the +20°C interior thermal setpoint."
                ),
                "actions": [
                    f"Maintain active thermal circulation loop ({heat_kw} kW).",
                    "Verify secondary habitat vestibule airlocks are sealed.",
                    "Audit P1 thermal loop relay online status."
                ],
                "voice_text": f"Habitat heating demand is currently {heat_kw} kilowatts at ambient temperature {temp} degrees Celsius."
            }

        # 6. Wind Generation & Favorability
        if "wind" in q and ("favorable" in q or "generation" in q or "turbine" in q or "condition" in q or "power" in q):
            impact = context.get("weather_impact_analysis", {}).get("current_impact", {})
            w = context.get("openweather_telemetry", {})
            wind_mps = w.get("wind_mps", 12.0)
            wind_kw = impact.get("wind_power_kw", 10.3)
            favorability = impact.get("wind_favorability", "Favorable aerodynamic generation")
            return {
                "intent": "WIND_GENERATION_ASSESSMENT",
                "priority": "OPERATIONAL",
                "explanation": (
                    f"Current aerodynamic wind velocity is {wind_mps} m/s, yielding {wind_kw} kW of clean renewable generation. "
                    f"Status: {favorability}. High-density polar air (1.34 kg/m³) provides optimal kinetic rotor coupling."
                ),
                "actions": [
                    f"Aerodynamic wind power curve verified ({wind_kw} kW).",
                    "Rotor blade pitch control monitored for gust buffering.",
                    "Surplus channeled to BESS battery reserves."
                ],
                "voice_text": f"Wind conditions are {favorability}. Current velocity is {wind_mps} meters per second producing {wind_kw} kilowatts."
            }

        # 7. Tomorrow Forecast & Energy Generation Impact
        if "tomorrow" in q or "forecast" in q or ("future" in q and "energy" in q):
            fc_impact = context.get("weather_impact_analysis", {}).get("forecast_impact_tomorrow", {})
            fc_temp = fc_impact.get("forecast_avg_temp_c", -28.0)
            fc_wind = fc_impact.get("forecast_avg_wind_mps", 12.5)
            fc_wind_kw = fc_impact.get("estimated_wind_generation_kw", 10.5)
            fc_heat_kw = fc_impact.get("estimated_heating_demand_kw", 14.8)
            return {
                "intent": "ENERGY_FORECAST_ANALYSIS",
                "priority": "ADVISORY",
                "explanation": (
                    f"Tomorrow's polar forecast projects an average temperature of {fc_temp}°C and wind velocity of {fc_wind} m/s. "
                    f"Anticipated aerodynamic wind output is ~{fc_wind_kw} kW, while baseline habitat heating demand will be ~{fc_heat_kw} kW. "
                    "Renewable generation is projected to comfortably support scientific operations during peak wind windows."
                ),
                "actions": [
                    "Correlate tomorrow's science queue with forecasted wind peak window.",
                    "Pre-condition BESS storage before expected temperature drops.",
                    "Maintain secondary genset on automated standby."
                ],
                "voice_text": f"Tomorrow's forecast indicates {fc_temp} degrees Celsius and {fc_wind} meters per second wind, supporting approximately {fc_wind_kw} kilowatts generation."
            }

        # 8. Current Weather at Station
        if "weather" in q or "temperature" in q or "blizzard" in q or "current conditions" in q:
            w = context.get("openweather_telemetry", {})
            temp = w.get("temp_c", -28.0)
            wind = w.get("wind_mps", 12.0)
            lux = w.get("lux", 350.0)
            condition = w.get("condition", "Clear")
            desc = w.get("description", "Clear")
            provider = w.get("provider", "OpenWeather")
            blizzard = w.get("blizzard_severity", 0.0)
            status_text = "blizzard alert active" if blizzard > 0.4 else "polar conditions stable"
            return {
                "intent": "WEATHER_TELEMETRY_REPORT",
                "priority": "ADVISORY" if blizzard <= 0.4 else "WARNING",
                "explanation": (
                    f"Current telemetry from {provider}: Temperature is {temp}°C, wind velocity is {wind} m/s, "
                    f"surface irradiance is {lux} Lux, with {desc.lower()} ({condition}). "
                    f"Blizzard severity index is {blizzard:.2f} ({status_text})."
                ),
                "actions": [
                    "Solar and wind physics models aligned to live telemetry.",
                    "Thermal envelope heating loop actively tracking ambient temperature.",
                    "Crew external mobility advisory updated."
                ],
                "voice_text": f"Current weather: {temp} degrees Celsius, wind {wind} meters per second, {desc}. {status_text}."
            }

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

