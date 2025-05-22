
import streamlit as st
import zipfile
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import TextIOWrapper
import os

st.set_page_config(page_title="Shaker Dashboard - Summary Export", layout="wide")

# Sidebar Setup
st.sidebar.image("assets/Prodigy_IQ_logo.png", width=180)
threshold = st.sidebar.slider("Utilization Threshold (%)", 50, 100, 80)
st.sidebar.image("assets/shaker_unit.png", caption="Hyperpool Shaker Unit", use_column_width=True)

# File Upload
st.title("📊 Shaker Dashboard with Summary Export and Recommendations")
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

            if time_col:
                df_all[time_col] = pd.to_datetime(df_all[time_col], errors='coerce')
            else:
                st.error("No timestamp column detected.")
                st.stop()

            df_all[load_col] = pd.to_numeric(df_all[load_col], errors='coerce')
            df_all = df_all.dropna(subset=[time_col, load_col])
            df_all['Date'] = df_all[time_col].dt.date

            # Daily Summary Table
            daily_summary = df_all.groupby('Date').agg({
                load_col: 'mean',
                depth_col: 'max' if depth_col else 'count'
            }).rename(columns={
                load_col: 'Avg_Shaker_Load',
                depth_col: 'Depth_Drilled' if depth_col else 'Sample_Count'
            }).reset_index()

            daily_summary['Screen_Utilization'] = (daily_summary['Avg_Shaker_Load'] / 100 * threshold).round(2)
            st.subheader("📅 Daily Summary")
            st.dataframe(daily_summary)

            # CSV Export
            csv_data = daily_summary.to_csv(index=False).encode('utf-8')
            st.download_button("📤 Export Summary to CSV", csv_data, "daily_shaker_summary.csv", "text/csv")

            # Charts
            st.subheader("📈 Daily Trend Overview")
            fig1 = px.line(daily_summary, x='Date', y='Avg_Shaker_Load', title='Average Shaker Load Over Time')
            fig2 = px.line(daily_summary, x='Date', y='Screen_Utilization', title='Screen Utilization % Over Time')
            fig3 = px.line(daily_summary, x='Date', y='Depth_Drilled', title='Depth Drilled Over Time')

            st.plotly_chart(fig1, use_container_width=True)
            st.plotly_chart(fig2, use_container_width=True)
            st.plotly_chart(fig3, use_container_width=True)

            # Descriptive Insights
            st.markdown("""
### ℹ️ Screen Life & Replacement Guidance
- 🟢 **Utilization below 50%**: screen condition is likely good.
- 🟡 **Between 50–80%**: monitor wear and check for vibration consistency.
- 🔴 **Above 80%**: recommend physical inspection, consider screen replacement.
- 📌 Regular high shaker loads reduce screen lifespan — aim to optimize feed rate.

These insights help predict screen wear and reduce non-productive time (NPT).
            """)

    except Exception as e:
        st.error(f"Error during processing: {e}")
