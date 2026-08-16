import numpy as np
import pandas as pd

def risk(peak, capacity):
    ratio = peak / capacity
    if ratio >= 1.0: return "HIGH"
    if ratio >= 0.92: return "MEDIUM"
    return "LOW"

def score_strategy(post_peak, capacity, battery_mw, battery_available, ev_reduction_mw, ev_load):
    overload = max(0, post_peak - capacity)
    reliability = max(0, 100 - overload * 20)
    bf = battery_mw / max(battery_available, 0.1) if battery_available else 0
    battery_score = max(0, 100 - bf * 30)
    customer_impact = ev_reduction_mw / max(ev_load, 0.1) * 100
    customer_score = max(0, 100 - customer_impact * 0.8)
    reserve_score = max(0, 100 - bf * 40)
    return reliability*.45 + customer_score*.20 + battery_score*.15 + reserve_score*.20

def optimize_scenario(base_demand, temperature, ev_load, solar, battery_power, battery_soc, ev_flex_pct, capacity):
    baseline = base_demand + max(0, temperature-80)*.30 + ev_load*.35 - solar*.20
    usable_battery = battery_power
    if battery_soc < 30: usable_battery *= .50
    elif battery_soc < 50: usable_battery *= .75
    max_ev_reduction = ev_load * ev_flex_pct / 100
    strategies = [
        ("Do Nothing", 0, 0),
        ("Battery Only", usable_battery, 0),
        ("EV Managed Charging Only", 0, max_ev_reduction),
        ("Battery + EV Managed Charging", usable_battery, max_ev_reduction),
    ]
    alternatives = []
    for label, batt, ev in strategies:
        post = max(0, baseline-batt-ev)
        impact = ev/max(ev_load,.1)*100
        alternatives.append({
            "label":label, "battery_mw":batt, "ev_reduction_mw":ev,
            "post_peak":post, "reduction":baseline-post,
            "customer_impact":f"{impact:.0f}%", 
            "score":score_strategy(post,capacity,batt,usable_battery,ev,ev_load)
        })
    best=max(alternatives,key=lambda x:x["score"])
    actions=[]
    if best["battery_mw"]>0:
        actions.append({"Resource":"Battery","Action":"Discharge","Power":f"{best['battery_mw']:.1f} MW","Duration":"30 min"})
    if best["ev_reduction_mw"]>0:
        actions.append({"Resource":"Opted-in EVs","Action":"Throttle / shift charging","Power Reduction":f"{best['ev_reduction_mw']:.1f} MW","Duration":"30 min"})
    if not actions: actions=[{"Resource":"None","Action":"Continue monitoring","Power":"0 MW","Duration":"—"}]
    best["actions"]=actions
    return {"baseline_peak":baseline,"capacity":capacity,"best":best,"alternatives":alternatives,
            "risk_before":risk(baseline,capacity),"risk_after":risk(best["post_peak"],capacity),
            "inputs":{"base_demand":base_demand,"temperature":temperature,"ev_load":ev_load,"solar":solar}}

def explain_strategy(r):
    b=r["best"]
    out=[f"Forecast peak is {r['baseline_peak']:.1f} MW against a {r['capacity']:.1f} MW limit.",
         f"The selected strategy reduces the modeled peak by {b['reduction']:.1f} MW."]
    if b["battery_mw"]>0: out.append(f"Battery discharge contributes {b['battery_mw']:.1f} MW.")
    if b["ev_reduction_mw"]>0: out.append(f"Opted-in EV flexibility contributes {b['ev_reduction_mw']:.1f} MW.")
    out.append("The score balances reliability, customer impact, battery use and reserve.")
    return out

def build_timeline(r):
    x=r["inputs"]; h=np.arange(24)
    demand=x["base_demand"]+7*np.exp(-((h-18)/4)**2)+max(0,x["temperature"]-80)*.18
    ev=x["ev_load"]*np.exp(-((h-19)/3)**2)
    solar=x["solar"]*np.exp(-((h-13)/3.2)**2)
    baseline=demand+ev-solar
    reduction=r["best"]["reduction"]*np.exp(-((h-18)/2.5)**2)
    return pd.DataFrame({"hour":[f"{i:02d}:00" for i in h],"baseline_mw":baseline.round(2),
                         "optimized_mw":(baseline-reduction).round(2),"capacity_mw":r["capacity"]})
