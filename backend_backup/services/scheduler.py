from typing import List, Dict, Any
from backend.database import get_db

def evaluate_experiments(surplus_kw: float, battery_pct: float, is_critical: bool) -> List[Dict[str, Any]]:
    """
    Evaluates scientific experiments against microgrid renewable surplus and BESS margins:
    - Recommends 'SAFE TO RUN' when surplus covers experiment power budget without deficit.
    - Advises 'DELAY - DEFICIT EXPECTED' if running would cause battery discharge or during emergency.
    """
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM experiments ORDER BY priority ASC, id ASC").fetchall()
        experiments = [dict(r) for r in rows]

    evaluated = []
    for exp in experiments:
        req_kwh = float(exp["required_kwh"])
        dur_hrs = max(0.5, float(exp["duration_hrs"]))
        avg_kw = round(req_kwh / dur_hrs, 2)
        exp["avg_power_kw"] = avg_kw

        # Feasibility check
        if is_critical:
            can_run = False
            badge = "DELAY - SURVIVAL MODE"
            recommendation = "Station is in SURVIVAL CRITICAL mode. All non-vital science tasks deferred."
        elif surplus_kw >= avg_kw:
            can_run = True
            badge = "SAFE TO RUN"
            recommendation = f"Renewable surplus (+{surplus_kw:.1f} kW) fully covers required ~{avg_kw:.1f} kW. Zero battery drain."
        elif battery_pct >= 60.0 and surplus_kw >= (avg_kw * 0.5):
            can_run = True
            badge = "CONDITIONALLY SAFE"
            recommendation = f"High BESS ({battery_pct:.1f}% SoC) cushions minor deficit. Impact: ~{req_kwh:.1f} kWh over {dur_hrs:.1f} hrs."
        else:
            can_run = False
            badge = "DELAY - DEFICIT EXPECTED"
            recommendation = f"Requires ~{avg_kw:.1f} kW continuous. Would increase grid deficit. Wait for wind peak or generator online."

        exp["can_run"] = can_run
        exp["badge"] = badge
        exp["recommendation"] = recommendation
        evaluated.append(exp)

    return evaluated

def update_experiment_status(exp_id: str, action: str) -> Dict[str, Any]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM experiments WHERE id = ?", (exp_id,)).fetchone()
        if not row:
            return {"ok": False, "error": f"Experiment '{exp_id}' not found"}

        status_map = {
            "run": "RUNNING",
            "defer": "DEFERRED",
            "queue": "QUEUED",
            "complete": "COMPLETED"
        }
        new_status = status_map.get(action.lower(), "QUEUED")
        conn.execute("UPDATE experiments SET status = ? WHERE id = ?", (new_status, exp_id))
        conn.commit()

        updated = dict(conn.execute("SELECT * FROM experiments WHERE id = ?", (exp_id,)).fetchone())
        return {"ok": True, "experiment": updated}

