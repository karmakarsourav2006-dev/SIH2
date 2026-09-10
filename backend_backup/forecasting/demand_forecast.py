from typing import List, Dict, Any

def compute_composite_demand(
    online_loads: List[Dict[str, Any]],
    active_experiments: List[Dict[str, Any]],
    thermal_heating_kw: float
) -> Dict[str, float]:
    """
    Aggregates composite demand:
    - Base habitat life-support & medical relays
    - Thermal loop baseline
    - Active research activities/experiments
    - Auxiliary equipment
    """
    base_load_kw = sum(float(l["live_kw"]) for l in online_loads if l.get("status") == "ONLINE")
    experiment_load_kw = sum(float(e.get("avg_power_kw", 0.0)) for e in active_experiments if e.get("execution_status") == "RUNNING")
    
    p1_kw = sum(float(l["live_kw"]) for l in online_loads if l.get("status") == "ONLINE" and l.get("priority") == 1)
    p2_kw = sum(float(l["live_kw"]) for l in online_loads if l.get("status") == "ONLINE" and l.get("priority") == 2)
    p3_kw = sum(float(l["live_kw"]) for l in online_loads if l.get("status") == "ONLINE" and l.get("priority") == 3)

    total_demand_kw = round(base_load_kw + experiment_load_kw, 2)

    return {
        "total_demand_kw": total_demand_kw,
        "base_load_kw": round(base_load_kw, 2),
        "experiment_load_kw": round(experiment_load_kw, 2),
        "thermal_heating_kw": round(thermal_heating_kw, 2),
        "p1_demand_kw": round(p1_kw, 2),
        "p2_demand_kw": round(p2_kw + experiment_load_kw, 2),
        "p3_demand_kw": round(p3_kw, 2)
    }

