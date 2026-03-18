
import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from src.analysis.descriptive import DescriptiveStats
from src.utils.helpers import detect_variable_type

st.title("🔍 Custom Analysis Builder")

if not st.session_state.get('data_loaded', False):
    st.warning("⚠️ Please load data from the home page first."); st.stop()

analysis_type = st.radio("Select Analysis Type", options=["📊 Summary Table", "📈 Trend Analysis"], horizontal=True)

if analysis_type == "📊 Summary Table":
    st.subheader("Build Summary Table")
    col1, col2 = st.columns([1, 2])
    with col1:
        domains = st.multiselect("Select Domain(s)", options=list(st.session_state.sdtm_data.keys()), default=['dm'] if 'dm' in st.session_state.sdtm_data else [])
        generate_btn = st.button("🚀 Generate Analysis", type="primary")
    with col2:
        st.markdown("#### Preview")
        if generate_btn and domains:
            df = st.session_state.sdtm_data[domains[0]]
            row_var = st.selectbox("Variable to Summarize", options=df.columns.tolist(), key='var_select')
            var_type = detect_variable_type(df[row_var]); st.info(f"Detected type: **{var_type}**")
            if var_type == 'continuous':
                stats = DescriptiveStats.calculate_continuous_stats(df[row_var])
                result_df = pd.DataFrame(list(stats.items()), columns=['Statistic', 'Value'])
            else:
                result_df = DescriptiveStats.calculate_categorical_stats(df[row_var])
            st.dataframe(result_df, use_container_width=True)
            st.download_button("📥 Export to CSV", data=result_df.to_csv(index=False).encode('utf-8'), file_name="custom_analysis.csv", mime="text/csv")
        else:
            st.info("👈 Configure your analysis and click Generate")
