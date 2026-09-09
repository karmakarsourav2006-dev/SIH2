"""Physics-based polar solar photovoltaic forecasting."""

def compute_solar_power(lux: float, temp_c: float = -28.0, snow_occlusion: float = 0.05) -> float:
    """
    Computes PV output in kW:
    - Base rating 25.0 kW array
    - Temperature coefficient (+0.35%/°C gain below 25°C standard test condition)
    - Snow occlusion factor (0.0 to 1.0 derating)
    - Tilt factor (~0.88 for polar latitude optimization)
    """
    if lux <= 0.0:
        return 0.0

    # Temperature efficiency boost for sub-zero silicon PV
    delta_t = 25.0 - temp_c
    temp_multiplier = 1.0 + (delta_t * 0.0035)
    
    # Snow derating
    occlusion_multiplier = max(0.0, 1.0 - snow_occlusion)

    normalized_irradiance = lux / 1000.0
    solar_kw = normalized_irradiance * 25.0 * 0.88 * temp_multiplier * occlusion_multiplier
    return round(max(0.0, solar_kw), 3)

