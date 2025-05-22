
import streamlit as st
import zipfile
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import TextIOWrapper
import os

st.set_page_config(page_title="Safe Shaker Dashboard", layout="wide")
st.sidebar.image("assets/Prodigy_IQ_logo.png", width=180)
threshold = st.sidebar.slider("Utilization Threshold (%)", 50, 100, 80)
st.sidebar.image("assets/shaker_unit.png", caption="Hyperpool Shaker Unit", use_column_width=True)

st.title("🛡 Safe Shaker Dashboard with Summary, Export, and Vertical Charts")
uploaded_zip = st.file_uploader("Upload ZIP with Shaker CSVs", type=["zip"])

def detect_column(columns, keywords):
    for col in columns:
        for key in keywords:
            if key.lower() in col.lower():
                return col
    return None

if uploaded_zip:
    try:
        with zipfile.ZipFile(uploaded_zip, 'r') as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                st.error("❌ No CSV files found in ZIP.")
                st.stop()

            all_dfs = []
            for file in csv_files:
                with z.open(file) as f:
                    df = pd.read_csv(TextIOWrapper(f, encoding="utf-8", errors="ignore"), on_bad_lines='skip')
                    df.columns = df.columns.str.strip()
                    df['ShakerUnit'] = os.path.basename(file).split('.')[0]
                    all_dfs.append(df)

            df_all = pd.concat(all_dfs, ignore_index=True)
            time_col = detect_column(df_all.columns, ["timestamp", "time", "date"])
            load_col = detect_column(df_all.columns, ["load", "shaker", "rpm"])
            depth_col = detect_column(df_all.columns, ["bit depth", "hole depth"])

            if not time_col or not load_col:
                st.error("❌ Required columns (timestamp/load) not found.")
                st.dataframe(df_all.head(10))
                st.stop()

            df_all[time_col] = pd.to_datetime(df_all[time_col], errors='coerce')
            df_all[load_col] = pd.to_numeric(df_all[load_col], errors='coerce')
            df_all = df_all.dropna(subset=[time_col, load_col])
            if df_all.empty:
                st.error("❌ All data rows are invalid or empty after cleaning.")
                st.stop()

            df_all['Date'] = df_all[time_col].dt.date
            summary_col = depth_col if depth_col else load_col
            summary_name = "Depth_Drilled" if depth_col else "Sample_Count"

            daily_summary = df_all.groupby('Date').agg({
                load_col: 'mean',
                summary_col: 'max' if depth_col else 'count'
            }).rename(columns={
                load_col: 'Avg_Shaker_Load',
                summary_col: summary_name
            }).reset_index()

            daily_summary['Screen_Utilization'] = (daily_summary['Avg_Shaker_Load'] / 100 * threshold).round(2)

            st.subheader("📅 Daily Summary Table")
            st.dataframe(daily_summary)

            csv_data = daily_summary.to_csv(index=False).encode('utf-8')
            st.download_button("📤 Export Summary to CSV", csv_data, "daily_shaker_summary.csv", "text/csv")

            # Date filter + vertical chart
            selected_date = st.sidebar.selectbox("Select Date for Detail View", sorted(df_all['Date'].unique())[::-1])
            df_day = df_all[df_all['Date'] == selected_date]

            if df_day.empty:
                st.warning("⚠️ No data for selected date.")
                st.stop()

            shaker_load = round(df_day[load_col].mean(), 2)
            screen_util_pct = round((shaker_load / 100) * threshold, 2)
            depth_value = int(df_day[depth_col].max()) if depth_col else len(df_day)

            col1, col2, col3 = st.columns(3)
            col1.metric("📏 Depth Drilled", f"{depth_value}")
            col2.metric("📉 Avg Shaker Load", f"{shaker_load:.1f}%")
            col3.metric("🧪 Screen Utilization", f"{screen_util_pct:.1f}%")

            tab1, tab2, tab3, tab4 = st.tabs(["Vertical View", "Drop Flags", "Efficiency", "Raw Data"])

            with tab1:
                df_day['Depth_Index'] = range(len(df_day))
                fig = px.line(df_day.tail(1000), y='Depth_Index', x=load_col, color='ShakerUnit',
                              orientation='h', title="Shaker Load vs Simulated Depth")
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                df_day['DropFlag'] = (df_day[load_col].diff().abs() > 5).astype(int)
                fig = px.scatter(df_day, y='Depth_Index', x=load_col,
                                 color=df_day['DropFlag'].map({0: "Normal", 1: "Drop"}))
                st.plotly_chart(fig, use_container_width=True)

            with tab3:
                fig = px.pie(values=[screen_util_pct, 100 - screen_util_pct], names=['Utilized', 'Losses'])
                st.plotly_chart(fig, use_container_width=True)

            with tab4:
                st.dataframe(df_day.head(200))

            st.markdown("""
### 🧠 Screen Management Tips
- <50% Utilization: Screen in good condition.
- 50–80%: Monitor for signs of wear.
- >80%: Check screen, likely needs replacement.
- 🔁 High load shortens screen life. Adjust feed rate to optimize.
            """)

    except Exception as e:
        st.error(f"🔥 Unhandled Error: {e}")
