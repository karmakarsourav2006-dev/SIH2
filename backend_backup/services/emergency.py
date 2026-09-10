from typing import List, Dict, Any, Tuple
import sqlite3
from backend.database import get_db

def evaluate_emergency(
    battery_kwh: float,
    battery_capacity: float,
    total_gen: float,
    total_renewables: float,
    gen_kw: float
) -> Tuple[str, bool, List[str], List[Dict[str, Any]], float, float, float, float]:
    """
    Survival-First Polar Microgrid Protection Matrix:
    - Triggers if Battery SoC < 25% OR Net Power Flow < -12.0 kW with zero generator support.
    - Elevates mode to SURVIVAL CRITICAL:
      * Auto-sheds P3 auxiliary loads
      * Auto-sheds/defers P2 scientific loads
      * Locks & ring-fences P1 life-support & medical relays
    - Computes dynamic survival runways.
    """
    soc_pct = round(max(0.0, min(100.0, (battery_kwh / max(1.0, battery_capacity)) * 100.0)), 1)

    with get_db() as conn:
        loads_raw = conn.execute("SELECT * FROM loads ORDER BY priority ASC, id ASC").fetchall()
        loads = [dict(r) for r in loads_raw]

        initial_active_demand = sum(l["live_kw"] for l in loads if str(l["status"]).upper() == "ONLINE")
        initial_net_flow = round(total_gen - initial_active_demand, 3)

        # Trigger conditions
        is_critical = (soc_pct < 25.0) or (initial_net_flow < -12.0 and gen_kw == 0.0)
        events = []

        if is_critical:
            mode = "SURVIVAL CRITICAL"
            # Auto-shed P3 and P2
            conn.execute("UPDATE loads SET status = 'SHEDDED' WHERE priority IN (2, 3) AND status != 'SHEDDED'")
            # Ring-fence P1
            conn.execute("UPDATE loads SET status = 'ONLINE' WHERE priority = 1 AND status != 'ONLINE'")
            conn.commit()

            loads_raw = conn.execute("SELECT * FROM loads ORDER BY priority ASC, id ASC").fetchall()
            loads = [dict(r) for r in loads_raw]

            events.append("SURVIVAL CRITICAL INITIATED: SoC < 25% or Net Deficit > 12 kW with generator offline.")
            events.append("AUTOMATED PRIORITY SHED: P3 Auxiliary Drone & P2 Science tasks isolated to preserve core bank.")
            events.append("RING-FENCE SECURED: P1 Habitat Life-Support, Medical & Comms locked online.")
        else:
            mode = "NORMAL OPTIMIZATION"

    # Effective demand after protection matrix
    active_demand = round(sum(l["live_kw"] for l in loads if str(l["status"]).upper() == "ONLINE"), 2)
    p1_demand = round(sum(l["live_kw"] for l in loads if l["priority"] == 1 and str(l["status"]).upper() == "ONLINE"), 2)
    net_flow = round(total_gen - active_demand, 2)

    # Dynamic Survival Runways
    # Total runtime: battery_kwh / max(0.2, active_demand - total_renewables)
    # Protected P1 runtime: battery_kwh / max(0.2, p1_demand - total_renewables)
    station_survival_hrs = round(battery_kwh / max(0.2, active_demand - total_renewables), 1)
    p1_isolated_hrs = round(battery_kwh / max(0.2, p1_demand - total_renewables), 1)

    return mode, is_critical, events, loads, active_demand, p1_demand, net_flow, station_survival_hrs, p1_isolated_hrs

