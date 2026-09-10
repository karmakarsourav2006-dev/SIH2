from typing import List, Dict, Any

FAULT_CLASSIFICATIONS = {
    "Cryogenic Spectrometry Unit": {
        "fault_type": "COMPRESSOR_VALVE_FREEZE",
        "description": "Sub-zero refrigerant crystallization and valve sticking causing continuous inductive stator overdraw.",
        "urgency": "HIGH",
        "action": "Initiate automated hot-gas bypass cycle or manual thermal heater jacket."
    },
    "Ice-Core Sub-Surface Thermal Drill": {
        "fault_type": "MECHANICAL_BOREHOLE_BINDING",
        "description": "Drill bit slush compaction or motor gearbox cold-bearing friction.",
        "urgency": "MEDIUM",
        "action": "Reverse rotation cycle and check glycol circulation."
    },
    "Habitat Life-Support & Thermal Loop": {
        "fault_type": "HEATING_ELEMENT_SHORT",
        "description": "High-draw electrical resistance element breakdown or pump cavitation.",
        "urgency": "CRITICAL",
        "action": "Switch to redundant backup thermal circulation loop."
    },
    "Medical Station & Emergency Telemetry": {
        "fault_type": "AUTOCLAVE_COIL_LEAKAGE",
        "description": "Sterilization autoclave heater isolation breakdown.",
        "urgency": "HIGH",
        "action": "Isolate medical sterilization branch to protect telemetry."
    },
    "Auxiliary Drone Bay & Snow-Rover Recharger": {
        "fault_type": "DC_RECTIFIER_THERMAL_RUNAWAY",
        "description": "Battery bank charger DC-DC bus ripple and diode leakage.",
        "urgency": "LOW",
        "action": "Reduce fast-charge rate from 60A to 25A."
    }
}

class AnomalyDetector:
    """Signature-based polar equipment anomaly and electrical fault classifier."""

    @staticmethod
    def audit_loads(loads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        anomalies = []

        for load in loads:
            nominal = float(load.get("nominal_kw", 0.0))
            live = float(load.get("live_kw", 0.0))
            status = str(load.get("status", "")).upper()

            if nominal <= 0.0:
                continue

            # >25% above baseline (1.25x)
            surge_ratio = live / nominal
            excess_kw = round(max(0.0, live - nominal), 2)
            surge_pct = round((surge_ratio - 1.0) * 100.0, 1)

            is_surge = surge_ratio > 1.25
            load["is_surge"] = is_surge
            load["excess_kw"] = excess_kw
            load["surge_pct"] = surge_pct

            if is_surge and status == "ONLINE":
                name = load.get("name", "Unknown Subsystem")
                fault_info = FAULT_CLASSIFICATIONS.get(name, {
                    "fault_type": "ELECTROMECHANICAL_FRICTION",
                    "description": "Extreme sub-zero cold-grease viscosity breakdown and phase imbalance.",
                    "urgency": "MEDIUM",
                    "action": "Inspect electrical terminals and apply pre-heaters."
                })

                wasted_kwh_per_hr = round(excess_kw * 1.0, 2)

                anomalies.append({
                    "load_id": load.get("id"),
                    "name": name,
                    "priority": load.get("priority"),
                    "nominal_kw": nominal,
                    "live_kw": live,
                    "excess_kw": excess_kw,
                    "surge_pct": surge_pct,
                    "wasted_kwh_per_hr": wasted_kwh_per_hr,
                    "fault_type": fault_info["fault_type"],
                    "description": fault_info["description"],
                    "urgency": fault_info["urgency"],
                    "recommended_action": fault_info["action"]
                })

        return anomalies

