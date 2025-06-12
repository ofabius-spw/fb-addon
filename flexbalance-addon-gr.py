import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

np.random.seed(41)  # For reproducibility
# --- Settings ---
st.set_page_config(layout="wide")
st.title("Imbalance Monitoring Dashboard")
# st.image(, caption="Optional caption", use_column_width=True)
st.sidebar.image("https://142257164.fs1.hubspotusercontent-eu1.net/hubfs/142257164/Sympower-Logo-01-2.png")
# --- Sidebar Global Controls ---
st.sidebar.header("Global Controls")
# selected_date = st.sidebar.date_input("Select Date", datetime.utcnow().date())
selected_date = datetime.utcnow().date()
# selected_time = st.sidebar.time_input("Select Time", datetime.utcnow().time())
selected_time = datetime.utcnow().time()  # Default to current Greek time 
site_options = ["All Sites", "Site A", "Site B", "Site C"]
selected_sites = st.sidebar.multiselect("Select Site(s)", site_options, default=["All Sites"])
(volume_threshold_low, volume_threshold_high) = st.sidebar.slider("Imbalance Volume Threshold (MW)", -25, 25, (-10, 10))
(price_threshold_low, price_threshold_high) = st.sidebar.slider("Estimated Price Alert Threshold (€/MWh)", -400, 1500, (0, 500))
(cost_threshold_low, cost_threshold_high) = st.sidebar.slider("Imbalance Cost Alert Threshold (€)", -10000, 10000, (-2000, 2000))

# Combine into a full datetime
selected_datetime = datetime.combine(selected_date, selected_time)+timedelta(hours=3)   # Convert to Greek time (UTC+3, summer) 

# Round down to the nearest hour or 15-min PTU if needed
now = selected_datetime.replace(minute=0, second=0, microsecond=0)

if "All Sites" in selected_sites:
    selected_sites = ["Site A", "Site B", "Site C"]

# resource_filter = st.sidebar.selectbox("Resource Type", ["All", "Type A", "Type B", "Type C"])
# show_alerts = st.sidebar.checkbox("Show Alerts", value=True)

# if st.sidebar.button("Refresh Data"):
#     st.experimental_rerun()

st.sidebar.download_button("Download Data", data="", file_name="mock_data.csv", disabled=True)

# --- Generate Synthetic Data ---
def generate_data(now, selected_sites):
    index = pd.date_range(now - timedelta(hours=16), now, freq="15min")
    df = pd.DataFrame(index=index)
    df.index.name = "timestamp"

    for site in selected_sites:
        df[f"scheduled_{site}"] = np.random.normal(25, 10, len(df))
        df[f"actual_{site}"] = df[f"scheduled_{site}"] + np.random.normal(0, 5, len(df))
        df[f"imbalance_{site}"] = df[f"actual_{site}"] - df[f"scheduled_{site}"]
    df["imbalance_price"] = np.random.normal(200, 200, len(df))
    df["balancing_activations"] = np.random.binomial(1, 0.2, len(df)) * np.random.uniform(5, 15, len(df))
    df["scheduled_total"] = df[[f"scheduled_{s}" for s in selected_sites]].sum(axis=1)

    df["actual_total"] = df[[f"actual_{s}" for s in selected_sites]].sum(axis=1)
    df["imbalance_total"] = df[[f"imbalance_{s}" for s in selected_sites]].sum(axis=1)
    df["imbalance_cost"] = df["imbalance_total"] * df["imbalance_price"]  # Convert to k€
    df["alerts_volume"] = df[f"imbalance_total"] > volume_threshold_high
    df["alerts_volume"] += df[f"imbalance_total"] < volume_threshold_low
    df["alerts_cost"] = df["imbalance_cost"] > cost_threshold_high
    df["alerts_cost"] += df["imbalance_cost"] < cost_threshold_low
    df["alerts_price"] = df["imbalance_price"] > price_threshold_high
    df["alerts_price"] += df["imbalance_price"] < price_threshold_low
    return df

now = selected_datetime.replace(minute=0, second=0, microsecond=0)
df = generate_data(now, selected_sites)

# --- Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Schedule", "Consumption", "Imbalance position", "Price estimate", "Imbalance costs" ])


# --- Tab 1: Schedule ---
with tab1:
    st.subheader("Scheduled Consumption")
    st.file_uploader("Upload Day-Ahead Schedule", type=["csv", "xlsx"], disabled=True)
    st.write("(Upload disabled in prototype)")

    c1, c2, c3 = st.columns(3)
    c3.metric("Total scheduled for selected period", f"{df['scheduled_total'].sum()/4:.1f} MWh")
    
    fig3 = go.Figure()
    for site in selected_sites:
        fig3.add_trace(go.Scatter(x=df.index, y=df[f"scheduled_{site}"], name=f"Scheduled {site}"))
    fig3.add_trace(go.Scatter(x=df.index, y=df["scheduled_total"], name="Total Scheduled", line=dict(color="blue", width=2)))
    fig3.update_layout(height=400, xaxis_title="Time", yaxis_title="MW", 
                      title="Scheduled Consumption per PTU")
    st.plotly_chart(fig3, use_container_width=True)

    # st.download_button("Download Performance Data", data="", file_name="mock_performance.csv", disabled=True)
    # st.write("(Download disabled in prototype)")

# --- Tab 2: Portfolio Overview ---
with tab2:
    st.subheader("Consumption monitoring")
        # check if png image is in current folder
    try:
        st.image("Debrief_view_grafana_confidential.png")
    except:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df.index, y=df["scheduled_total"], name="Scheduled", line=dict(color="blue")))
        fig1.add_trace(go.Scatter(x=df.index, y=df["actual_total"], name="Actual", line=dict(color="red", dash="dot")))
        fig1.add_vline(x=now, line_width=2, line_dash="dash", line_color="grey")
        fig1.update_layout(height=400, xaxis_title="Time", yaxis_title="MW")
        st.plotly_chart(fig1, use_container_width=True)


# --- Tab 3: Site-Level Flex & Imbalance ---
with tab3:
    st.subheader("Imbalance of portfolio")
    # st.metric(, ")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total imbalance for selected period", f"{df['imbalance_total'].sum()/4:.1f} MWh")
    col2.metric("Positive imbalance PTUs", f"{sum(df['imbalance_total']>0)/len(df)*100:.1f}%" )
    col3.metric("Negative imbalance PTUs", f"{sum(df['imbalance_total']<0)/len(df)*100:.1f}%")
    
    st.write("Change the imbalance volume thresholds in the sidebar to see how the alerts change.")
    site = selected_sites[0]
    fig2 = go.Figure()
    x = df.index
    fig2.add_trace(go.Scatter(x=x, y=df[f"scheduled_total"], name="Scheduled Consumption", line=dict(color="blue")))
    fig2.add_trace(go.Scatter(x=x, y=df[f"actual_total"], name="Consumption", line=dict(color="red", dash="dot")))

    y_upper = [volume_threshold_high]*len(df)
    y_lower = [volume_threshold_low]*len(df)
    
    fig2.add_hline(y=volume_threshold_low, line_width=2, line_dash="dash", line_color="red", annotation_text="Alert Threshold (low)", annotation_position="top left")
    fig2.add_hline(y=volume_threshold_high, line_width=2, line_dash="dash", line_color="blue", annotation_text="Alert Threshold (high)", annotation_position="top left") 

    alert_volume_count = df["alerts_volume"].sum()
    st.warning(f"⚠️ {alert_volume_count} imbalance alerts outside volume thresholds in selected timeframe")

    # fig2.add_trace(go.Scatter(
    #     name='Upper Bound',
    #     x=x,
    #     y=y_upper,
    #     mode='lines',
    #     marker=dict(color="#444"),
    #     line=dict(width=0),
    #     showlegend=False
    # ))
    # fig2.add_trace(
    # go.Scatter(
    #     name='Lower Bound',
    #     x=x,
    #     y=y_lower,
    #     marker=dict(color="#444"),
    #     line=dict(width=0),
    #     mode='lines',
    #     fillcolor='rgba(225, 100, 106, 0.2)',
    #     fill='tonexty',
    #     showlegend=False
    # ))

    fig2.add_trace(go.Bar(x=df.index, y=df["imbalance_total"], name="Imbalance per PTU", marker_color="orange", opacity=0.5))
    fig2.update_layout(height=400, xaxis_title="Time", yaxis_title="MW")
    st.plotly_chart(fig2, use_container_width=True)

    # st.markdown("**Cumulative Balancing Activations**")
    # col1, col2, col3 = st.columns(3)
    # col1.metric("# Activations", int((df["balancing_activations"] > 0).sum()))
    # col2.metric("Energy (MWh)", f"{df["balancing_activations"].sum():.1f}")
    # col3.metric("Avg Price (€/MWh)", f"{df["imbalance_price"].mean():.0f}")

with tab4:
    st.subheader("Imbalance price estimate")
    try:
        st.image("imbalance_price_estimate_confidential.png")
    except:
        col1, col2, col3 = st.columns(3)
        col1.metric("Highest price", f"{max(df['imbalance_price']):.0f} €/MWh")
        col2.metric("Lowest price", f"{min(df['imbalance_price']):.0f} €/MWh" )
        col3.metric("PTUs with negative prices", f"{sum(df['imbalance_price']<0):.1f}")
        alert_price_count = df["alerts_price"].sum()
        st.warning(f"⚠️ {alert_price_count} imbalance price alerts outside thresholds in selected timeframe")

        fig4 = go.Figure()
        fig4.add_trace(go.Bar(x=df.index, y=df["imbalance_price"], name="Estimated Imbalance Price", marker_color="orange", opacity=0.5))
        fig4.add_vline(x=now, line_width=2, line_dash="dash", line_color="grey")
        fig4.add_hline(y=price_threshold_low, line_width=2, line_dash="dash", line_color="red", annotation_text="Alert Threshold (high)", annotation_position="top left")
        fig4.add_hline(y=price_threshold_high, line_width=2, line_dash="dash", line_color="blue", annotation_text="Alert Threshold (low)", annotation_position="top left")
        st.plotly_chart(fig4, use_container_width=True)

with tab5:

    col1, col2, col3 = st.columns(3)
    col1.metric("Total imbalance costs for selected period", f"€{df['imbalance_cost'].sum():.0f}", 11350, delta_color='inverse')
    col2.metric("Most expensive PTU", f"€{df['imbalance_cost'].max():.0f}")
    col3.metric("Most beneficial PTU", f"€{df['imbalance_cost'].min():.0f}")

    alert_cost_count = df["alerts_cost"].sum()
    st.warning(f"⚠️ {alert_cost_count} imbalance cost alerts outside volume thresholds in selected timeframe")

    st.subheader("Imbalance Costs Per PTU")
    fig5 = go.Figure()

    fig5.add_trace(go.Bar(x=df.index, y=df["imbalance_cost"], name="Imbalance Cost", marker_color="orange", opacity=0.5))
    fig5.add_vline(x=now, line_width=2, line_dash="dash", line_color="grey")
    fig5.add_hline(y=cost_threshold_low, line_width=2, line_dash="dash", line_color="red", annotation_text="Alert Threshold (high)", annotation_position="top left")
    fig5.add_hline(y=cost_threshold_high, line_width=2, line_dash="dash", line_color="blue", annotation_text="Alert Threshold (low)", annotation_position="top left")
    fig5.update_layout(height=400, xaxis_title="Time", yaxis_title="€")
    st.plotly_chart(fig5, use_container_width=True)