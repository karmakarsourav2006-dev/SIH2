from typing import List, Dict, Any

CAUSE_CATALOG = {
    "Cryogenic Spectrometry Unit": "Cryo-compressor valve freeze & mechanical bearing friction causing excessive inductive current draw.",
    "Ice-Core Sub-Surface Thermal Drill": "High-resistance borehole binding or drill motor thermal runaway.",
    "Habitat Life-Support & Thermal Loop": "Heat exchanger pump cavitation or heating element insulation degradation.",
    "Medical Station & Emergency Telemetry": "Autoclave power supply coil leakage or battery backup fault.",
    "Auxiliary Drone Bay & Snow-Rover Recharger": "Fast-charge DC rectifier imbalance or battery pack cell short.",
    "Satellite Comms & Emergency Beacon": "RF power amplifier thermal overload or radome de-icing heater short."
}

def detect_anomalies(loads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluates signature power anomalies across all operational station loads:
    - Flags active loads drawing > 125% of baseline nominal power
    - Computes wasted kilowatt-hours and attributes engineering root cause
    """
    anomalies = []
    for load in loads:
        nominal = float(load["nominal_kw"])
        live = float(load["live_kw"])
        status = str(load["status"]).upper()
        
        # Anomaly threshold: 125% of nominal baseline
        threshold = 1.25 * nominal
        is_surge = live > threshold
        excess_kw = round(max(0.0, live - nominal), 2)
        surge_pct = round(((live / max(0.01, nominal)) - 1.0) * 100.0, 1)

        load["is_surge"] = is_surge
        load["excess_kw"] = excess_kw
        load["surge_pct"] = surge_pct

        if is_surge and status == "ONLINE":
            name = load["name"]
            probable_cause = CAUSE_CATALOG.get(
                name,
                "Sub-zero electromechanical friction, cold-lubrication viscosity increase, or phase imbalance."
            )
            # Assuming continuous draw for 1 hour
            est_wasted_kwh = round(excess_kw * 1.0, 2)

            anomalies.append({
                "id": load["id"],
                "name": name,
                "priority": load["priority"],
                "nominal_kw": nominal,
                "live_kw": live,
                "excess_kw": excess_kw,
                "surge_pct": surge_pct,
                "wasted_kwh_per_hr": est_wasted_kwh,
                "severity": "CRITICAL" if load["priority"] <= 2 else "WARNING",
                "probable_cause": probable_cause,
                "message": f"Power surge on '{name}': drawing {live:.1f} kW (+{excess_kw:.1f} kW / +{surge_pct:.1f}% over nominal). Wasting ~{est_wasted_kwh} kWh/hr."
            })

    return anomalies

