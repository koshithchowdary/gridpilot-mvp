import streamlit as st
import pandas as pd
from optimizer import optimize_scenario, build_timeline, explain_strategy

st.set_page_config(page_title="GridPilot MVP", page_icon="⚡", layout="wide")
st.title("⚡ GridPilot")
st.caption("Substation Peak Management MVP • Explainable decision support")

with st.sidebar:
    st.header("Scenario Inputs")
    st.caption("Synthetic data for demonstration")
    temperature = st.slider("Temperature (°F)", 70, 105, 98)
    base_demand = st.slider("Base demand (MW)", 70.0, 100.0, 88.0, 0.5)
    ev_load = st.slider("EV charging load (MW)", 0.0, 10.0, 5.0, 0.1)
    solar = st.slider("Solar generation (MW)", 0.0, 15.0, 4.0, 0.1)
    battery_power = st.slider("Available battery discharge (MW)", 0.0, 8.0, 3.0, 0.1)
    battery_soc = st.slider("Battery SOC (%)", 10, 100, 80)
    ev_flex = st.slider("Opted-in EV flexibility (%)", 0, 100, 50)
    capacity = st.slider("Substation capacity (MW)", 90.0, 120.0, 100.0, 0.5)

result = optimize_scenario(base_demand, temperature, ev_load, solar,
                           battery_power, battery_soc, ev_flex, capacity)

c1,c2,c3,c4 = st.columns(4)
c1.metric("Forecast Peak", f"{result['baseline_peak']:.1f} MW")
c2.metric("Peak After Action", f"{result['best']['post_peak']:.1f} MW",
          f"{result['best']['reduction']:.1f} MW lower")
c3.metric("Risk", result["risk_after"])
c4.metric("GridPilot Score", f"{result['best']['score']:.0f}/100")

st.subheader("Substation Health")
loading = result["baseline_peak"] / capacity
st.progress(min(loading, 1.0))
st.write(f"Forecast loading: **{loading*100:.1f}%** · Capacity: **{capacity:.1f} MW**")

if result["risk_before"] == "HIGH":
    st.error("⚠️ Forecast exceeds the modeled substation limit.")
elif result["risk_before"] == "MEDIUM":
    st.warning("⚠️ Forecast is approaching the modeled substation limit.")
else:
    st.success("✅ Forecast remains within the modeled limit.")

st.subheader("GridPilot Recommendation")
st.success(result["best"]["label"])

left, right = st.columns(2)
with left:
    st.markdown("### Recommended actions")
    st.dataframe(pd.DataFrame(result["best"]["actions"]), use_container_width=True, hide_index=True)
with right:
    st.markdown("### Why?")
    for item in explain_strategy(result):
        st.write("• " + item)

st.subheader("Compare All Strategies")
comparison = pd.DataFrame([
    {"Strategy":x["label"], "Peak After (MW)":round(x["post_peak"],1),
     "Peak Reduction (MW)":round(x["reduction"],1),
     "Customer Impact":x["customer_impact"],
     "Battery Used (MW)":round(x["battery_mw"],1),
     "Score":round(x["score"],0)}
    for x in result["alternatives"]
]).sort_values("Score", ascending=False)
st.dataframe(comparison, use_container_width=True, hide_index=True)

st.subheader("24-Hour Synthetic Load Profile")
timeline = build_timeline(result)
st.line_chart(timeline.set_index("hour")[["baseline_mw","optimized_mw","capacity_mw"]])

st.subheader("Human-in-the-Loop")
a,b,c = st.columns(3)
if a.button("✅ Approve Recommendation", use_container_width=True):
    st.session_state["decision"] = "APPROVED"
if b.button("✏️ Modify Recommendation", use_container_width=True):
    st.session_state["decision"] = "MODIFIED"
if c.button("❌ Reject Recommendation", use_container_width=True):
    st.session_state["decision"] = "REJECTED"

decision = st.session_state.get("decision")
if decision == "APPROVED":
    st.success("Recommendation approved — simulation only. No physical grid equipment is controlled.")
elif decision == "MODIFIED":
    st.warning("Recommendation marked for operator modification — simulation only.")
elif decision == "REJECTED":
    st.error("Recommendation rejected — simulation only.")

with st.expander("How GridPilot works"):
    st.markdown("""
**Forecast demand → Detect constraint → Find flexibility → Compare strategies → Explain → Human approval**

This MVP uses synthetic data and does not connect to FPL or any live utility system.
""")
st.caption("GridPilot MVP • Decision support, not autonomous grid control.")
