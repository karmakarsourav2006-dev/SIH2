from typing import Dict, Any, List
from backend.forecasting.solar_forecast import compute_solar_power
from backend.forecasting.wind_forecast import compute_wind_power
from backend.forecasting.heating_forecast import compute_thermal_heating
from backend.forecasting.demand_forecast import compute_composite_demand

class ModelManager:
    """Central orchestration manager for polar microgrid generation and demand forecasting."""

    @staticmethod
    def forecast_microgrid(
        wind_mps: float,
        lux: float,
        temp_c: float,
        gen_kw: float,
        loads: List[Dict[str, Any]],
        experiments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        solar_kw = compute_solar_power(lux=lux, temp_c=temp_c)
        wind_kw = compute_wind_power(wind_mps=wind_mps)
        thermal_heating_kw = compute_thermal_heating(temp_c=temp_c, wind_mps=wind_mps)
        
        demand_data = compute_composite_demand(
            online_loads=loads,
            active_experiments=experiments,
            thermal_heating_kw=thermal_heating_kw
        )

        total_renewables = round(solar_kw + wind_kw, 3)
        total_gen = round(total_renewables + gen_kw, 3)
        net_flow_kw = round(total_gen - demand_data["total_demand_kw"], 2)

        return {
            "solar_kw": solar_kw,
            "wind_kw": wind_kw,
            "thermal_heating_kw": thermal_heating_kw,
            "total_renewables_kw": total_renewables,
            "generator_kw": round(gen_kw, 2),
            "total_generation_kw": total_gen,
            "net_flow_kw": net_flow_kw,
            "demand": demand_data
        }

