
import streamlit as st
import zipfile
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import TextIOWrapper
import os

st.set_page_config(page_title="Shaker Dashboard - Smart Column Detection", layout="wide")

# === Sidebar Controls ===
st.sidebar.image("assets/Prodigy_IQ_logo.png", width=180)
st.sidebar.selectbox("Select Screen Mesh Type", ["API 100", "API 120", "API 140", "API 200"])
threshold = st.sidebar.slider("Utilization Threshold (%)", 50, 100, 80)
st.sidebar.image("assets/shaker_unit.png", caption="Hyperpool Shaker Unit", use_column_width=True)
selected_date = st.sidebar.date_input("Select Date to View Performance", value=datetime.today())

st.title("📈 Real-Time Shaker Dashboard (Smart Detection)")
uploaded_zip = st.file_uploader("Upload ZIP of shaker CSV files", type=['zip'])

def detect_column(cols, keywords):
    for col in cols:
        for keyword in keywords:
            if keyword.lower() in col.lower():
                return col
    return None

if uploaded_zip:
    try:
        with zipfile.ZipFile(uploaded_zip, 'r') as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                st.error("No CSV files found in ZIP.")
            else:
                all_dfs = []
                for file in csv_files:
                    with z.open(file) as f:
                        df = pd.read_csv(TextIOWrapper(f, encoding='utf-8', errors='ignore'), on_bad_lines='skip')
                        df.columns = df.columns.str.strip()
                        df['ShakerUnit'] = os.path.basename(file).split('.')[0]
                        all_dfs.append(df)

                df_all = pd.concat(all_dfs, ignore_index=True)

                # Detect time and load columns
                time_col = detect_column(df_all.columns, ['Timestamp', 'Time', 'Date', 'HH:MM:SS', 'YYYY/MM/DD'])
                load_col = detect_column(df_all.columns, ['Shaker', 'Load', 'RPM'])

                if time_col:
                    df_all[time_col] = pd.to_datetime(df_all[time_col], errors='coerce')
                else:
                    st.error("⚠️ Could not detect a valid timestamp column.")
                    st.stop()

                if not load_col:
                    st.error("⚠️ Could not detect a shaker load-related column.")
                    st.stop()

                # Compute metrics
                depth_col = detect_column(df_all.columns, ['Bit Depth', 'Hole Depth'])
                depth_drilled = int(df_all[depth_col].max()) if depth_col else 0
                shaker_load = round(df_all[load_col].mean(), 2)
                screen_life_hrs = round((200 - shaker_load) * 0.8, 1)
                screen_util_pct = round((shaker_load / 100) * threshold, 2)

                col1, col2, col3 = st.columns(3)
                col1.metric("📏 Depth Drilled (ft)", f"{depth_drilled:,}")
                col2.metric("📉 Shaker Load", f"{shaker_load:.1f}%", delta="-")
                col3.metric("🧪 Screen Utilization", f"{screen_util_pct:.1f}%", delta="-")

                st.warning("🔴 Auto anomaly flagging enabled based on shaker load changes.")

                tab1, tab2, tab3, tab4 = st.tabs(["Charts", "Drop Flags", "Efficiency", "Raw Data"])

                with tab1:
                    st.subheader("Shaker Output Over Time")
                    fig = px.line(df_all.tail(1000), x=time_col, y=load_col, color='ShakerUnit')
                    st.plotly_chart(fig, use_container_width=True)

                with tab2:
                    df_all['DropFlag'] = (df_all[load_col].diff().abs() > 5).astype(int)
                    st.subheader("Drop Detection")
                    fig = px.scatter(df_all, x=time_col, y=load_col, color=df_all['DropFlag'].map({0: "Normal", 1: "Drop"}))
                    st.plotly_chart(fig, use_container_width=True)

                with tab3:
                    st.subheader("Solids Removal Efficiency")
                    fig = px.pie(values=[screen_util_pct, 100 - screen_util_pct], names=['Utilized', 'Losses'])
                    st.plotly_chart(fig, use_container_width=True)

                with tab4:
                    st.subheader("Raw Merged Shaker Data")
                    st.dataframe(df_all.head(200))

    except Exception as e:
        st.error(f"❌ Error processing ZIP: {e}")
