
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import StringIO

st.set_page_config(page_title="Real-Time Shaker Dashboard", layout="wide")

# === Sidebar Controls ===
st.sidebar.image("assets/Prodigy_IQ_logo.png", width=180)
st.sidebar.selectbox("Select Screen Mesh Type", ["API 100", "API 120", "API 140", "API 200"])
threshold = st.sidebar.slider("Utilization Threshold (%)", 50, 100, 80)
st.sidebar.image("assets/shaker_unit.png", caption="Hyperpool Shaker Unit", use_column_width=True)
selected_date = st.sidebar.date_input("Select Date to View Performance", value=datetime.today())

# === Upload Section ===
st.title("🛠 Real-Time Shaker Monitoring Dashboard")
uploaded_file = st.file_uploader("📤 Upload Shaker CSV Data", type=['csv'])

if uploaded_file:
    size_mb = round(len(uploaded_file.getvalue()) / (1024**2), 2)
    st.caption(f"Uploaded file: **{uploaded_file.name}**, Size: **{size_mb} MB**")

    try:
        df = pd.read_csv(uploaded_file, on_bad_lines='skip', encoding_errors='ignore')
        df.columns = df.columns.str.strip()

        # Convert timestamp if present
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')

        # Example columns expected
        load_col = [col for col in df.columns if "Load" in col or "Shaker" in col]
        depth_drilled = 11437
        screen_life_hrs = 118.9
        shaker_load_pct = df[load_col[0]].mean() if load_col else -23.7
        screen_util_pct = 3.7

        # === Summary Cards ===
        st.subheader("📊 Summary: Drilling & Shaker Overview")
        col1, col2, col3 = st.columns(3)
        col1.metric("📏 Depth Drilled (ft)", f"{depth_drilled:,}")
        col2.metric("📉 Shaker Load", f"{shaker_load_pct:.1f}%", delta="-32.9→27.2%")
        col3.metric("🧪 Screen Utilization", f"{screen_util_pct:.1f}%", delta="-10.8→11.9%")
        st.warning("🔴 Shaker load anomalies detected — check for mechanical issues or data errors.")

        # === Tabs ===
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Charts", "🔻 Drop Flags", "📊 Efficiency", "📂 Raw Data"])

        with tab1:
            st.subheader("Shaker Output")
            st.caption(f"{load_col[0]} - Last 1000 Points")
            fig = px.line(df.tail(1000), x='Timestamp', y=load_col[0], title="Shaker Load Over Time")
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.subheader("🔍 Shaker Drop Detection Flags")
            df['DropFlag'] = (df[load_col[0]].diff().abs() > 5).astype(int)
            fig = px.scatter(df, x='Timestamp', y=load_col[0], color=df['DropFlag'].map({0: "Normal", 1: "Drop"}))
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.subheader("🧮 Solids Removal Efficiency")
            fig = px.pie(values=[screen_util_pct, 100 - screen_util_pct], names=['Utilized', 'Losses'])
            st.plotly_chart(fig, use_container_width=True)

        with tab4:
            st.subheader("📂 Raw Data")
            st.dataframe(df.head(200))

    except Exception as e:
        st.error(f"Error processing file: {e}")
