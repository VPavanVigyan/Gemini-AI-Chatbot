def _num(data, key, default=0.0):
    try:
        return float(data.get(key, default))
    except (TypeError, ValueError):
        return default


def optimize(data, impact):
    """Transparent rule-based optimizer for the CarboNova prototype.

    The optimizer evaluates operational conditions, environmental signals,
    expected environmental benefit, implementation effort and relative cost.
    Scores are intentionally explainable so the recommendations can be audited.
    """
    electricity = impact["electricity_kwh"]
    water = impact["water_liters"]
    fuel = impact["fuel_liters"]
    waste = impact["waste_kg"]
    solar = impact["solar_kwh"]

    temperature = _num(data, "temperature", 23)
    daylight = max(0, min(_num(data, "daylight", 85), 100))
    air_quality = max(0, min(_num(data, "air_quality", 90), 100))
    carbon_intensity = max(_num(data, "carbon_intensity", 150), 0)
    occupancy = max(_num(data, "occupancy", impact.get("occupancy", 0)), 0)
    operating_hours = max(_num(data, "operating_hours", 8), 0)
    operating_condition = str(data.get("operating_condition", "Normal")).strip() or "Normal"

    # Use the submitted grid intensity for adaptive carbon estimates.
    grid_factor = carbon_intensity / 1000 if carbon_intensity > 0 else 0.82
    candidates = []

    def add(title, priority, category, condition, action, impact_text,
            estimated_reduction, cost_level, implementation, benefit, cost):
        benefit = max(float(benefit), 0)
        cost = max(float(cost), 0.1)
        cost_benefit = benefit / cost
        candidates.append({
            "title": title,
            "priority": priority,
            "category": category,
            "current_condition": condition,
            "action": action,
            "expected_impact": impact_text,
            "reason": condition,
            "estimated_reduction": round(max(estimated_reduction, 0), 2),
            "cost_level": cost_level,
            "implementation": implementation,
            "cost_benefit_score": round(cost_benefit, 2)
        })

    # 1. Daylight -> reduce unnecessary artificial lighting.
    if daylight >= 70 and electricity > 0:
        reduction = electricity * min(0.06 + (daylight - 70) / 1000, 0.12) * grid_factor
        add(
            "Reduce unnecessary artificial lighting", "High", "Lighting",
            f"High daylight availability ({daylight:.0f}%).",
            "Dim or switch off non-essential artificial lighting in daylit zones and use occupancy controls where available.",
            "↓ Energy and ↓ CO₂",
            reduction, "Low", "Low", reduction * 1.25, 1.0
        )

    # 2. Temperature + occupancy -> adaptive cooling.
    if temperature >= 26 and electricity > 0 and occupancy > 0:
        reduction = electricity * min(0.08 + max(temperature - 26, 0) * 0.015, 0.18) * grid_factor
        add(
            "Optimize cooling to temperature and occupancy", "High", "HVAC",
            f"High temperature ({temperature:.1f} °C) with an occupancy level of {occupancy:.0f}.",
            "Adjust cooling schedules and setpoints to actual occupancy and outdoor temperature while maintaining required comfort.",
            "↓ Energy and ↓ CO₂",
            reduction, "Low", "Medium", reduction * 1.4, 1.2
        )

    # 3. High grid intensity -> shift flexible loads.
    if carbon_intensity >= 500 and electricity > 0 and operating_hours > 0:
        reduction = electricity * 0.08 * grid_factor
        add(
            "Shift flexible electricity loads", "High", "Electricity",
            f"High electricity carbon intensity ({carbon_intensity:.0f} gCO₂e/kWh).",
            "Move flexible charging, pumping, heating or other deferrable loads toward lower-carbon operating periods.",
            "↓ CO₂",
            reduction, "Low", "Medium", reduction * 1.5, 1.0
        )

    # 4. Water conservation.
    if water > 1000:
        reduction = water * 0.10 * 0.0003
        add(
            "Reduce avoidable water usage", "Medium", "Water",
            f"Water demand is {water:.0f} L/day.",
            "Check leaks and optimize irrigation, cleaning and other high-consumption schedules.",
            "↓ Water and ↓ resource-related CO₂",
            reduction, "Low", "Low", max(reduction, 0.5) * 1.2, 1.0
        )

    # 5. Green-area / tree intervention. This is a planning recommendation,
    # not a claim that a specific number of trees will remove a fixed amount.
    if air_quality < 60 or daylight < 45:
        add(
            "Prioritize trees and green-area interventions", "Medium", "Green infrastructure",
            f"Environmental quality score is {air_quality:.0f}/100.",
            "Evaluate shade trees, native planting and additional green areas where site conditions permit; pair with local air-quality monitoring.",
            "↑ Environmental quality and potential cooling benefit",
            0, "Medium", "Medium", 1.0, 2.0
        )

    # 6. Poor air quality -> monitoring/mitigation.
    if air_quality < 60:
        add(
            "Increase air-quality monitoring and mitigation", "Medium", "Environment",
            f"Air-quality score is {air_quality:.0f}/100.",
            "Increase monitoring frequency and investigate practical ventilation, filtration or source-control measures appropriate to the building.",
            "↑ Environmental quality",
            0, "Medium", "Medium", 1.1, 2.0
        )

    if solar < electricity * 0.25 and electricity > 100:
        reduction = min(electricity * 0.18, electricity) * grid_factor
        add(
            "Increase renewable electricity utilization", "Medium", "Energy",
            f"Solar generation ({solar:.0f} kWh) is low relative to electricity demand ({electricity:.0f} kWh).",
            "Evaluate additional solar generation or increase use of existing solar during high-load periods.",
            "↓ Grid electricity and ↓ CO₂",
            reduction, "Medium", "Medium", reduction * 1.15, 2.0
        )

    if fuel > 20:
        reduction = fuel * 0.15 * 2.31
        add(
            "Reduce unnecessary fuel usage", "Medium", "Mobility",
            f"Fuel use is {fuel:.1f} L/day.",
            "Consolidate trips, improve route planning and prioritize lower-emission mobility where practical.",
            "↓ Fuel and ↓ CO₂",
            reduction, "Low", "Medium", reduction * 1.1, 1.0
        )

    if waste > 50:
        reduction = waste * 0.12 * 0.45
        add(
            "Improve waste segregation and diversion", "Low", "Waste",
            f"Waste is {waste:.1f} kg/day.",
            "Increase source segregation and divert recyclable or compostable material where local facilities support it.",
            "↓ Waste and ↓ CO₂",
            reduction, "Low", "Low", reduction * 1.0, 1.0
        )

    if operating_condition.lower() in {"peak", "strained", "high load"}:
        add(
            "Prioritize flexible-load scheduling", "High", "Operations",
            f"Building/campus condition is {operating_condition}.",
            "Identify deferrable processes and schedule them outside constrained operating periods.",
            "↓ Peak demand and potentially ↓ CO₂",
            electricity * 0.03 * grid_factor,
            "Low", "Low", max(electricity * 0.03 * grid_factor, 0.5), 0.8
        )

    if not candidates:
        candidates.append({
            "title": "Start collecting a baseline",
            "priority": "High",
            "category": "Data",
            "current_condition": "Not enough signals triggered a specific intervention.",
            "action": "Record energy, water, environmental and operational data regularly so CarboNova can identify trends.",
            "expected_impact": "↑ Decision confidence",
            "reason": "A reliable baseline is needed before optimization can be trusted.",
            "estimated_reduction": 0,
            "cost_level": "Low",
            "implementation": "Low",
            "cost_benefit_score": 0
        })

    priority_weight = {"High": 3, "Medium": 2, "Low": 1}
    for item in candidates:
        # Environmental benefit gets the strongest weight, with feasibility/cost
        # and priority acting as tie-breakers.
        item["score"] = round(
            item["estimated_reduction"] * 0.60
            + item["cost_benefit_score"] * 1.5
            + priority_weight[item["priority"]] * 2,
            2
        )

    return sorted(candidates, key=lambda x: x["score"], reverse=True)[:7]
