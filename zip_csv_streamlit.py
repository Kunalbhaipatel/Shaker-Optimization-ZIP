
import streamlit as st
import zipfile
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from io import TextIOWrapper

st.set_page_config(page_title="Stream-Safe ZIP CSV Viewer", layout="wide")
st.title("📦 Stream-Safe CSV from ZIP Analyzer")
st.markdown("""
Upload a `.zip` file containing large `.csv` files. This version reads a sample portion 
of the CSV **line-by-line** for stability on Streamlit Cloud.
""")

uploaded_zip = st.file_uploader("Upload ZIP file", type='zip')

if uploaded_zip:
    try:
        zip_size_mb = round(len(uploaded_zip.getvalue()) / (1024**2), 2)
        st.success(f"Uploaded ZIP size: {zip_size_mb} MB")

        with zipfile.ZipFile(uploaded_zip) as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]

            if not csv_files:
                st.warning("No CSV files found in ZIP.")
            else:
                selected_csv = st.selectbox("📁 Select a CSV file", csv_files)

                with z.open(selected_csv) as f:
                    st.caption("Reading first 1000 lines for safe preview...")
                    wrapper = TextIOWrapper(f, encoding='utf-8', errors='ignore')
                    df = pd.read_csv(wrapper, nrows=1000)

                    df.columns = df.columns.str.strip()
                    st.dataframe(df.head(50))
                    st.write("Shape:", df.shape)

                    if not df.empty:
                        st.write("🔢 Summary")
                        st.write(df.describe(include='all'))

                        numeric_cols = df.select_dtypes(include='number').columns.tolist()
                        if numeric_cols:
                            col1, col2 = st.columns(2)
                            with col1:
                                selected_col = st.selectbox("📊 Histogram Column", numeric_cols)
                                fig, ax = plt.subplots()
                                sns.histplot(df[selected_col].dropna(), kde=True, ax=ax)
                                st.pyplot(fig)
                            with col2:
                                if len(numeric_cols) >= 2:
                                    x_col = st.selectbox("X Axis", numeric_cols, index=0)
                                    y_col = st.selectbox("Y Axis", numeric_cols, index=1)
                                    fig2, ax2 = plt.subplots()
                                    sns.scatterplot(data=df, x=x_col, y=y_col, ax=ax2)
                                    st.pyplot(fig2)
                        else:
                            st.info("No numeric data for visualization.")
    except Exception as e:
        st.error(f"App failed with error: {e}")
