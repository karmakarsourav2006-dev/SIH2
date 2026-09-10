from typing import Dict

def forecast_generation(wind_mps: float, lux: float, temp_c: float, gen_kw: float) -> Dict[str, float]:
    """
    Computes physics-grounded generation for sub-zero polar environment:
    - Solar PV accounting for polar tilt and albedo: (lux / 1000.0) * 25.0 * 0.88
    - Wind Turbines with high-density polar air (1.34 kg/m³): 0.5 * 1.34 * 16.0 * min(wind, 25)^3 * 0.00042
    - Dynamic Thermal Heating baseline based on ambient sub-zero temperature
    """
    # 1. Solar generation with sub-zero bifacial gain and panel efficiency
    solar_kw = round(max(0.0, (lux / 1000.0) * 25.0 * 0.88), 3)

    # 2. Wind generation with polar air density calibration
    effective_wind = min(wind_mps, 25.0)
    wind_kw = round(max(0.0, 0.5 * 1.34 * 16.0 * (effective_wind ** 3) * 0.00042), 3)

    # 3. Dynamic Thermal Loop Heating demand
    sub_zero_delta = abs(min(0.0, temp_c))
    heating_kw = round(max(8.0, 14.0 + (sub_zero_delta * 0.18)), 2)

    total_renewables = round(solar_kw + wind_kw, 3)
    total_gen = round(total_renewables + gen_kw, 3)

    return {
        "solar_kw": solar_kw,
        "wind_kw": wind_kw,
        "total_renewables": total_renewables,
        "gen_kw": round(gen_kw, 2),
        "total_gen": total_gen,
        "thermal_heating_demand_kw": heating_kw
    }

