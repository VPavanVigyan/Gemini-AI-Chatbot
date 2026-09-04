import os
from dotenv import load_dotenv

load_dotenv()


def env_float(name, default):
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


ELECTRICITY_FACTOR = env_float("ELECTRICITY_FACTOR", 0.82)
FUEL_FACTOR = env_float("FUEL_FACTOR", 2.31)
WATER_FACTOR = env_float("WATER_FACTOR", 0.0003)
WASTE_FACTOR = env_float("WASTE_FACTOR", 0.45)


def safe_float(value, default=0):
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def calculate_impact(data):
    electricity = max(safe_float(data.get("electricity_kwh")), 0)
    water = max(safe_float(data.get("water_liters")), 0)
    fuel = max(safe_float(data.get("fuel_liters")), 0)
    waste = max(safe_float(data.get("waste_kg")), 0)
    solar = max(safe_float(data.get("solar_kwh")), 0)
    cost = max(safe_float(data.get("energy_cost")), 0)
    occupancy = max(int(safe_float(data.get("occupancy"))), 0)

    # Live/site-specific electricity carbon intensity
    intensity = max(safe_float(data.get("carbon_intensity")), 0)

    electricity_factor = (
        intensity / 1000
        if intensity > 0
        else ELECTRICITY_FACTOR
    )

    grid_carbon = electricity * electricity_factor

    solar_offset = min(solar, electricity) * electricity_factor

    electricity_carbon = max(
        grid_carbon - solar_offset,
        0
    )

    fuel_carbon = fuel * FUEL_FACTOR
    water_carbon = water * WATER_FACTOR
    waste_carbon = waste * WASTE_FACTOR

    total = (
        electricity_carbon
        + fuel_carbon
        + water_carbon
        + waste_carbon
    )

    return {
        "electricity_carbon": round(electricity_carbon, 2),
        "fuel_carbon": round(fuel_carbon, 2),
        "water_carbon": round(water_carbon, 2),
        "waste_carbon": round(waste_carbon, 2),
        "solar_offset": round(solar_offset, 2),
        "total_carbon": round(total, 2),
        "energy_cost": round(cost, 2),
        "occupancy": occupancy,
        "electricity_kwh": electricity,
        "water_liters": water,
        "fuel_liters": fuel,
        "waste_kg": waste,
        "solar_kwh": solar,
        "carbon_intensity": round(
            intensity if intensity else ELECTRICITY_FACTOR * 1000,
            2
        )
    }