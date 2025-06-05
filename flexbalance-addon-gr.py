import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Settings ---
st.set_page_config(layout="wide")
st.title("Imbalance Data Monitoring Dashboard")

# --- Sidebar Global Controls ---
st.sidebar.header("Global Controls")
selected_date = st.sidebar.date_input("Select Date", datetime.utcnow().date())
selected_time = st.sidebar.time_input("Select Time", datetime.utcnow().time())
site_options = ["All Sites", "Site A", "Site B", "Site C"]
selected_sites = st.sidebar.multiselect("Select Site(s)", site_options, default=["All Sites"])

# Combine into a full datetime
selected_datetime = datetime.combine(selected_date, selected_time)

# Round down to the nearest hour or 15-min PTU if needed
now = selected_datetime.replace(minute=0, second=0, microsecond=0)

if "All Sites" in selected_sites:
    selected_sites = ["Site A", "Site B", "Site C"]

resource_filter = st.sidebar.selectbox("Resource Type", ["All", "Boilers", "Chillers", "Pumps"])
show_alerts = st.sidebar.checkbox("Show Alerts", value=True)
imbalance_threshold = st.sidebar.slider("Imbalance Alert Threshold (MW)", 0, 20, 5)

if st.sidebar.button("Refresh Data"):
    st.experimental_rerun()

st.sidebar.download_button("Download Data", data="", file_name="mock_data.csv", disabled=True)

# --- Generate Synthetic Data ---
def generate_data(now):
    index = pd.date_range(now - timedelta(hours=8), now + timedelta(hours=8), freq="15min")
    df = pd.DataFrame(index=index)
    df.index.name = "timestamp"

    for site in ["Site A", "Site B", "Site C"]:
        df[f"scheduled_{site}"] = np.random.normal(50, 10, len(df))
        df[f"actual_{site}"] = df[f"scheduled_{site}"] + np.random.normal(0, 5, len(df))
        df[f"imbalance_{site}"] = df[f"actual_{site}"] - df[f"scheduled_{site}"]

    df["imbalance_price"] = np.random.uniform(0, 200, len(df))
    df["balancing_activations"] = np.random.binomial(1, 0.2, len(df)) * np.random.uniform(5, 15, len(df))
    df["alerts"] = np.abs(df[f"imbalance_Site A"]) > imbalance_threshold
    return df

now = selected_datetime.replace(minute=0, second=0, microsecond=0)
df = generate_data(now)

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["Portfolio Overview", "Site-Level Flex", "Market & Schedule"])

# --- Tab 1: Portfolio Overview ---
with tab1:
    st.subheader("Aggregated Portfolio Consumption")
    df["total_scheduled"] = df[[f"scheduled_{s}" for s in selected_sites]].sum(axis=1)
    df["total_actual"] = df[[f"actual_{s}" for s in selected_sites]].sum(axis=1)

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df.index, y=df["total_scheduled"], name="Scheduled", line=dict(color="blue")))
    fig1.add_trace(go.Scatter(x=df.index, y=df["total_actual"], name="Actual", line=dict(color="red", dash="dot")))
    fig1.add_vline(x=now, line_width=2, line_dash="dash", line_color="grey")
    fig1.update_layout(height=400, xaxis_title="Time", yaxis_title="MW")
    st.plotly_chart(fig1, use_container_width=True)

    if show_alerts:
        alert_count = df["alerts"].sum()
        st.warning(f"⚠️ {alert_count} imbalance alerts above threshold in selected timeframe")

# --- Tab 2: Site-Level Flex & Imbalance ---
with tab2:
    st.subheader("Site-Level Imbalance and Flexibility")
    site = selected_sites[0]
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df.index, y=df[f"scheduled_{site}"], name="Scheduled", line=dict(color="blue")))
    fig2.add_trace(go.Scatter(x=df.index, y=df[f"actual_{site}"], name="Actual", line=dict(color="red", dash="dot")))
    fig2.add_trace(go.Bar(x=df.index, y=df[f"imbalance_{site}"], name="Imbalance", marker_color="orange", opacity=0.5))
    fig2.update_layout(height=400, xaxis_title="Time", yaxis_title="MW")
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("**Cumulative Balancing Activations**")
    col1, col2, col3 = st.columns(3)
    col1.metric("# Activations", int((df["balancing_activations"] > 0).sum()))
    col2.metric("Energy (MWh)", f"{df["balancing_activations"].sum():.1f}")
    col3.metric("Avg Price (€/MWh)", f"{df["imbalance_price"].mean():.0f}")

# --- Tab 3: Market & Schedule ---
with tab3:
    st.subheader("Market Schedule Upload")
    st.file_uploader("Upload Day-Ahead Schedule", type=["csv", "xlsx"], disabled=True)
    st.write("(Upload disabled in prototype)")

    fig3 = go.Figure()
    for site in selected_sites:
        fig3.add_trace(go.Scatter(x=df.index, y=df[f"scheduled_{site}"], name=f"Scheduled {site}"))
    fig3.update_layout(height=400, xaxis_title="Time", yaxis_title="MW")
    st.plotly_chart(fig3, use_container_width=True)

    st.download_button("Download Performance Data", data="", file_name="mock_performance.csv", disabled=True)
