
import streamlit as st
import zipfile
import pandas as pd
import plotly.express as px
from io import TextIOWrapper
import numpy as np
import os

st.set_page_config(page_title="📈 Shaker Dashboard Pro", layout="wide")
st.markdown("<h1 style='text-align: center;'>🛠️ Prodigy Shaker Performance Dashboard</h1>", unsafe_allow_html=True)

st.sidebar.image("assets/Prodigy_IQ_logo.png", width=180)
threshold = st.sidebar.slider("🎯 Utilization Threshold (%)", 50, 100, 80)
st.sidebar.image("assets/shaker_unit.png", caption="Hyperpool Shaker Unit", use_column_width=True)

uploaded_zip = st.file_uploader("📤 Upload a ZIP file containing shaker CSVs", type=["zip"])

def detect_column(columns, keywords):
    for col in columns:
        for key in keywords:
            if key.lower() in col.lower():
                return col
    return None

def try_parse_formats(series, formats):
    for fmt in formats:
        try:
            parsed = pd.to_datetime(series, format=fmt, errors='raise')
            return parsed, fmt
        except:
            continue
    return None, None

def color_load(val):
    if val > 80:
        return "background-color: #ffa3a3"
    elif val < 30:
        return "background-color: #a3d5ff"
    return ""

def color_util(val):
    if val > 80:
        return "background-color: #ffcccc"
    elif val < 30:
        return "background-color: #cceeff"
    return ""

if uploaded_zip:
    try:
        with zipfile.ZipFile(uploaded_zip, 'r') as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                st.error("No CSV files found.")
                st.stop()

            all_dfs = []
            for file in csv_files:
                with z.open(file) as f:
                    df = pd.read_csv(TextIOWrapper(f, encoding="utf-8", errors="ignore"), on_bad_lines='skip')
                    df.columns = df.columns.str.strip()
                    df['ShakerUnit'] = os.path.basename(file).split('.')[0]
                    all_dfs.append(df)

            df_all = pd.concat(all_dfs, ignore_index=True)

            time_col = detect_column(df_all.columns, ["timestamp", "time", "date", "yyyy/mm/dd"])
            load_col = detect_column(df_all.columns, ["load", "shaker", "rpm"])
            depth_col = detect_column(df_all.columns, ["bit depth", "hole depth"])

            if not time_col or not load_col:
                st.error("Required time/load column missing.")
                st.dataframe(df_all.head(10))
                st.stop()

            with st.expander("🧪 Show Timestamp Preview"):
                st.caption(f"First 5 values from `{time_col}`:")
                st.write(df_all[time_col].dropna().astype(str).unique()[:5])

            formats = ["%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"]
            parsed, detected_fmt = try_parse_formats(df_all[time_col], formats)

            if parsed is not None:
                df_all[time_col] = parsed
                st.success(f"✅ Detected date format: `{detected_fmt}`")
            else:
                st.error("❌ Could not parse timestamps. Check format.")
                st.stop()

            df_all[load_col] = pd.to_numeric(df_all[load_col], errors='coerce')
            df_all = df_all.dropna(subset=[time_col, load_col])
            df_all['Date'] = df_all[time_col].dt.normalize()

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

            valid_dates = sorted(df_all['Date'].dropna().unique())
            selected_date = st.sidebar.selectbox("📅 Select a Date", valid_dates[::-1],
                                                 format_func=lambda d: d.strftime("%Y-%m-%d"))

            df_day = df_all[df_all['Date'] == selected_date]
            if df_day.empty:
                st.warning("⚠️ No data for selected date.")
                st.stop()

            depth_val = int(df_day[depth_col].max()) if depth_col else len(df_day)
            shaker_load = round(df_day[load_col].mean(), 2)
            screen_util_pct = round((shaker_load / 100) * threshold, 2)
            screen_life_remaining = round((100 - screen_util_pct) * 1.5, 1)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📏 Depth", f"{depth_val}")
            col2.metric("📉 Load", f"{shaker_load:.1f}%")
            col3.metric("🧪 Utilization", f"{screen_util_pct:.1f}%")
            col4.metric("⏳ Life Left (hrs)", f"{screen_life_remaining}")

            df_day['Depth_Index'] = range(len(df_day))

            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📈 Vertical View", "🔻 Drop Flags", "🥧 Efficiency", "📂 Raw Data", "📊 Summary Report"
            ])

            with tab1:
                fig = px.line(df_day.tail(1000), y='Depth_Index', x=load_col, color='ShakerUnit', orientation='h',
                              title="Shaker Load by Depth (Vertical Layout)")
                st.plotly_chart(fig, use_container_width=True)
                if shaker_load > 80:
                    st.warning("⚠️ Load increases with depth — check mud flow rate or screen tension.")
                else:
                    st.success("✅ Load profile appears stable.")

            with tab2:
                df_day['DropFlag'] = (df_day[load_col].diff().abs() > 5).astype(int)
                fig = px.scatter(df_day, y='Depth_Index', x=load_col,
                                 color=df_day['DropFlag'].map({0: "Normal", 1: "Drop"}))
                st.plotly_chart(fig, use_container_width=True)
                if df_day['DropFlag'].sum() > 20:
                    st.warning("🔧 Frequent drops detected — recheck screen clamping or mud consistency.")
                else:
                    st.info("🟢 Low drop rate.")

            with tab3:
                fig = px.pie(values=[screen_util_pct, 100 - screen_util_pct],
                             names=["Utilized", "Unused"],
                             title="Solids Removal Efficiency")
                st.plotly_chart(fig, use_container_width=True)
                if screen_util_pct > 80:
                    st.warning("🔍 Screen nearly saturated — consider replacement soon.")
                elif screen_util_pct < 30:
                    st.info("ℹ️ Low screen usage — check bypass flow or screen type.")

            with tab4:
                st.dataframe(df_day.head(200))

            with tab5:
                st.subheader("📅 Summary Report Table")
                styled = daily_summary.style.applymap(color_load, subset=["Avg_Shaker_Load"])\
                                             .applymap(color_util, subset=["Screen_Utilization"])
                st.dataframe(styled, use_container_width=True)
                csv_data = daily_summary.to_csv(index=False).encode("utf-8")
                st.download_button("📤 Download Summary", csv_data, "daily_summary.csv", "text/csv")

    except Exception as e:
        st.error(f"🔥 Error: {e}")
