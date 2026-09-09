"""Operational tools executable by AI assistant or operators."""
from typing import Dict, Any
from backend.services.energy_service import EnergyService
from backend.services.digital_twin import DigitalTwin

def tool_shed_non_critical(station_id: str = "ST-01") -> Dict[str, Any]:
    loads = EnergyService.get_station_loads(station_id)
    shed_count = 0
    for l in loads:
        if l["priority"] in (2, 3) and l["status"] == "ONLINE":
            EnergyService.set_load_status(l["id"], "SHEDDED", station_id)
            shed_count += 1
    return {"status": "success", "shed_loads_count": shed_count}

def tool_restore_all(station_id: str = "ST-01") -> Dict[str, Any]:
    loads = EnergyService.reset_all_loads(station_id)
    return {"status": "success", "restored_loads_count": len(loads)}

def tool_get_telemetry(station_id: str = "ST-01") -> Dict[str, Any]:
    return DigitalTwin.evaluate_state(station_id=station_id)

