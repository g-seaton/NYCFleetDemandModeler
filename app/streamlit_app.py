from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fleetopt.optimization import optimize_repositioning

st.set_page_config(page_title="NYC Fleet Optimizer", page_icon="🚕", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1400px;}
[data-testid="stMetric"] {background: rgba(120,120,120,0.08); padding: 14px; border-radius: 14px;}
</style>
""", unsafe_allow_html=True)

st.title("🚕 NYC Dynamic Fleet Repositioning")
st.caption("Demand forecasting → mathematical optimization → operational simulation")

artifacts = ROOT / "artifacts"
zones_path = ROOT / "data" / "processed" / "demo_zones.csv"
cost_path = ROOT / "data" / "processed" / "demo_travel_minutes.csv"
pred_path = artifacts / "predictions.csv"
metrics_path = artifacts / "policy_comparison.csv"

if not all(p.exists() for p in [zones_path, cost_path, pred_path]):
    st.warning("Run `make demo` first to generate the demo artifacts.")
    st.stop()

zones = pd.read_csv(zones_path)
cost_df = pd.read_csv(cost_path, index_col=0)
costs = cost_df.to_numpy(float)
pred = pd.read_csv(pred_path, parse_dates=["window_start"])

latest_times = sorted(pred.window_start.unique())
selected_time = st.select_slider("Decision interval", options=latest_times, value=latest_times[-1])
frame = pred[pred.window_start == selected_time].copy().sort_values("zone_id")

# Use forecast demand as a transparent fleet-state proxy for the interactive one-step demo.
base_total = max(120, int(frame.demand.sum() * 1.05))
weights = (frame.demand.to_numpy() + 1) / (frame.demand.sum() + len(frame))
vehicles = np.floor(weights * base_total).astype(int)
# Introduce realistic imbalance so repositioning is visible.
if len(vehicles) >= 4:
    transfer = min(12, vehicles[0] // 2)
    vehicles[0] -= transfer
    vehicles[-1] += transfer
vehicle_map = {int(z): int(v) for z, v in zip(frame.zone_id, vehicles)}
demand_map = {int(z): float(p) for z, p in zip(frame.zone_id, frame.prediction)}

with st.sidebar:
    st.header("Optimization controls")
    unmet_penalty = st.slider("Unmet demand penalty", 5.0, 50.0, 20.0, 1.0)
    move_cost = st.slider("Move cost / vehicle-minute", 0.05, 1.00, 0.35, 0.05)
    max_move = st.slider("Max reposition time (min)", 10, 60, 35, 5)
    solver = st.selectbox("Solver", ["auto", "scipy", "gurobi"])

result = optimize_repositioning(
    vehicle_map, demand_map, costs,
    unmet_penalty=unmet_penalty,
    reposition_cost_per_minute=move_cost,
    max_reposition_minutes=float(max_move),
    solver=solver,
)

post = pd.Series(result.post_reposition_vehicles)
frame["vehicles_before"] = frame.zone_id.map(vehicle_map)
frame["vehicles_after"] = frame.zone_id.map(post)
frame = frame.merge(zones, on="zone_id", how="left")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Forecast demand", f"{frame.prediction.sum():.0f}")
c2.metric("Vehicles moved", f"{sum(m['vehicles'] for m in result.moves):,.0f}")
c3.metric("Predicted uncovered", f"{sum(result.unmet_demand.values()):.1f}")
c4.metric("Solver", result.solver)

left, right = st.columns([1.35, 1])
with left:
    st.subheader("Supply vs forecast demand")
    long = frame.melt(
        id_vars=["zone_name"], value_vars=["prediction", "vehicles_before", "vehicles_after"],
        var_name="series", value_name="count"
    )
    fig = px.bar(long, x="zone_name", y="count", color="series", barmode="group", height=460)
    fig.update_layout(xaxis_title="", yaxis_title="Vehicles / trips", legend_title="")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Demand map")
    fig = px.scatter_map(
        frame, lat="lat", lon="lon", size="prediction", color="prediction",
        hover_name="zone_name", hover_data=["vehicles_before", "vehicles_after"],
        zoom=9.6, height=460, map_style="carto-positron"
    )
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Recommended moves")
if result.moves:
    move_df = pd.DataFrame(result.moves)
    name_map = zones.set_index("zone_id").zone_name.to_dict()
    move_df["origin_name"] = move_df.origin.map(name_map)
    move_df["destination_name"] = move_df.destination.map(name_map)
    st.dataframe(move_df[["origin_name", "destination_name", "vehicles"]], use_container_width=True, hide_index=True)
else:
    st.success("No repositioning is needed under the current settings.")

if metrics_path.exists():
    st.subheader("Rolling simulation comparison")
    comparison = pd.read_csv(metrics_path)
    fig = px.bar(comparison, x="policy", y="service_rate", text_auto=".2%", height=360)
    fig.update_yaxes(tickformat=".0%", range=[max(0, comparison.service_rate.min() - 0.05), 1])
    st.plotly_chart(fig, use_container_width=True)
