from fastapi import APIRouter
from backend.models.energy import EnergySimulationStep
from backend.services.digital_twin import DigitalTwin
from backend.simulation.simulator import MicrogridSimulator

router = APIRouter(prefix="/api/simulation", tags=["Simulation"])

@router.post("/step")
def run_simulation_step(payload: EnergySimulationStep):
    state = DigitalTwin.evaluate_state(
        station_id=payload.station_id,
        wind_mps=payload.wind_mps,
        lux=payload.lux,
        temp_c=payload.temp_c,
        battery_kwh=payload.battery_kwh,
        gen_kw=payload.gen_kw
    )
    return {"ok": True, "state": state}

@router.get("/scenarios")
def list_scenarios():
    return {"ok": True, "scenarios": MicrogridSimulator.SCENARIOS}

@router.post("/scenario/{scenario_key}")
def run_scenario(scenario_key: str, battery_kwh: float = 85.0):
    res = MicrogridSimulator.run_scenario(scenario_key, battery_kwh)
    return {"ok": True, "simulation": res}

