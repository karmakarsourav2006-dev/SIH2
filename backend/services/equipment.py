from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import HTTPException
from backend.config import settings
import sqlite3

PERSISTENCE_READINGS = 3

def _conn():
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def evaluate_equipment_telemetry(device_id: str, live_kw: float, timestamp=None) -> Dict[str, Any]:
    conn = _conn()
    sig = conn.execute("SELECT * FROM equipment_signatures WHERE device_id = ?", (device_id,)).fetchone()
    if not sig:
        conn.close(); raise HTTPException(404, f"Unknown equipment device: {device_id}")
    deviation = ((live_kw - sig["nominal_kw"]) / sig["nominal_kw"]) * 100
    absolute = abs(deviation)
    abnormal = absolute > sig["tolerance_percent"]
    if not abnormal:
        status, risk, consecutive = "NORMAL", "LOW", 0
    else:
        history = conn.execute("SELECT deviation_percent FROM equipment_telemetry_logs WHERE device_id=? ORDER BY id DESC", (device_id,)).fetchall()
        consecutive = 1
        for previous in history:
            if abs(previous["deviation_percent"]) > sig["tolerance_percent"]: consecutive += 1
            else: break
        status = "CRITICAL_MALFUNCTION" if consecutive >= PERSISTENCE_READINGS else "PERSISTENT_ANOMALY" if consecutive > 1 else "ANOMALY"
        risk = "HIGH" if consecutive > 1 else "MODERATE"
    if deviation > 40:
        diagnosis = "Abnormal high power draw. Probable compressor failure, thermal seal rupture, or internal short. Recommend immediate inspection or shedding."
    elif deviation < -50:
        diagnosis = "Power delivery failure or open circuit. Device is under-consuming. Recommend immediate inspection."
    elif status in ("ANOMALY", "PERSISTENT_ANOMALY"):
        diagnosis = f"Abnormal energy consumption detected; persistence check is {consecutive}/{PERSISTENCE_READINGS} consecutive readings."
    else:
        diagnosis = "Power signature is within the calibrated baseline tolerance."
    score = min(1.0, absolute / 100)
    observed_at = timestamp or datetime.now(timezone.utc).isoformat()
    conn.execute("INSERT INTO equipment_telemetry_logs (device_id,timestamp,observed_kw,deviation_percent,anomaly_score,flagged,diagnosis) VALUES (?,?,?,?,?,?,?)", (device_id, observed_at, live_kw, deviation, score, status != "NORMAL", diagnosis))
    conn.execute("UPDATE equipment_signatures SET status = ? WHERE device_id = ?", (status, device_id))
    if status == "NORMAL":
        conn.commit()
    else:
        conn.commit()
    excess_kw = max(live_kw - sig["nominal_kw"], 0)
    result = dict(sig); result.update({"observed_kw": live_kw, "deviation_percent": round(deviation, 2), "anomaly_score": round(score, 3), "flagged": status != "NORMAL", "status": status, "risk": risk, "diagnosis": diagnosis, "timestamp": observed_at, "consecutive_abnormal_readings": consecutive, "persistence_required": PERSISTENCE_READINGS, "excess_kw": round(excess_kw, 2), "extra_energy_1h_kwh": round(excess_kw, 2), "extra_energy_24h_kwh": round(excess_kw * 24, 2)})
    conn.close(); return result

def list_signatures():
    conn = _conn(); rows = [dict(r) for r in conn.execute("SELECT * FROM equipment_signatures")]
    for row in rows:
        last = conn.execute("SELECT observed_kw,deviation_percent,timestamp,diagnosis FROM equipment_telemetry_logs WHERE device_id=? ORDER BY id DESC LIMIT 1", (row["device_id"],)).fetchone()
        row.update(dict(last) if last else {"observed_kw": row["nominal_kw"], "deviation_percent": 0, "timestamp": None, "diagnosis": "Power signature is within the calibrated baseline tolerance."})
        row["risk"] = "LOW" if row["status"] == "NORMAL" else "HIGH" if row["status"] in ("CRITICAL_MALFUNCTION", "PERSISTENT_ANOMALY") else "MODERATE"
        row["flagged"] = row["status"] not in ("NORMAL", "ISOLATED")
        history = conn.execute("SELECT deviation_percent FROM equipment_telemetry_logs WHERE device_id=? ORDER BY id DESC", (row["device_id"],)).fetchall()
        count = 0
        for item in history:
            if abs(item["deviation_percent"]) > row["tolerance_percent"]: count += 1
            else: break
        row["consecutive_abnormal_readings"] = count; row["persistence_required"] = PERSISTENCE_READINGS
        excess = max(float(row["observed_kw"]) - float(row["nominal_kw"]), 0); row.update({"excess_kw": round(excess, 2), "extra_energy_1h_kwh": round(excess, 2), "extra_energy_24h_kwh": round(excess * 24, 2)})
    conn.close(); return rows

def live_anomalies():
    return [r for r in list_signatures() if abs(r["deviation_percent"]) > r["tolerance_percent"]]

def equipment_action(device_id, action):
    conn = _conn(); exists = conn.execute("SELECT * FROM equipment_signatures WHERE device_id=?", (device_id,)).fetchone()
    if not exists: conn.close(); raise HTTPException(404, f"Unknown equipment device: {device_id}")
    status = {"ISOLATE": "ISOLATED", "RESET": "NORMAL", "RECALIBRATE": "NORMAL"}[action]
    before_rows = conn.execute("SELECT live_kw FROM loads WHERE station_id='ST-01' AND UPPER(status)='ONLINE'").fetchall()
    before_station = round(sum(float(r["live_kw"]) for r in before_rows), 2)
    affected = conn.execute("SELECT observed_kw FROM equipment_telemetry_logs WHERE device_id=? ORDER BY id DESC LIMIT 1", (device_id,)).fetchone()
    affected_kw = float(affected["observed_kw"]) if affected else float(exists["nominal_kw"])
    if action == "ISOLATE": conn.execute("UPDATE equipment_signatures SET status=? WHERE device_id=?", (status, device_id))
    conn.commit(); after_station = round(max(before_station - affected_kw, 0), 2) if action == "ISOLATE" else before_station; conn.close()
    return {"device_id": device_id, "action": action, "status": status, "energy_balance": {"before_station_load_kw": before_station, "before_equipment_load_kw": round(affected_kw, 2), "after_station_load_kw": after_station, "after_equipment_load_kw": 0 if action == "ISOLATE" else round(affected_kw, 2), "load_removed_kw": round(before_station - after_station, 2)}}
