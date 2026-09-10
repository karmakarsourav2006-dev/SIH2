from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import HTTPException
from backend.config import settings
import sqlite3

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
    if absolute <= sig["tolerance_percent"]:
        status, risk = "NORMAL", "LOW"
    elif absolute <= 40:
        status, risk = "WARNING", "MODERATE"
    else:
        status, risk = "CRITICAL_MALFUNCTION", "HIGH"
    if deviation > 40:
        diagnosis = "Abnormal high power draw. Probable compressor failure, thermal seal rupture, or internal short. Recommend immediate inspection or shedding."
    elif deviation < -50:
        diagnosis = "Power delivery failure or open circuit. Device is under-consuming. Recommend immediate inspection."
    elif status == "WARNING":
        diagnosis = "Consumption is outside the calibrated tolerance. Inspect the device during the next maintenance window."
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
    result = dict(sig); result.update({"observed_kw": live_kw, "deviation_percent": round(deviation, 2), "anomaly_score": round(score, 3), "flagged": status != "NORMAL", "status": status, "risk": risk, "diagnosis": diagnosis, "timestamp": observed_at})
    conn.close(); return result

def list_signatures():
    conn = _conn(); rows = [dict(r) for r in conn.execute("SELECT * FROM equipment_signatures")]
    for row in rows:
        last = conn.execute("SELECT observed_kw,deviation_percent,timestamp FROM equipment_telemetry_logs WHERE device_id=? ORDER BY id DESC LIMIT 1", (row["device_id"],)).fetchone()
        row.update(dict(last) if last else {"observed_kw": row["nominal_kw"], "deviation_percent": 0, "timestamp": None})
    conn.close(); return rows

def live_anomalies():
    return [r for r in list_signatures() if abs(r["deviation_percent"]) > r["tolerance_percent"]]

def equipment_action(device_id, action):
    conn = _conn(); exists = conn.execute("SELECT 1 FROM equipment_signatures WHERE device_id=?", (device_id,)).fetchone()
    if not exists: conn.close(); raise HTTPException(404, f"Unknown equipment device: {device_id}")
    status = {"ISOLATE": "ISOLATED", "RESET": "NORMAL", "RECALIBRATE": "NORMAL"}[action]
    conn.execute("UPDATE equipment_signatures SET status=? WHERE device_id=?", (status, device_id)); conn.commit(); conn.close()
    return {"device_id": device_id, "action": action, "status": status}
