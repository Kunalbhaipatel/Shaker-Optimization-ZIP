
import streamlit as st
import zipfile
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import TextIOWrapper
import os

st.set_page_config(page_title="Shaker Dashboard - Vertical + Summary", layout="wide")

# === Sidebar ===
st.sidebar.image("assets/Prodigy_IQ_logo.png", width=180)
threshold = st.sidebar.slider("Utilization Threshold (%)", 50, 100, 80)
st.sidebar.image("assets/shaker_unit.png", caption="Hyperpool Shaker Unit", use_column_width=True)

# === Upload ===
st.title("📊 Shaker Dashboard: Vertical View + Daily Summary + Export")
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
                st.stop()

            all_dfs = []
            for file in csv_files:
                with z.open(file) as f:
                    df = pd.read_csv(TextIOWrapper(f, encoding='utf-8', errors='ignore'), on_bad_lines='skip')
                    df.columns = df.columns.str.strip()
                    df['ShakerUnit'] = os.path.basename(file).split('.')[0]
                    all_dfs.append(df)

            df_all = pd.concat(all_dfs, ignore_index=True)

            time_col = detect_column(df_all.columns, ['Timestamp', 'Time', 'Date', 'HH:MM:SS', 'YYYY/MM/DD'])
            load_col = detect_column(df_all.columns, ['Shaker', 'Load', 'RPM'])
            depth_col = detect_column(df_all.columns, ['Bit Depth', 'Hole Depth'])

            if not time_col or not load_col:
                st.error("Missing time/load column.")
                st.stop()

            df_all[time_col] = pd.to_datetime(df_all[time_col], errors='coerce')
            df_all[load_col] = pd.to_numeric(df_all[load_col], errors='coerce')
            df_all = df_all.dropna(subset=[time_col, load_col])
            df_all['Date'] = df_all[time_col].dt.date

            # === Summary Table ===
            daily_summary = df_all.groupby('Date').agg({
                load_col: 'mean',
                depth_col: 'max' if depth_col else 'count'
            }).rename(columns={
                load_col: 'Avg_Shaker_Load',
                depth_col: 'Depth_Drilled' if depth_col else 'Sample_Count'
            }).reset_index()
            daily_summary['Screen_Utilization'] = (daily_summary['Avg_Shaker_Load'] / 100 * threshold).round(2)

            st.subheader("📅 Daily Summary Table")
            st.dataframe(daily_summary)

            csv_data = daily_summary.to_csv(index=False).encode('utf-8')
            st.download_button("📤 Export Summary to CSV", csv_data, "daily_shaker_summary.csv", "text/csv")

            # === Date Filter + Per-Day Detail ===
            selected_date = st.sidebar.selectbox("Select Date to View Vertically", sorted(df_all['Date'].dropna().unique())[::-1])
            df_day = df_all[df_all['Date'] == selected_date]

            if df_day.empty:
                st.warning("No data for selected date.")
                st.stop()

            shaker_load = round(df_day[load_col].mean(), 2)
            screen_util_pct = round((shaker_load / 100) * threshold, 2)
            depth_drilled = int(df_day[depth_col].max()) if depth_col else 0

            col1, col2, col3 = st.columns(3)
            col1.metric("📏 Depth Drilled (ft)", f"{depth_drilled:,}")
            col2.metric("📉 Shaker Load", f"{shaker_load:.1f}%", delta="-")
            col3.metric("🧪 Screen Utilization", f"{screen_util_pct:.1f}%", delta="-")

            # === Vertical + Summary Tabs ===
            tab1, tab2, tab3, tab4 = st.tabs(["Vertical View", "Drop Flags", "Efficiency", "Raw Data"])

            with tab1:
                df_day['Depth_Index'] = range(len(df_day))
                fig = px.line(df_day.tail(1000), y='Depth_Index', x=load_col, color='ShakerUnit',
                              orientation='h', title="Shaker Load vs Simulated Depth")
                fig.update_yaxes(title="Simulated Depth Index")
                fig.update_xaxes(title="Shaker Load (%)")
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                df_day['DropFlag'] = (df_day[load_col].diff().abs() > 5).astype(int)
                fig = px.scatter(df_day, y='Depth_Index', x=load_col, color=df_day['DropFlag'].map({0: "Normal", 1: "Drop"}))
                fig.update_yaxes(title="Depth Index")
                fig.update_xaxes(title="Shaker Load (%)")
                st.plotly_chart(fig, use_container_width=True)

            with tab3:
                fig = px.pie(values=[screen_util_pct, 100 - screen_util_pct], names=['Utilized', 'Losses'])
                st.plotly_chart(fig, use_container_width=True)

            with tab4:
                st.dataframe(df_day.head(200))

            st.markdown("""
### ℹ️ Recommendations
- 🟢 Screen utilization < 50%: optimal
- 🟡 50-80%: monitor closely
- 🔴 > 80%: inspect screen and consider change
Avoid high continuous load to extend screen life and improve solids removal.
            """)

    except Exception as e:
        st.error(f"Unexpected error: {e}")
