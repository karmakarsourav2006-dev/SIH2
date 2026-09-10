from typing import List, Dict, Any

class EnergyOptimizer:
    """
    Multi-source power optimization & Green Window scheduling engine:
    1. Priority 1: Direct Solar & Wind renewable consumption
    2. Priority 2: Battery Energy Storage System (BESS) buffering (if SoC > 25%)
    3. Priority 3: Diesel Genset modulation to fill deficits and protect BESS
    """

    @staticmethod
    def optimize_dispatch(
        total_renewables_kw: float,
        active_demand_kw: float,
        battery_kwh: float,
        battery_capacity_kwh: float,
        generator_kw: float
    ) -> Dict[str, Any]:
        soc_pct = max(0.0, min(100.0, (battery_kwh / max(1.0, battery_capacity_kwh)) * 100.0))
        deficit_kw = active_demand_kw - total_renewables_kw

        bess_discharge_kw = 0.0
        bess_charge_kw = 0.0
        genset_recommended_kw = generator_kw
        unmet_demand_kw = 0.0

        if deficit_kw <= 0.0:
            # Renewable surplus
            surplus_kw = abs(deficit_kw)
            # Maximum charge rate (C-rate 0.5 ~ 80 kW max)
            max_charge_rate = battery_capacity_kwh * 0.4
            headroom_kwh = battery_capacity_kwh - battery_kwh
            bess_charge_kw = min(surplus_kw, max_charge_rate, headroom_kwh * 2.0)
            genset_recommended_kw = 0.0
        else:
            # Renewable deficit
            if soc_pct > 25.0:
                # BESS can buffer part or all of deficit
                max_discharge_rate = battery_capacity_kwh * 0.5
                available_battery_kw = min(deficit_kw, max_discharge_rate, (battery_kwh - (battery_capacity_kwh * 0.20)) * 2.0)
                bess_discharge_kw = max(0.0, available_battery_kw)
                remaining_deficit = deficit_kw - bess_discharge_kw
            else:
                remaining_deficit = deficit_kw

            if remaining_deficit > 0.0:
                genset_recommended_kw = min(40.0, max(generator_kw, remaining_deficit))
                if genset_recommended_kw < remaining_deficit:
                    unmet_demand_kw = remaining_deficit - genset_recommended_kw

        return {
            "dispatch_priority": "RENEWABLE -> BESS -> GENSET",
            "bess_discharge_kw": round(bess_discharge_kw, 2),
            "bess_charge_kw": round(bess_charge_kw, 2),
            "genset_recommended_kw": round(genset_recommended_kw, 2),
            "unmet_demand_kw": round(unmet_demand_kw, 2),
            "green_energy_ratio_pct": round(min(100.0, (total_renewables_kw / max(0.01, active_demand_kw)) * 100.0), 1)
        }

    @staticmethod
    def calculate_green_windows(
        forecast_timeline: List[Dict[str, float]],
        required_kwh: float,
        duration_hrs: float
    ) -> List[Dict[str, Any]]:
        """Finds time slots where renewable surplus is sufficient to run experiments without carbon footprint."""
        avg_kw_needed = required_kwh / max(0.5, duration_hrs)
        windows = []

        for slot in forecast_timeline:
            surplus = slot.get("surplus_kw", 0.0)
            if surplus >= avg_kw_needed:
                windows.append({
                    "slot": slot.get("time_label", "Peak Window"),
                    "confidence": "HIGH",
                    "surplus_kw": surplus,
                    "carbon_saving_kg": round(required_kwh * 0.72, 2)
                })

        return windows

