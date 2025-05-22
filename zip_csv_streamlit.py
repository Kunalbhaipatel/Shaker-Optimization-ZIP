
import streamlit as st
import zipfile
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import TextIOWrapper
import os

st.set_page_config(page_title="Shaker Dashboard - Auto Merge + Sensors", layout="wide")

# === Sidebar Controls ===
st.sidebar.image("assets/Prodigy_IQ_logo.png", width=180)
st.sidebar.selectbox("Select Screen Mesh Type", ["API 100", "API 120", "API 140", "API 200"])
threshold = st.sidebar.slider("Utilization Threshold (%)", 50, 100, 80)
st.sidebar.image("assets/shaker_unit.png", caption="Hyperpool Shaker Unit", use_column_width=True)
selected_date = st.sidebar.date_input("Select Date to View Performance", value=datetime.today())

# === Upload Section ===
st.title("🔄 Auto-Merged Real-Time Shaker Dashboard")
uploaded_zip = st.file_uploader("📤 Upload ZIP of Shaker CSVs", type=['zip'])

if uploaded_zip:
    size_mb = round(len(uploaded_zip.getvalue()) / (1024**2), 2)
    st.caption(f"Uploaded: **{uploaded_zip.name}**, Size: **{size_mb} MB**")

    try:
        with zipfile.ZipFile(uploaded_zip, 'r') as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                st.error("No CSV files found in ZIP.")
            else:
                all_dfs = []
                for file_name in csv_files:
                    with z.open(file_name) as f:
                        df = pd.read_csv(TextIOWrapper(f, encoding='utf-8', errors='ignore'), on_bad_lines='skip')
                        df.columns = df.columns.str.strip()
                        df['ShakerUnit'] = os.path.basename(file_name).split('.')[0]
                        all_dfs.append(df)

                df_all = pd.concat(all_dfs, ignore_index=True)

                # Timestamp conversion
                if 'Timestamp' in df_all.columns:
                    df_all['Timestamp'] = pd.to_datetime(df_all['Timestamp'], errors='coerce')

                # Custom metric extraction
                depth_col = next((c for c in df_all.columns if 'Depth' in c and 'Bit' in c), None)
                load_col = next((c for c in df_all.columns if 'Load' in c or 'Shaker' in c), None)

                depth_drilled = int(df_all[depth_col].max()) if depth_col else 0
                shaker_load = round(df_all[load_col].mean(), 2) if load_col else -999
                screen_life_hrs = round((200 - shaker_load) * 0.8, 1) if shaker_load != -999 else 0
                screen_util_pct = round((shaker_load / 100) * threshold, 2) if shaker_load != -999 else 0

                st.subheader("📊 Aggregated Metrics from Sensors")
                col1, col2, col3 = st.columns(3)
                col1.metric("📏 Depth Drilled (ft)", f"{depth_drilled:,}")
                col2.metric("📉 Shaker Load", f"{shaker_load:.1f}%", delta="-")
                col3.metric("🧪 Screen Utilization", f"{screen_util_pct:.1f}%", delta="-")

                st.warning("🔴 System-wide anomaly detection activated — auto-flagging enabled.")

                tab1, tab2, tab3, tab4 = st.tabs(["📈 Charts", "🔻 Drop Flags", "📊 Efficiency", "📂 Raw Data"])

                with tab1:
                    st.subheader("Shaker Load Over Time")
                    fig = px.line(df_all.tail(1000), x='Timestamp', y=load_col, color='ShakerUnit')
                    st.plotly_chart(fig, use_container_width=True)

                with tab2:
                    st.subheader("Anomaly Drop Detection")
                    df_all['DropFlag'] = (df_all[load_col].diff().abs() > 5).astype(int)
                    fig = px.scatter(df_all, x='Timestamp', y=load_col, color='DropFlag', symbol='ShakerUnit')
                    st.plotly_chart(fig, use_container_width=True)

                with tab3:
                    st.subheader("Screen Utilization Efficiency")
                    fig = px.pie(values=[screen_util_pct, 100 - screen_util_pct],
                                 names=['Utilized', 'Losses'],
                                 title="Solids Removal Efficiency")
                    st.plotly_chart(fig, use_container_width=True)

                with tab4:
                    st.subheader("Raw Merged Data Sample")
                    st.dataframe(df_all.head(200))
    except Exception as e:
        st.error(f"Error processing ZIP: {e}")
