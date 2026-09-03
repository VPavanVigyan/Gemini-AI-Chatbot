# CarboNova
### An AI-Powered Adaptive Climate Impact Optimizer

## Run it in VS Code on Windows

```powershell
py -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Open `http://127.0.0.1:5000`.

Add your Gemini API key to `.env` to enable the optional Gemini reasoning layer. The built-in calculation and optimization engine works without Gemini.

## Main architecture

Browser UI → Flask REST API → SQLite + calculation engine → optimization engine → optional Gemini reasoning → recommendation → what-if simulation → predicted vs actual verification.

## Files

- `app.py` — Flask routes, authentication, database and API endpoints
- `templates/` — HTML pages
- `static/css/style.css` — light-only design
- `static/js/app.js` — dashboard interactions
- `services/calculator.py` — carbon/resource calculations
- `services/optimizer.py` — transparent intervention ranking
- `services/gemini_service.py` — optional Gemini API integration
- `data/emission_factors.json` — prototype factors
- `.env` — local secrets; never upload it to GitHub

The prototype factors are placeholders for a hackathon demo. Document and replace them with the emission factors you choose for the final presentation.

## Adaptive optimization inputs

The dashboard assessment form now accepts temperature, daylight availability, air/environment quality, electricity carbon intensity, operating hours and building/campus operating condition in addition to energy, water, fuel, waste, solar, occupancy and energy cost.

The optimizer evaluates:
- unnecessary artificial lighting during high daylight
- adaptive cooling using temperature and occupancy
- flexible-load shifting when electricity carbon intensity is high
- water conservation
- tree/green-area interventions when environmental conditions warrant site planning
- air-quality monitoring/mitigation
- renewable electricity utilization
- fuel and waste reduction
- peak/strained operating conditions

Recommendations are ranked using estimated environmental benefit plus relative cost/feasibility and operational priority. The environmental table shows the current condition, recommended action and expected impact.

### Important modeling note

The electricity carbon-intensity field is used as an adaptive prototype factor when supplied. The values in `data/emission_factors.json` remain demonstration defaults and should be replaced with region/site-specific factors before deployment or a formal environmental claim.
