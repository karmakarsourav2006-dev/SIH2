from typing import Dict, Any, List
from backend.services.station_service import StationService
from backend.services.energy_service import EnergyService
from backend.forecasting.model_manager import ModelManager
from backend.optimization.energy_optimizer import EnergyOptimizer
from backend.anomaly.detector import AnomalyDetector
from backend.database import get_db

class DigitalTwin:
    """Live state aggregator representing the physical-digital mirror of the polar research station."""

    @classmethod
    def evaluate_state(
        cls,
        station_id: str = "ST-01",
        wind_mps: float = 12.0,
        lux: float = 350.0,
        temp_c: float = -28.0,
        battery_kwh: float = 85.0,
        gen_kw: float = 0.0
    ) -> Dict[str, Any]:
        station = StationService.get_station_by_id(station_id) or {
            "id": station_id,
            "name": "Maitri Station",
            "battery_capacity_kwh": 160.0,
            "generator_rating_kw": 40.0
        }

        battery_capacity = float(station.get("battery_capacity_kwh", 160.0))
        loads = EnergyService.get_station_loads(station_id)

        with get_db() as conn:
            act_rows = conn.execute("SELECT * FROM activities WHERE station_id = ?", (station_id,)).fetchall()
            activities = [dict(r) for r in act_rows]

        # 1. Physics forecasting
        forecast = ModelManager.forecast_microgrid(
            wind_mps=wind_mps,
            lux=lux,
            temp_c=temp_c,
            gen_kw=gen_kw,
            loads=loads,
            experiments=activities
        )

        total_gen = forecast["total_generation_kw"]
        total_renewables = forecast["total_renewables_kw"]
        demand_info = forecast["demand"]
        active_demand = demand_info["total_demand_kw"]
        net_flow = round(total_gen - active_demand, 2)
        soc_pct = round(max(0.0, min(100.0, (battery_kwh / battery_capacity) * 100.0)), 1)

        # 2. Deterministic 4-Tier Emergency Supervisor
        from backend.services.emergency import EmergencySupervisor
        safety = EmergencySupervisor.audit_station_safety(
            station_id=station_id,
            battery_kwh=battery_kwh,
            battery_capacity_kwh=battery_capacity,
            total_gen_kw=total_gen,
            total_renewables_kw=total_renewables,
            active_demand_kw=active_demand,
            gen_kw=gen_kw,
            wind_mps=wind_mps
        )
        mode = safety["mode"]
        is_critical = safety["is_critical"]
        severity = safety["severity"]
        emergency_events = safety["events"]
        auto_voice_alert = safety.get("auto_voice_alert")
        loads = safety["loads"]
        active_demand = safety["active_demand_kw"]
        p1_demand = safety["p1_demand_kw"]
        net_flow = safety["net_flow_kw"]


        # 3. Anomaly audit
        anomalies = AnomalyDetector.audit_loads(loads)

        # 4. Survivability Horizon
        p1_demand = sum(float(l["live_kw"]) for l in loads if l.get("priority") == 1 and l.get("status") == "ONLINE")
        safe_runtime_hours = round(battery_kwh / max(0.1, active_demand - total_renewables), 1)
        p1_isolated_hours = round(battery_kwh / max(0.1, p1_demand - total_renewables), 1)

        # 5. Energy optimization dispatch
        dispatch = EnergyOptimizer.optimize_dispatch(
            total_renewables_kw=total_renewables,
            active_demand_kw=active_demand,
            battery_kwh=battery_kwh,
            battery_capacity_kwh=battery_capacity,
            generator_kw=gen_kw
        )

        # Record history
        EnergyService.record_telemetry(
            station_id=station_id,
            solar_kw=forecast["solar_kw"],
            wind_kw=forecast["wind_kw"],
            gen_kw=gen_kw,
            demand_kw=active_demand,
            soc_pct=soc_pct,
            net_flow_kw=net_flow,
            mode=mode
        )

        return {
            "station": station,
            "station_id": station_id,
            "mode": mode,
            "is_critical": is_critical,
            "severity": severity,
            "auto_voice_alert": auto_voice_alert,
            "soc_pct": soc_pct,
            "battery_kwh": battery_kwh,
            "battery_capacity_kwh": battery_capacity,
            "temp_c": temp_c,
            "wind_mps": wind_mps,
            "lux": lux,
            "solar_kw": forecast["solar_kw"],
            "wind_kw": forecast["wind_kw"],
            "total_renewables_kw": total_renewables,
            "gen_kw": round(gen_kw, 2),
            "total_generation_kw": total_gen,
            "active_demand_kw": round(active_demand, 2),
            "p1_demand_kw": round(p1_demand, 2),
            "weather": {
                "wind_mps": wind_mps,
                "lux": lux,
                "temp_c": temp_c
            },
            "generation": {
                "solar_kw": forecast["solar_kw"],
                "wind_kw": forecast["wind_kw"],
                "total_renewables_kw": total_renewables,
                "diesel_kw": round(gen_kw, 2),
                "total_generation_kw": total_gen
            },
            "demand": {
                "active_demand_kw": round(active_demand, 2),
                "p1_demand_kw": round(p1_demand, 2),
                "thermal_heating_kw": demand_info["thermal_heating_kw"]
            },
            "net_flow_kw": net_flow,
            "survivability": {
                "safe_runtime_hours": safe_runtime_hours,
                "p1_isolated_hours": p1_isolated_hours,
                "fuel_days_left": round(max(0.0, 45.0 - (gen_kw * 0.1)), 1)
            },
            "dispatch": dispatch,
            "loads": loads,
            "anomalies": anomalies,
            "emergency_events": emergency_events,
            "activities": activities
        }

