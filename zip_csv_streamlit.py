
import streamlit as st
import zipfile
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for Streamlit Cloud
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO

st.set_page_config(page_title="CSV from ZIP (Analyzer)", layout="wide")

st.title("📦 CSV from ZIP Analyzer")
st.markdown("""
Upload a `.zip` file with one or more large `.csv` files.  
Choose which one to analyze. Fully in-memory, safe, and temporary.
""")

uploaded_zip = st.file_uploader("Upload ZIP file", type='zip')

if uploaded_zip:
    try:
        zip_size_mb = round(len(uploaded_zip.getvalue()) / (1024**2), 2)
        st.success(f"Uploaded ZIP size: {zip_size_mb} MB")

        with zipfile.ZipFile(uploaded_zip) as z:
            file_list = z.namelist()
            csv_files = [f for f in file_list if f.endswith('.csv')]

            if not csv_files:
                st.warning("No CSV files found in ZIP.")
            else:
                selected_csv = st.selectbox("📁 Select a CSV file to load", csv_files)
                file_info = z.getinfo(selected_csv)
                size_mb = round(file_info.file_size / (1024**2), 2)
                st.caption(f"Selected file size: {size_mb} MB")

                try:
                    with z.open(selected_csv) as f:
                        df = pd.read_csv(f)

                    st.subheader("📊 Data Preview")
                    st.dataframe(df.head(100))

                    st.subheader("🔢 Data Summary")
                    st.write(df.describe(include='all'))

                    st.subheader("📌 Column Types")
                    st.write(df.dtypes)

                    st.subheader("📈 Quick Visualizations")
                    numeric_cols = df.select_dtypes(include='number').columns.tolist()

                    if numeric_cols:
                        col1, col2 = st.columns(2)

                        with col1:
                            selected_hist_col = st.selectbox("Histogram: select numeric column", numeric_cols, key='hist')
                            fig1, ax1 = plt.subplots()
                            sns.histplot(df[selected_hist_col].dropna(), kde=True, ax=ax1)
                            st.pyplot(fig1)

                        with col2:
                            if len(numeric_cols) >= 2:
                                selected_x = st.selectbox("Scatter X", numeric_cols, key='x')
                                selected_y = st.selectbox("Scatter Y", numeric_cols, key='y')
                                fig2, ax2 = plt.subplots()
                                sns.scatterplot(data=df, x=selected_x, y=selected_y, ax=ax2)
                                st.pyplot(fig2)
                    else:
                        st.info("No numeric columns available for plotting.")
                except Exception as e:
                    st.error(f"⚠️ Failed to read or process the CSV: {e}")
    except zipfile.BadZipFile:
        st.error("❌ Not a valid ZIP file. Please upload a valid ZIP archive.")
