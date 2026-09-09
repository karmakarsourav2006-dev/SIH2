from fastapi import APIRouter, HTTPException
from backend.models import ExperimentScheduleInput
from backend.services.scheduler import evaluate_experiments, update_experiment_status
from backend.database import get_db

router = APIRouter(prefix="/api/experiments", tags=["Research Experiment Optimizer"])

@router.get("")
def list_experiments(surplus_kw: float = 0.0, battery_pct: float = 50.0, is_critical: bool = False):
    """
    Returns scientific experiments annotated with AI energy safety recommendations.
    """
    experiments = evaluate_experiments(
        surplus_kw=surplus_kw,
        battery_pct=battery_pct,
        is_critical=is_critical
    )
    return {
        "ok": True,
        "count": len(experiments),
        "experiments": experiments
    }

@router.post("/schedule")
def schedule_experiment(payload: ExperimentScheduleInput):
    """
    Schedules, defers, or queues an experiment.
    """
    res = update_experiment_status(payload.id, payload.action)
    if not res.get("ok"):
        raise HTTPException(status_code=404, detail=res.get("error"))
    return res

