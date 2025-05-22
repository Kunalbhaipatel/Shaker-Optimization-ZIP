
import streamlit as st
import zipfile
import pandas as pd
import plotly.express as px
from io import TextIOWrapper
from PIL import Image
import os

# === Page Configuration ===
st.set_page_config(page_title="Unified Shaker ETL Dashboard", layout="wide")

# === Load Logo ===
logo_path = "assets/Prodigy_IQ_logo.png"
if os.path.exists(logo_path):
    st.image(logo_path, width=250)

st.title("🛠 Unified Shaker Data Analyzer")
st.markdown("""
This dashboard previews and analyzes multiple shaker CSV files inside a `.zip` archive.  
Supports full ETL processing with interactive charts and unified summaries.
""")

# === ETL Loader Function ===
def load_and_clean_csv(file, full=False):
    try:
        wrapper = TextIOWrapper(file, encoding='utf-8', errors='ignore')
        df = pd.read_csv(wrapper, on_bad_lines='skip') if full else pd.read_csv(wrapper, nrows=1000)
        df.columns = df.columns.str.strip()
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='ignore')
        return df
    except Exception as e:
        st.error(f"❌ Failed to load CSV: {e}")
        return pd.DataFrame()

uploaded_zip = st.file_uploader("📂 Upload ZIP file containing shaker CSVs", type='zip')

if uploaded_zip:
    try:
        zip_size = round(len(uploaded_zip.getvalue()) / (1024**2), 2)
        st.success(f"✅ Uploaded ZIP: {zip_size} MB")

        with zipfile.ZipFile(uploaded_zip) as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]

            if not csv_files:
                st.warning("No CSV files found in ZIP.")
            else:
                st.info(f"Found {len(csv_files)} shaker files: {csv_files}")

                all_dfs = []
                for csv_file in csv_files:
                    with z.open(csv_file) as f:
                        df = load_and_clean_csv(f, full=True)
                        df['ShakerSource'] = os.path.basename(csv_file).split('.')[0]
                        all_dfs.append(df)

                if all_dfs:
                    df_all = pd.concat(all_dfs, ignore_index=True)
                    st.subheader("🔍 Combined Shaker Data Overview")
                    st.dataframe(df_all.head(50))
                    st.write("📊 Summary")
                    st.write(df_all.describe(include='all'))

                    numeric_cols = df_all.select_dtypes(include='number').columns.tolist()
                    if numeric_cols:
                        st.subheader("📈 Interactive Visualizations")
                        col1, col2 = st.columns(2)

                        with col1:
                            hist_col = st.selectbox("Histogram Column", numeric_cols)
                            fig = px.histogram(df_all, x=hist_col, color='ShakerSource', nbins=50, title=f"{hist_col} Distribution")
                            st.plotly_chart(fig, use_container_width=True)

                        with col2:
                            if len(numeric_cols) >= 2:
                                x = st.selectbox("Scatter X", numeric_cols, index=0)
                                y = st.selectbox("Scatter Y", numeric_cols, index=1)
                                fig2 = px.scatter(df_all, x=x, y=y, color='ShakerSource', title=f"{x} vs {y}")
                                st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.info("No numeric columns available for plotting.")
    except Exception as e:
        st.error(f"App failed with error: {e}")
