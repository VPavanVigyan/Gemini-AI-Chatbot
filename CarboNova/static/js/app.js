function openModal(id){document.getElementById(id)?.classList.add("open")}
function closeModal(id){document.getElementById(id)?.classList.remove("open")}

const menuButton=document.getElementById("menuButton");
const sidebar=document.getElementById("sidebar");
if(menuButton&&sidebar){menuButton.addEventListener("click",()=>sidebar.classList.toggle("open"))}

document.querySelectorAll(".modal-backdrop").forEach(m=>m.addEventListener("click",e=>{if(e.target===m)m.classList.remove("open")}));

const form=document.getElementById("assessmentForm");
if(form){
form.addEventListener("submit",async e=>{
e.preventDefault();
const status=document.getElementById("analysisStatus");
status.textContent="Analyzing data and ranking interventions...";
status.className="analysis-status loading";
const data=Object.fromEntries(new FormData(form).entries());
const numericFields=[
"electricity_kwh","water_liters","fuel_liters","waste_kg","solar_kwh",
"occupancy","energy_cost","temperature","daylight","air_quality",
"carbon_intensity","operating_hours"
];
numericFields.forEach(k=>data[k]=Number(data[k]||0));
try{
const r=await fetch("/api/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
const d=await r.json();
if(!r.ok||!d.ok)throw new Error(d.error||"Analysis failed");
status.textContent=`Done. Modeled carbon: ${d.impact.total_carbon} kg CO₂e.`;
status.className="analysis-status success";
setTimeout(()=>location.reload(),700);
}catch(err){status.textContent=err.message;status.className="analysis-status error"}
});
}

function slider(id,out,suffix){
const el=document.getElementById(id),o=document.getElementById(out);
if(!el||!o)return;
const update=()=>o.textContent=el.value+suffix;
el.addEventListener("input",update);update();
}
slider("elecSlider","elecOut","%");
slider("waterSlider","waterOut","%");
slider("solarSlider","solarOut"," kWh");

async function runWhatIf(){
const result=document.getElementById("whatIfResult");
if(!result)return;
result.textContent="Simulating...";
const payload={
electricity_kwh:Number("{{ latest['electricity_kwh'] if latest else 0 }}"),
water_liters:Number("{{ latest['water_liters'] if latest else 0 }}"),
fuel_liters:Number("{{ latest['fuel_liters'] if latest else 0 }}"),
waste_kg:Number("{{ latest['waste_kg'] if latest else 0 }}"),
solar_kwh:Number("{{ latest['solar_kwh'] if latest else 0 }}"),
carbon_intensity:Number("{{ latest['carbon_intensity'] if latest and latest['carbon_intensity'] else 150 }}"),
electricity_reduction_pct:Number(document.getElementById("elecSlider")?.value||0),
water_reduction_pct:Number(document.getElementById("waterSlider")?.value||0),
solar_addition_kwh:Number(document.getElementById("solarSlider")?.value||0)
};
try{
const r=await fetch("/api/what-if",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
const d=await r.json();
if(!r.ok)throw new Error(d.error||"Simulation failed");
result.innerHTML=`<b>${d.saved.toFixed(1)} kg CO₂e modeled reduction</b><br><span>${d.baseline.toFixed(1)} → ${d.scenario.toFixed(1)} kg CO₂e</span>`;
}catch(e){result.textContent=e.message}
}

async function verifyOutcome(id){
const result=document.getElementById("verifyResult");
const actual=Number(document.getElementById("actualReduction")?.value||0);
if(!actual){result.textContent="Enter the measured reduction first.";return}
try{
const r=await fetch("/api/verify/"+id,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({actual_reduction:actual})});
const d=await r.json();
if(!r.ok)throw new Error(d.error||"Verification failed");
const direction=d.variance>=0?"above":"below";
result.innerHTML=`<b>Verified.</b> Actual impact is ${Math.abs(d.variance).toFixed(1)} kg ${direction} the prediction.`;
}catch(e){result.textContent=e.message}
}
