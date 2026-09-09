from fastapi import APIRouter
from backend.models.alert import AlertCreate
from backend.database import get_db

router = APIRouter(prefix="/api/alerts", tags=["Alerts & Anomalies"])

@router.get("")
def list_alerts(station_id: str = "ST-01"):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM alerts WHERE station_id = ? ORDER BY id DESC LIMIT 50", (station_id,)).fetchall()
        return {"ok": True, "alerts": [dict(r) for r in rows]}

@router.post("")
def create_alert(alert: AlertCreate):
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO alerts (station_id, severity, category, message, root_cause, acknowledged)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (alert.station_id, alert.severity, alert.category, alert.message, alert.root_cause))
        conn.commit()
        row = conn.execute("SELECT * FROM alerts WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return {"ok": True, "alert": dict(row)}

@router.post("/{alert_id}/ack")
def acknowledge_alert(alert_id: int):
    with get_db() as conn:
        conn.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
        conn.commit()
    return {"ok": True, "acknowledged_id": alert_id}

