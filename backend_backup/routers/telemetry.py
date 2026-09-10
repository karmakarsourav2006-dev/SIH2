from fastapi import APIRouter, HTTPException
from backend.models import TelemetryInput, LoadToggleInput
from backend.services.forecasting import forecast_generation
from backend.services.emergency import evaluate_emergency
from backend.services.anomaly import detect_anomalies
from backend.services.scheduler import evaluate_experiments
from backend.database import get_db

router = APIRouter(prefix="/api", tags=["Telemetry & Microgrid Relays"])

@router.post("/telemetry")
def get_telemetry(payload: TelemetryInput):
    # 1. Physics forecasting
    gen_data = forecast_generation(
        wind_mps=payload.wind_mps,
        lux=payload.lux,
        temp_c=payload.temp_c,
        gen_kw=payload.gen_kw
    )

    # 2. Emergency Evaluation & Automatic Shedding
    (
        mode,
        is_critical,
        emergency_events,
        loads,
        active_demand,
        p1_demand,
        net_flow,
        station_survival_hrs,
        p1_isolated_hrs
    ) = evaluate_emergency(
        battery_kwh=payload.battery_kwh,
        battery_capacity=160.0,
        total_gen=gen_data["total_gen"],
        total_renewables=gen_data["total_renewables"],
        gen_kw=payload.gen_kw
    )

    # 3. Signature Malfunction & Surge Detection
    anomalies = detect_anomalies(loads)

    # 4. Research Experiment Optimization check
    surplus_kw = max(0.0, gen_data["total_gen"] - active_demand)
    soc_pct = round(max(0.0, min(100.0, (payload.battery_kwh / 160.0) * 100.0)), 1)
    experiments = evaluate_experiments(surplus_kw, soc_pct, is_critical)

    return {
        "status": "success",
        "station_mode": mode,
        "is_critical": is_critical,
        "environment": {
            "wind_mps": payload.wind_mps,
            "lux": payload.lux,
            "temp_c": payload.temp_c,
            "battery_kwh": payload.battery_kwh,
            "battery_capacity_kwh": 160.0,
            "soc_pct": soc_pct,
            "generator_kw": payload.gen_kw
        },
        "power": {
            "solar_kw": gen_data["solar_kw"],
            "wind_kw": gen_data["wind_kw"],
            "total_renewables_kw": gen_data["total_renewables"],
            "generator_kw": gen_data["gen_kw"],
            "total_generation_kw": gen_data["total_gen"],
            "active_demand_kw": active_demand,
            "p1_demand_kw": p1_demand,
            "thermal_heating_baseline_kw": gen_data["thermal_heating_demand_kw"],
            "net_flow_kw": net_flow,
            "surplus_kw": round(surplus_kw, 2)
        },
        "survivability": {
            "station_survival_hrs": station_survival_hrs,
            "p1_isolated_hrs": p1_isolated_hrs,
            "is_charging": net_flow > 0
        },
        "loads": loads,
        "anomalies": anomalies,
        "emergency_events": emergency_events,
        "experiments_summary": {
            "total_queued": len(experiments),
            "safe_to_run_count": sum(1 for e in experiments if e["can_run"])
        }
    }

@router.post("/loads/toggle")
def toggle_load_relay(payload: LoadToggleInput):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM loads WHERE id = ?", (payload.id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Load relay '{payload.id}' not found")

        current_status = str(row["status"]).upper()
        target_status = "SHEDDED" if current_status == "ONLINE" else "ONLINE"

        conn.execute("UPDATE loads SET status = ? WHERE id = ?", (target_status, payload.id))
        conn.commit()

        updated = dict(conn.execute("SELECT * FROM loads WHERE id = ?", (payload.id,)).fetchone())
        return {
            "ok": True,
            "id": payload.id,
            "name": updated["name"],
            "status": target_status
        }

@router.post("/loads/reset")
def reset_all_loads():
    with get_db() as conn:
        conn.execute("UPDATE loads SET status = 'ONLINE'")
        conn.commit()
        loads = [dict(r) for r in conn.execute("SELECT * FROM loads ORDER BY priority ASC, id ASC").fetchall()]
    return {
        "ok": True,
        "message": "All station load relays restored to ONLINE status",
        "loads": loads
    }

