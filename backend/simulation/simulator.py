from typing import Dict, Any, List
from backend.forecasting.solar_forecast import compute_solar_power
from backend.forecasting.wind_forecast import compute_wind_power
from backend.forecasting.heating_forecast import compute_thermal_heating

class MicrogridSimulator:
    """Simulates what-if environmental scenarios (Blizzard, Generator Failure, Midnight Sun)."""

    SCENARIOS = {
        "BLIZZARD": {
            "name": "Catastrophic Blizzard",
            "wind_mps": 28.0,      # Above 25 m/s cut-out -> Turbines feather to 0 kW
            "lux": 15.0,           # Severe darkness
            "temp_c": -45.0,       # Extreme cold
            "gen_kw": 0.0,
            "description": "28 m/s gale forces turbine cutoff while blinding snow collapses PV output."
        },
        "GENERATOR_FAILURE": {
            "name": "Diesel Generator Trip",
            "wind_mps": 8.0,
            "lux": 180.0,
            "temp_c": -32.0,
            "gen_kw": 0.0,
            "description": "Primary diesel generator mechanically seizes during standard baseline draw."
        },
        "POLAR_SUMMER_SURPLUS": {
            "name": "Midnight Sun Peak",
            "wind_mps": 14.0,
            "lux": 850.0,
            "temp_c": -12.0,
            "gen_kw": 0.0,
            "description": "High solar insolation and consistent wind produce massive green surplus."
        },
        "DARK_POLAR_WINTER": {
            "name": "Polar Winter Night",
            "wind_mps": 6.0,
            "lux": 0.0,
            "temp_c": -55.0,
            "gen_kw": 15.0,
            "description": "Total darkness with low wind speed and peak thermal heating demands."
        }
    }

    # Aliases
    SCENARIOS["GENERATOR_TRIP"] = SCENARIOS["GENERATOR_FAILURE"]
    SCENARIOS["MIDNIGHT_SUN"] = SCENARIOS["POLAR_SUMMER_SURPLUS"]
    SCENARIOS["WINTER_NIGHT"] = SCENARIOS["DARK_POLAR_WINTER"]

    @classmethod
    def run_scenario(cls, scenario_key: str, battery_kwh: float = 85.0) -> Dict[str, Any]:
        scenario = cls.SCENARIOS.get(scenario_key.upper())
        if not scenario:
            return {"error": f"Scenario '{scenario_key}' not found"}

        wind = scenario["wind_mps"]
        lux = scenario["lux"]
        temp = scenario["temp_c"]
        gen = scenario["gen_kw"]

        solar_kw = compute_solar_power(lux, temp)
        wind_kw = compute_wind_power(wind)
        heating_kw = compute_thermal_heating(temp, wind)

        # Baseline station load ~18.5 kW without auxiliary
        demand_kw = 18.5 + heating_kw * 0.3
        total_gen = solar_kw + wind_kw + gen
        net_flow = total_gen - demand_kw

        # Emergency check
        soc_pct = (battery_kwh / 160.0) * 100.0
        is_critical = soc_pct < 20.0 or (net_flow < -12.0 and gen == 0.0)

        p1_demand = 19.5
        runtime_hrs = round(battery_kwh / max(0.1, demand_kw - (solar_kw + wind_kw)), 1)
        p1_hrs = round(battery_kwh / max(0.1, p1_demand - (solar_kw + wind_kw)), 1)

        results = {
            "solar_kw": solar_kw,
            "wind_kw": wind_kw,
            "thermal_heating_kw": heating_kw,
            "total_generation_kw": round(total_gen, 2),
            "station_demand_kw": round(demand_kw, 2),
            "net_flow_kw": round(net_flow, 2),
            "mode": "SURVIVAL CRITICAL" if is_critical else "NORMAL OPTIMIZATION",
            "is_critical": is_critical,
            "safe_runtime_hours": runtime_hrs,
            "p1_isolated_hours": p1_hrs
        }

        return {
            "scenario": scenario["name"],
            "scenario_name": scenario["name"],
            "description": scenario["description"],
            "scenario_applied": scenario,
            "inputs": {
                "wind_mps": wind,
                "lux": lux,
                "temp_c": temp,
                "gen_kw": gen,
                "battery_kwh": battery_kwh
            },
            "results": results,
            "state": results
        }
