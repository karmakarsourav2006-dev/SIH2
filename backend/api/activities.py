import uuid
from fastapi import APIRouter, HTTPException
from backend.models.activity import ActivityCreate
from backend.database import get_db

router = APIRouter(prefix="/api/activities", tags=["Activities & Experiments"])

@router.get("")
def list_activities(station_id: str = "ST-01", surplus_kw: float = 5.0):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM activities WHERE station_id = ? ORDER BY priority ASC, id ASC", (station_id,)).fetchall()
        activities = [dict(r) for r in rows]

    # Annotate with real-time green energy recommendation
    for a in activities:
        avg_kw = round(float(a["required_kwh"]) / max(0.5, float(a["duration_hrs"])), 2)
        a["avg_power_kw"] = avg_kw
        can_run = surplus_kw >= avg_kw
        a["safe_to_run"] = can_run
        a["ai_recommendation"] = (
            f"Safe to Run on Renewable Surplus (+{surplus_kw:.1f} kW available)"
            if can_run else
            f"Delay recommended. Requires ~{avg_kw:.1f} kW continuous. Wait for wind peak."
        )

    return {"ok": True, "count": len(activities), "activities": activities}

@router.post("")
def create_activity(activity: ActivityCreate):
    act_id = f"ACT-{uuid.uuid4().hex[:4].upper()}"
    with get_db() as conn:
        conn.execute("""
            INSERT INTO activities (id, station_id, name, required_kwh, duration_hrs, deadline_hrs, priority, approval_status, execution_status, recommended_slot)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'APPROVED', 'QUEUED', 'Next Green Window')
        """, (act_id, activity.station_id, activity.name, activity.required_kwh, activity.duration_hrs, activity.deadline_hrs, activity.priority))
        conn.commit()
        row = conn.execute("SELECT * FROM activities WHERE id = ?", (act_id,)).fetchone()
    return {"ok": True, "activity": dict(row)}

@router.post("/{activity_id}/schedule")
def update_activity_schedule(activity_id: str, action: str = "run"):
    status_map = {
        "run": "RUNNING",
        "defer": "DEFERRED",
        "queue": "QUEUED",
        "complete": "COMPLETED"
    }
    new_status = status_map.get(action.lower(), "QUEUED")
    with get_db() as conn:
        conn.execute("UPDATE activities SET execution_status = ? WHERE id = ?", (new_status, activity_id))
        conn.commit()
        row = conn.execute("SELECT * FROM activities WHERE id = ?", (activity_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Activity not found")
    return {"ok": True, "activity": dict(row)}

@router.delete("/{activity_id}")
def delete_activity(activity_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
        conn.commit()
    return {"ok": True, "deleted_id": activity_id}

