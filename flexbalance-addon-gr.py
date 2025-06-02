import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ---------- SETTINGS ----------
np.random.seed(43)

now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

# Generate timestamps for last 8h and next 8h
ptu_range = pd.date_range(now - timedelta(hours=12), now  - timedelta(minutes=15), freq="15min")

# ---------- MOCK DATA ----------
def generate_mock_data():
    df = pd.DataFrame(index=ptu_range)
    df.index.name = "timestamp"

    # mFRR prices (positive normal dist, capped)
    prices = np.abs(np.random.normal(loc=200, scale=500, size=len(df)))
    prices = np.clip(prices, 0, 1050)
    df["mFRR_price"] = prices

    # Asset A (mFRR active) base pattern: 10 MW with no flex, then 80 MW with flex to 10 MW
    df["scheduled_A"] = [10 if (i // 4) % 2 == 0 else 80 for i in range(len(df))]
    df["min_flex_A"] = [scheduled if scheduled == 10 else 10 for scheduled in df["scheduled_A"]]
    df["actual_A"] = df["scheduled_A"]

    # mFRR activations only when price > 600, in 50% of those cases
    high_price_mask = (df.index < now) & (df["mFRR_price"] > 500)
    activation_mask = high_price_mask & (np.random.rand(len(df)) < 0.5) & (df["scheduled_A"] == 80)
    df.loc[activation_mask, "actual_A"] = 40  # Activated (half load)

    # Add further curtailments due to internal optimization
    extra_curtail = (np.random.rand(len(df)) < 0.05) & (df.index < now)
    df.loc[extra_curtail, "actual_A"] = 30

    # Asset B (not mFRR active)
    df["scheduled_B"] = 20  # Full load constant
    df["actual_B"] = df["scheduled_B"]

    # Apply curtailment only when mFRR price > 600
    curtail_mask_B = (df.index < now) & (df["mFRR_price"] > 600) & (np.random.rand(len(df)) < 0.1)
    df.loc[curtail_mask_B, "actual_B"] -= 10

    df["min_flex_B"] = 10

    return df

df = generate_mock_data()

# ---------- STREAMLIT UI ----------
st.set_page_config(layout="wide")

st.sidebar.header("Over-activating mFRR assets")
overactivate_price = st.sidebar.slider("Min mFRR Price to Over-activate (€/MWh)", 0, 1000, 600, 50)

st.sidebar.header("Activating mFRR assets for other PTUs")
other_ptu_price = st.sidebar.slider("Min mFRR Price to Activate Other PTUs (€/MWh)", 0, 1000, 500, 50)
other_ptu_max_activations = st.sidebar.number_input("Max Activations on Other PTUs", min_value=0, max_value=1000, value=10, step=1)

st.sidebar.header("Activating Additional Flex (non-mFRR assets)")
additional_flex_price = st.sidebar.slider("Min mFRR Price to Activate Additional Flex (€/MWh)", 0, 1000, 400, 50)
additional_flex_max_activations = st.sidebar.number_input("Max Additional Flex Activations", min_value=0, max_value=1000, value=5, step=1)


st.title("Energy Asset Flexibility Monitor")



st.subheader("Key Metrics")
col1, col2, col3 = st.columns(3)
activations = (df["actual_A"] < df["scheduled_A"]).sum()
earnings = activations * df["mFRR_price"].mean() / 4  # simple estimate
earnings_additional_flex = (df["actual_B"] < df["scheduled_B"]).sum() * df["mFRR_price"].mean() / 4
earnings_mfrr_overactivate = (df["actual_A"] < df["scheduled_A"]).sum() * overactivate_price / 4
earnings_mfrr_other_ptu = (df["actual_A"] < df["scheduled_A"]).sum() * other_ptu_price / 4
col1.metric("mFRR Earnings (est.)", f"€{earnings:,.0f}")
col2.metric("mFRR Overactivation earnings (other PTU)", f"€{earnings_mfrr_other_ptu:,.0f} ")
col1.metric("mFRR Overactivation earnings", f"€{earnings_mfrr_overactivate:,.0f} ")
col2.metric("additional flex earnings", f"€{earnings_additional_flex:,.0f}")
col1.metric("mFRR Activations", f"{activations}")
other_flex_activations = 3
col2.metric("Additional Flex Activations", f"{other_flex_activations}")

st.subheader("Consumption & Flexibility (Last 12h)")
fig = go.Figure()

# Asset A (Blue)
fig.add_trace(go.Scatter(x=df.index, y=df["scheduled_A"], name="Asset A – Scheduled", line=dict(color="royalblue")))

fig.add_trace(go.Scatter(x=df.index, y=df["actual_A"], name="Asset A – Actual", line=dict(color="royalblue", dash="dot")))

fig.add_trace(go.Scatter(x=df.index, y=df["min_flex_A"], name="Asset A – Flex Limit", line=dict(color="royalblue", dash="dash")))

# Asset B (Green)
fig.add_trace(go.Scatter(x=df.index, y=df["scheduled_B"], name="Asset B – Scheduled", line=dict(color="forestgreen")))

fig.add_trace(go.Scatter(x=df.index, y=df["actual_B"], name="Asset B – Actual", line=dict(color="forestgreen", dash="dot")))

fig.add_trace(go.Scatter(x=df.index, y=df["min_flex_B"], name="Asset B – Flex Limit", line=dict(color="forestgreen", dash="dash")))

fig.update_layout(height=450, xaxis_title="Time", yaxis_title="MW")
st.plotly_chart(fig, use_container_width=True)

st.subheader("mFRR Price (€/MWh)")
fig2 = go.Figure()
for i in range(0, len(df), 4):
    ptus = df.index[i:i+4]
    if len(ptus) == 4:
        fig2.add_trace(go.Scatter(x=[ptus[0], ptus[-1]], y=[df.iloc[i]["mFRR_price"]]*2,
                                    mode="lines", line=dict(color="orange"), showlegend=False))
fig2.update_layout(height=300, xaxis_title="Time", yaxis_title="€/MWh")
st.plotly_chart(fig2, use_container_width=True)

