"""Thermodynamic habitat building envelope heating forecast."""

def compute_thermal_heating(temp_c: float, wind_mps: float, r_value: float = 35.0, interior_setpoint_c: float = 20.0) -> float:
    """
    Computes thermal heating load in kW:
    - Base habitat enclosure thermal conduction: Q_cond = (Area / R) * Delta_T
    - Convective windchill infiltration factor: increases loss with high wind
    - Minimum baseline circulation pump power: 8.0 kW
    """
    delta_t = max(0.0, interior_setpoint_c - temp_c)
    
    # Wind convective coefficient factor (windchill infiltration)
    wind_factor = 1.0 + (max(0.0, wind_mps - 5.0) * 0.025)
    
    # Enclosure conduction loss factor
    conduction_kw = (delta_t / r_value) * 12.0
    
    total_heating_kw = (8.0 + conduction_kw) * wind_factor
    return round(max(8.0, min(35.0, total_heating_kw)), 2)

