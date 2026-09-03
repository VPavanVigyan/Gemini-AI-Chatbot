import os
from dotenv import load_dotenv
load_dotenv()

def get_gemini_recommendation(impact, recommendations):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        model = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")

        recs = "\n".join(
            f"- {r['title']}: estimated reduction {r['estimated_reduction']} kg CO2e; "
            f"cost={r['cost_level']}; implementation={r['implementation']}"
            for r in recommendations
        )

        prompt = f"""
You are the AI reasoning layer for CarboNova, an AI-Powered Adaptive Climate Impact Optimizer.
Use only the supplied measurements. Do not invent measurements or claim certainty.
Explain practical interventions while balancing carbon, cost, feasibility and operational continuity.
Return concise plain text with these headings:
Situation
Top action
Why
Next step
Verification

Current modeled impact:
Total carbon: {impact['total_carbon']} kg CO2e
Electricity carbon intensity: {impact.get('carbon_intensity', 'not supplied')} gCO2e/kWh
Electricity: {impact['electricity_kwh']} kWh
Water: {impact['water_liters']} L
Fuel: {impact['fuel_liters']} L
Waste: {impact['waste_kg']} kg
Solar: {impact['solar_kwh']} kWh

Candidate interventions:
{recs}

The candidate list includes current conditions, expected impact, relative cost and cost-benefit scores.
Do not invent monetary prices or scientific removal rates for trees/green infrastructure.
"""
        response = client.models.generate_content(model=model, contents=prompt)
        text = getattr(response, "text", None)
        return text.strip() if text else None
    except Exception as exc:
        return f"Gemini is unavailable right now; the built-in decision engine remains active. ({type(exc).__name__})"
