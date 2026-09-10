import uuid
import datetime
from typing import Dict, Any, List, Optional
from backend.database import get_db
from backend.services.digital_twin import DigitalTwin
from backend.services.energy_service import EnergyService
from backend.services.station_service import StationService
from backend.forecasting.model_manager import ModelManager
from backend.forecasting.heating_forecast import compute_thermal_heating
from backend.forecasting.solar_forecast import compute_solar_power
from backend.forecasting.wind_forecast import compute_wind_power
from backend.anomaly.detector import AnomalyDetector

class AITools:
    """Live project tools exposing station state, forecasting, scheduling, and simulations."""

    @staticmethod
    def get_station_status(station_id: str = "ST-01") -> Dict[str, Any]:
        """Returns live microgrid telemetry, generation mix, demand, and operational mode."""
        state = DigitalTwin.evaluate_state(station_id=station_id)
        station = StationService.get_station_by_id(station_id) or {"name": "Maitri Station"}
        return {
            "station_id": station_id,
            "station_name": station.get("name"),
            "mode": state.get("mode"),
            "is_critical": state.get("is_critical"),
            "soc_pct": state.get("soc_pct"),
            "battery_kwh": state.get("battery_kwh"),
            "battery_capacity_kwh": state.get("battery_capacity_kwh"),
            "weather": state.get("weather"),
            "generation": state.get("generation"),
            "demand": state.get("demand"),
            "net_flow_kw": state.get("net_flow_kw"),
            "survivability": state.get("survivability"),
            "active_loads_count": len([l for l in state.get("loads", []) if l.get("status") == "ONLINE"])
        }

    @staticmethod
    def get_current_energy(station_id: str = "ST-01") -> Dict[str, Any]:
        """Returns station-level stored energy in battery reserve, renewable generation, and power balance."""
        state = DigitalTwin.evaluate_state(station_id=station_id)
        gen = state.get("generation", {})
        battery_kwh = state.get("battery_kwh", 0.0)
        battery_cap = state.get("battery_capacity_kwh", 160.0)
        soc_pct = state.get("soc_pct", 0.0)
        solar_kw = gen.get("solar_kw", 0.0)
        wind_kw = gen.get("wind_kw", 0.0)
        total_gen_kw = gen.get("total_generation_kw", 0.0)
        demand_kw = state.get("demand", {}).get("active_demand_kw", 0.0)
        net_flow_kw = state.get("net_flow_kw", 0.0)
        safe_runtime = state.get("survivability", {}).get("safe_runtime_hours", 0.0)
        return {
            "station_id": station_id,
            "stored_energy_kwh": battery_kwh,
            "storage_capacity_kwh": battery_cap,
            "soc_pct": soc_pct,
            "generation_power_kw": total_gen_kw,
            "solar_kw": solar_kw,
            "wind_kw": wind_kw,
            "demand_kw": demand_kw,
            "net_flow_kw": net_flow_kw,
            "safe_runtime_hours": safe_runtime
        }

    @staticmethod
    def get_current_schedule(station_id: str = "ST-01") -> List[Dict[str, Any]]:
        """Returns all scientific experiments, operations queue, and slot recommendations."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM activities WHERE station_id = ? ORDER BY priority ASC",
                (station_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_activity(activity_id_or_name: str, station_id: str = "ST-01") -> Optional[Dict[str, Any]]:
        """Fetch an activity by exact ID or fuzzy matching equipment name."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM activities WHERE id = ? OR LOWER(name) LIKE ? LIMIT 1",
                (activity_id_or_name, f"%{activity_id_or_name.lower().strip()}%")
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_activity_energy(activity_id_or_name: str, station_id: str = "ST-01") -> Dict[str, Any]:
        """Returns the total energy in kWh required to complete an activity."""
        act = AITools.get_activity(activity_id_or_name, station_id)
        if not act:
            return {"error": f"Activity '{activity_id_or_name}' not found in station database."}
        return {
            "id": act.get("id"),
            "name": act.get("name"),
            "required_kwh": act.get("required_kwh"),
            "duration_hrs": act.get("duration_hrs"),
            "status": act.get("execution_status")
        }

    @staticmethod
    def get_activity_power(activity_id_or_name: str, station_id: str = "ST-01") -> Dict[str, Any]:
        """Calculates average continuous electrical draw in kW (kWh / duration_hrs)."""
        act = AITools.get_activity(activity_id_or_name, station_id)
        if not act:
            return {"error": f"Activity '{activity_id_or_name}' not found."}
        kwh = float(act.get("required_kwh", 0.0))
        hrs = max(0.25, float(act.get("duration_hrs", 1.0)))
        avg_kw = round(kwh / hrs, 2)
        return {
            "id": act.get("id"),
            "name": act.get("name"),
            "continuous_power_kw": avg_kw,
            "required_kwh": kwh,
            "duration_hrs": hrs
        }

    @staticmethod
    def get_energy_forecast(station_id: str = "ST-01", hours: int = 24) -> Dict[str, Any]:
        """Generates 24-hour predictive generation curves (solar, wind, demand, net balance)."""
        timeline = []
        base_loads = EnergyService.get_station_loads(station_id)
        base_demand = sum(float(l.get("live_kw", 0.0)) for l in base_loads if l.get("status") == "ONLINE")

        for h in range(min(hours, 48)):
            lux = max(0.0, 420.0 * (0.8 + 0.4 * (1.0 if (6 <= h % 24 <= 18) else 0.05)))
            wind = round(9.0 + 4.5 * ((h * 7) % 5) / 5.0, 1)
            temp = round(-28.0 - 5.0 * ((h * 3) % 4) / 4.0, 1)

            solar_kw = compute_solar_power(lux, temp)
            wind_kw = compute_wind_power(wind)
            heat_kw = compute_thermal_heating(temp, wind)
            total_gen = solar_kw + wind_kw
            tot_demand = base_demand + heat_kw
            surplus = round(total_gen - tot_demand, 2)

            timeline.append({
                "hour_offset": h,
                "time_label": f"+{h:02d}:00 UTC",
                "solar_kw": solar_kw,
                "wind_kw": wind_kw,
                "renewables_kw": round(total_gen, 2),
                "demand_kw": round(tot_demand, 2),
                "surplus_kw": surplus,
                "is_green_window": surplus > 3.0
            })

        green_windows_count = len([t for t in timeline if t["is_green_window"]])
        return {
            "station_id": station_id,
            "forecast_hours": hours,
            "green_windows_count": green_windows_count,
            "timeline": timeline[:24]
        }

    @staticmethod
    def get_weather_forecast(station_id: str = "ST-01") -> Dict[str, Any]:
        """Returns meteorological conditions: temperature, wind velocity, irradiance, and storm severity."""
        return {
            "station_id": station_id,
            "temp_c": -28.0,
            "wind_mps": 12.0,
            "lux": 350.0,
            "wind_knots": round(12.0 * 1.94384, 1),
            "blizzard_severity": 0.15,
            "katabatic_alert": False,
            "frostbite_risk": "HIGH",
            "advisory": "Stable sub-zero Antarctic baseline conditions. Moderate renewable potential."
        }

    @staticmethod
    def get_heating_forecast(station_id: str = "ST-01", ambient_temp_c: float = -28.0) -> Dict[str, Any]:
        """Computes structural heat loss and baseline habitat core electrical heating load."""
        heat_kw = compute_thermal_heating(ambient_temp_c, 12.0)
        station = StationService.get_station_by_id(station_id) or {}
        base_thermal = float(station.get("base_thermal_rating_kw", 14.0))
        return {
            "station_id": station_id,
            "ambient_temp_c": ambient_temp_c,
            "habitat_target_temp_c": 19.5,
            "delta_t": round(19.5 - ambient_temp_c, 1),
            "estimated_heating_kw": heat_kw,
            "base_thermal_rating_kw": base_thermal,
            "urgency": "CRITICAL - Non-deferrable life-support core"
        }

    @staticmethod
    def get_battery_status(station_id: str = "ST-01") -> Dict[str, Any]:
        """Returns BESS (LiFePO4) metrics: SoC, reserve kWh, cell temperature, and C-rate safety margin."""
        station = StationService.get_station_by_id(station_id) or {"battery_capacity_kwh": 160.0}
        cap = float(station.get("battery_capacity_kwh", 160.0))
        state = DigitalTwin.evaluate_state(station_id=station_id)
        soc = state.get("soc_pct", 53.0)
        curr_kwh = state.get("battery_kwh", 85.0)
        return {
            "station_id": station_id,
            "battery_chemistry": "LiFePO4 Deep-Cycle Polar Bank",
            "capacity_kwh": cap,
            "current_reserve_kwh": curr_kwh,
            "soc_pct": soc,
            "cell_temperature_c": 15.2,
            "thermal_conditioning_status": "ACTIVE_HEATED",
            "min_cutoff_soc_pct": 20.0,
            "max_c_rate": 0.5,
            "safe_runtime_hours": state.get("survivability", {}).get("safe_runtime_hours", 48.0)
        }

    @staticmethod
    def get_alerts(station_id: str = "ST-01") -> List[Dict[str, Any]]:
        """Returns active system alerts and fault warnings."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM alerts WHERE station_id = ? ORDER BY id DESC LIMIT 10",
                (station_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_anomalies(station_id: str = "ST-01") -> List[Dict[str, Any]]:
        """Audits all loads for unexpected current surges (>125%) and classifies mechanical faults."""
        loads = EnergyService.get_station_loads(station_id)
        return AnomalyDetector.audit_loads(loads)

    @staticmethod
    def simulate_activity(
        station_id: str = "ST-01",
        name: str = "Simulated Operation",
        required_kwh: float = 25.0,
        duration_hrs: float = 3.0
    ) -> Dict[str, Any]:
        """
        Non-destructive what-if calculation.
        Evaluates impact of adding a new load without modifying database state.
        """
        state = DigitalTwin.evaluate_state(station_id=station_id)
        curr_demand = state.get("demand", {}).get("active_demand_kw", 25.0)
        curr_renewables = state.get("generation", {}).get("total_renewables_kw", 16.0)
        batt_kwh = state.get("battery_kwh", 85.0)

        added_kw = round(float(required_kwh) / max(0.5, float(duration_hrs)), 2)
        projected_demand = round(curr_demand + added_kw, 2)
        projected_net = round(curr_renewables - projected_demand, 2)

        if projected_net >= 0:
            projected_runway = 999.0
            deficit_notes = "Surplus coverage: Battery will not be drawn."
        else:
            deficit = abs(projected_net)
            projected_runway = round(batt_kwh / deficit, 1)
            deficit_notes = f"Draws {deficit} kW continuous deficit from battery reserve."

        safe_to_run = projected_runway >= 12.0 and state.get("soc_pct", 50.0) > 25.0

        return {
            "simulation_mode": "WHAT_IF_NON_DESTRUCTIVE",
            "name": name,
            "required_kwh": required_kwh,
            "duration_hrs": duration_hrs,
            "added_power_kw": added_kw,
            "current_demand_kw": curr_demand,
            "projected_demand_kw": projected_demand,
            "projected_net_flow_kw": projected_net,
            "projected_safe_runway_hours": projected_runway,
            "safe_to_run": safe_to_run,
            "recommendation": "APPROVED FOR EXECUTION" if safe_to_run else "DEFER TO GREEN SURPLUS WINDOW",
            "notes": deficit_notes
        }

    @staticmethod
    def create_activity(
        station_id: str = "ST-01",
        name: str = "New Science Mission",
        required_kwh: float = 20.0,
        duration_hrs: float = 2.0,
        deadline_hrs: float = 24.0,
        priority: int = 2
    ) -> Dict[str, Any]:
        """Registers a new scientific activity directly into the database."""
        act_id = f"ACT-{uuid.uuid4().hex[:6].upper()}"
        with get_db() as conn:
            conn.execute(
                """INSERT INTO activities 
                   (id, station_id, name, required_kwh, duration_hrs, deadline_hrs, priority, approval_status, execution_status, recommended_slot)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    act_id,
                    station_id,
                    name,
                    float(required_kwh),
                    float(duration_hrs),
                    float(deadline_hrs),
                    int(priority),
                    "APPROVED",
                    "QUEUED",
                    "NEXT_GREEN_WINDOW"
                )
            )
            conn.commit()

        return {
            "ok": True,
            "action": "CREATED",
            "activity_id": act_id,
            "name": name,
            "required_kwh": required_kwh,
            "duration_hrs": duration_hrs,
            "priority": priority,
            "status": "QUEUED"
        }

    @staticmethod
    def update_activity(activity_id: str, **kwargs) -> Dict[str, Any]:
        """Modifies parameters of an existing activity."""
        allowed_fields = ["name", "required_kwh", "duration_hrs", "deadline_hrs", "priority", "execution_status", "recommended_slot"]
        updates = []
        params = []
        for k, v in kwargs.items():
            if k in allowed_fields and v is not None:
                updates.append(f"{k} = ?")
                params.append(v)

        if not updates:
            return {"error": "No valid fields provided to update."}

        params.append(activity_id)
        with get_db() as conn:
            cursor = conn.execute(f"UPDATE activities SET {', '.join(updates)} WHERE id = ?", tuple(params))
            conn.commit()
            if cursor.rowcount == 0:
                return {"error": f"Activity '{activity_id}' not found."}

        return {"ok": True, "action": "UPDATED", "activity_id": activity_id, "updated_fields": list(kwargs.keys())}

    @staticmethod
    def delete_activity(activity_id: str) -> Dict[str, Any]:
        """Removes a scientific activity from the schedule."""
        with get_db() as conn:
            cursor = conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
            conn.commit()
            if cursor.rowcount == 0:
                return {"error": f"Activity '{activity_id}' not found."}
        return {"ok": True, "action": "DELETED", "activity_id": activity_id}

    @staticmethod
    def reschedule_activity(activity_id: str, new_slot: str) -> Dict[str, Any]:
        """Reschedules an activity to a specified green window or time slot."""
        with get_db() as conn:
            cursor = conn.execute(
                "UPDATE activities SET recommended_slot = ?, execution_status = 'QUEUED' WHERE id = ?",
                (new_slot, activity_id)
            )
            conn.commit()
            if cursor.rowcount == 0:
                return {"error": f"Activity '{activity_id}' not found."}
        return {"ok": True, "action": "RESCHEDULED", "activity_id": activity_id, "new_slot": new_slot}
