import datetime
from typing import List, Dict, Any, Tuple
from backend.database import get_db

class EmergencySupervisor:
    """
    Deterministic Safety-First Polar Emergency Supervisor.
    Never relies on LLM hallucination for life-critical survival decisions.
    """

    @classmethod
    def audit_station_safety(
        cls,
        station_id: str,
        battery_kwh: float,
        battery_capacity_kwh: float,
        total_gen_kw: float,
        total_renewables_kw: float,
        active_demand_kw: float,
        gen_kw: float,
        wind_mps: float = 12.0
    ) -> Dict[str, Any]:
        soc_pct = round(max(0.0, min(100.0, (battery_kwh / max(1.0, battery_capacity_kwh)) * 100.0)), 1)
        net_flow_kw = round(total_gen_kw - active_demand_kw, 2)

        # 1. Evaluate 4-Tier Severity
        severity = "INFO"
        events = []
        auto_voice = None
        mode = "NORMAL RUN"
        shedded_assets = []

        # TIER 1: EMERGENCY (Immediate Blackout Danger)
        if soc_pct < 15.0 or (net_flow_kw < -15.0 and gen_kw == 0.0):
            severity = "EMERGENCY"
            mode = "SURVIVAL CRITICAL"
            events.append("CODE RED: Battery reserve depleted below 15% or massive unbacked deficit.")
            events.append("AUTONOMOUS INTERLOCK: P2 Science & P3 Auxiliary contactors isolated.")
            events.append("LIFE-SUPPORT PROTECTED: P1 Thermal Habitat loop secured.")
            auto_voice = f"Emergency Alert! Battery at {soc_pct} percent. Non-critical loads shed. Core life support secured."

            # Perform physical shed in database
            with get_db() as conn:
                conn.execute(
                    "UPDATE loads SET status = 'SHEDDED' WHERE station_id = ? AND priority IN (2, 3) AND status != 'SHEDDED'",
                    (station_id,)
                )
                conn.execute(
                    "UPDATE loads SET status = 'ONLINE' WHERE station_id = ? AND priority = 1 AND status != 'ONLINE'",
                    (station_id,)
                )
                # Log critical event into database alerts
                conn.execute(
                    """INSERT INTO alerts (station_id, severity, category, message, root_cause, acknowledged)
                       VALUES (?, 'CRITICAL', 'MICROGRID_EMERGENCY', ?, 'Battery depleted below survival threshold', 0)""",
                    (station_id, f"Autonomous Emergency Shed triggered at {soc_pct}% SoC")
                )
                conn.commit()

        # TIER 2: CRITICAL (Deficit threat)
        elif soc_pct < 25.0 or (net_flow_kw < -10.0 and gen_kw == 0.0):
            severity = "CRITICAL"
            mode = "SURVIVAL CRITICAL"
            events.append("CRITICAL DEFICIT: Battery SoC below 25% reserve threshold.")
            events.append("AUTONOMOUS INTERLOCK: Auxiliary P3 loads shed to conserve battery runway.")
            auto_voice = f"Warning! Microgrid deficit detected. Battery SoC at {soc_pct} percent. Conserving reserve."

            with get_db() as conn:
                conn.execute(
                    "UPDATE loads SET status = 'SHEDDED' WHERE station_id = ? AND priority = 3 AND status != 'SHEDDED'",
                    (station_id,)
                )
                conn.commit()

        # TIER 3: WARNING (Weather or high draw)
        elif soc_pct < 40.0 or wind_mps > 22.0:
            severity = "WARNING"
            mode = "CONSERVATION WATCH"
            if wind_mps > 22.0:
                events.append(f"HIGH WIND ADVISORY: Wind velocity {wind_mps} m/s nearing 25 m/s turbine cut-out.")
                auto_voice = f"Advisory. High winds of {wind_mps} meters per second. Wind turbine cut-out imminent."
            else:
                events.append(f"BATTERY RESERVE LOW: Storage at {soc_pct}%. Minimize science workloads.")
                auto_voice = f"Advisory. Battery reserve is at {soc_pct} percent. Science loads should be deferred."

        # TIER 4: INFO (Optimal Normal Operations)
        else:
            severity = "INFO"
            mode = "NORMAL RUN"
            events.append("Microgrid operating within optimal thermodynamic parameters.")

        # Re-fetch loads after potential shedding
        with get_db() as conn:
            rows = conn.execute("SELECT * FROM loads WHERE station_id = ? ORDER BY priority ASC", (station_id,)).fetchall()
            loads = [dict(r) for r in rows]

        active_demand = round(sum(l["live_kw"] for l in loads if str(l.get("status")).upper() == "ONLINE"), 2)
        p1_demand = round(sum(l["live_kw"] for l in loads if l.get("priority") == 1 and str(l.get("status")).upper() == "ONLINE"), 2)
        final_net = round(total_gen_kw - active_demand, 2)

        safe_runway_hours = round(battery_kwh / max(0.2, active_demand - total_renewables_kw), 1) if active_demand > total_renewables_kw else 999.0
        p1_isolated_hours = round(battery_kwh / max(0.2, p1_demand - total_renewables_kw), 1) if p1_demand > total_renewables_kw else 999.0

        return {
            "station_id": station_id,
            "severity": severity,
            "mode": mode,
            "is_critical": severity in ("CRITICAL", "EMERGENCY"),
            "events": events,
            "auto_voice_alert": auto_voice,
            "soc_pct": soc_pct,
            "active_demand_kw": active_demand,
            "p1_demand_kw": p1_demand,
            "net_flow_kw": final_net,
            "safe_runtime_hours": safe_runway_hours,
            "p1_isolated_hours": p1_isolated_hours,
            "loads": loads
        }
