"""Aerodynamic wind turbine power forecasting for polar microgrid."""

def compute_wind_power(wind_mps: float, air_density: float = 1.34, swept_area_m2: float = 16.0) -> float:
    """
    Aerodynamic wind power curve:
    - Cut-in wind speed: 3.0 m/s (below this, 0 kW)
    - Rated wind speed: 12.0 m/s
    - Storm cut-out speed: 25.0 m/s (safety feathering)
    - Air density rho = 1.34 kg/m³ for high-density sub-zero polar air
    - Cp (aerodynamic power coefficient) ~ 0.42
    """
    v = float(wind_mps)

    if v < 3.0 or v > 25.0:
        return 0.0

    # Between cut-in and rated: P = 0.5 * rho * A * v^3 * Cp
    effective_v = min(v, 12.0)
    # Power in Watts -> convert to kW (/ 1000.0)
    power_kw = 0.5 * air_density * swept_area_m2 * (effective_v ** 3) * 0.00042

    # Above rated up to cut-out: maintain rated plateau with slight gust modulation
    if v > 12.0:
        rated_cap = 0.5 * air_density * swept_area_m2 * (12.0 ** 3) * 0.00042
        gust_bonus = (v - 12.0) * 0.08
        power_kw = min(rated_cap * 1.15, rated_cap + gust_bonus)

    return round(max(0.0, power_kw), 3)

