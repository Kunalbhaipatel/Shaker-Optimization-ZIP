
import streamlit as st
import zipfile
import pandas as pd
import plotly.express as px
from io import TextIOWrapper
from datetime import datetime
import os

st.set_page_config(page_title="Final Smart Shaker Dashboard", layout="wide")
st.sidebar.image("assets/Prodigy_IQ_logo.png", width=180)
threshold = st.sidebar.slider("Utilization Threshold (%)", 50, 100, 80)
st.sidebar.image("assets/shaker_unit.png", caption="Hyperpool Shaker Unit", use_column_width=True)

st.title("📊 Final Smart Shaker Dashboard with Summary + Vertical View")

uploaded_zip = st.file_uploader("Upload ZIP with shaker CSVs", type=["zip"])

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

            preview = df_all[time_col].dropna().astype(str).unique()[:5]
            st.markdown(f"🔍 **Preview from `{time_col}`**:")
            st.write(preview)

            formats = ["%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"]
            parsed, detected_fmt = try_parse_formats(df_all[time_col], formats)

            if parsed is not None:
                df_all[time_col] = parsed
                st.success(f"✅ Detected date format: `{detected_fmt}`")
            else:
                st.error("❌ Unable to parse date column. Check format.")
                st.stop()

            df_all[load_col] = pd.to_numeric(df_all[load_col], errors='coerce')
            df_all = df_all.dropna(subset=[time_col, load_col])
            df_all['Date'] = df_all[time_col].dt.normalize()

            if df_all.empty:
                st.warning("No usable data after cleaning.")
                st.stop()

            # Daily summary
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
            st.subheader("📅 Daily Summary")
            st.dataframe(daily_summary)
            csv_data = daily_summary.to_csv(index=False).encode('utf-8')
            st.download_button("📤 Export Summary to CSV", csv_data, "daily_summary.csv", "text/csv")

            # Date filter
            valid_dates = sorted(df_all['Date'].dropna().unique())
            selected_date = st.sidebar.selectbox("Select Date to View", valid_dates[::-1],
                                                 format_func=lambda d: d.strftime("%Y-%m-%d"))
            df_day = df_all[df_all['Date'] == selected_date]

            if df_day.empty:
                st.warning("No data for selected date.")
                st.stop()

            depth_val = int(df_day[depth_col].max()) if depth_col else len(df_day)
            shaker_load = round(df_day[load_col].mean(), 2)
            screen_util_pct = round((shaker_load / 100) * threshold, 2)

            col1, col2, col3 = st.columns(3)
            col1.metric("Depth", f"{depth_val}")
            col2.metric("Avg Load", f"{shaker_load:.1f}%")
            col3.metric("Utilization", f"{screen_util_pct:.1f}%")

            df_day['Depth_Index'] = range(len(df_day))

            tab1, tab2, tab3, tab4 = st.tabs(["Vertical View", "Drop Flags", "Efficiency", "Raw Data"])

            with tab1:
                fig = px.line(df_day.tail(1000), y='Depth_Index', x=load_col, color='ShakerUnit',
                              orientation='h', title="Shaker Load vs Depth")
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
### 🧠 Screen Change Guidance
- <50% Utilization = screen healthy
- 50–80% = monitor performance
- >80% = consider screen replacement
Adjust shaker feed rate to reduce stress and extend screen life.
            """)

    except Exception as e:
        st.error(f"🔥 Error: {e}")
