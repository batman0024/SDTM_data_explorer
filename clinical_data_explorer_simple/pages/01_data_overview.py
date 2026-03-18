
import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from src.utils.helpers import get_domain_label, detect_variable_type, create_frequency_table
from src.visualizations.plots import ClinicalPlots

st.title("📊 SDTM Data Overview")

if not st.session_state.get('data_loaded', False):
    st.warning("⚠️ Please load data from the home page first."); st.stop()

sdtm_data = st.session_state.sdtm_data
available_domains = list(sdtm_data.keys())
if not available_domains:
    st.error("No domains loaded."); st.stop()

domain = st.selectbox("Select SDTM Domain", options=available_domains, format_func=lambda x: f"{x.upper()} - {get_domain_label(x)}")

df = sdtm_data[domain]
col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("Records", f"{len(df):,}")
with col2:
    n_subjects = df['USUBJID'].nunique() if 'USUBJID' in df.columns else 'N/A'
    st.metric("Subjects", f"{n_subjects:,}" if isinstance(n_subjects, int) else n_subjects)
with col3: st.metric("Variables", len(df.columns))
with col4:
    total_cells = max(1, len(df) * len(df.columns)); missing_pct = (df.isna().sum().sum() / total_cells * 100)
    st.metric("Missing Data", f"{missing_pct:.1f}%")

st.divider()

tab1, tab2, tab3 = st.tabs(["📋 Data Preview", "📊 Variable Distribution", "⚠️ Data Quality"])

with tab1:
    st.subheader(f"{domain.upper()} Data Preview")
    n_rows = st.number_input("Rows to show", min_value=10, max_value=1000, value=100)
    st.dataframe(df.head(n_rows), use_container_width=True, height=400)
    st.download_button(label="📥 Download as CSV", data=df.to_csv(index=False).encode('utf-8'), file_name=f"{domain}.csv", mime="text/csv")

with tab2:
    st.subheader("Variable Distribution Analysis")
    variable = st.selectbox("Select Variable", options=df.columns.tolist())
    var_type = detect_variable_type(df[variable])
    col1, col2 = st.columns([2, 1])
    with col1:
        if var_type == 'categorical':
            vc = df[variable].value_counts().reset_index(); vc.columns = ['Category', 'Count']
            fig = ClinicalPlots.create_bar_chart(vc, 'Category', 'Count', title=f"Distribution of {variable}")
            st.plotly_chart(fig, use_container_width=True)
        elif var_type == 'continuous':
            fig = ClinicalPlots.create_histogram(df[variable], title=f"Distribution of {variable}")
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if var_type == 'categorical':
            st.dataframe(create_frequency_table(df[variable]), use_container_width=True, hide_index=True)
        elif var_type == 'continuous':
            from src.analysis.descriptive import DescriptiveStats
            stats = DescriptiveStats.calculate_continuous_stats(df[variable])
            st.dataframe(pd.DataFrame(list(stats.items()), columns=['Statistic', 'Value']), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Data Quality Summary")
    missing_by_var = df.isna().sum(); missing_pct_by_var = (missing_by_var / len(df) * 100).round(1)
    qdf = pd.DataFrame({'Variable': df.columns, 'Missing Count': missing_by_var.values, 'Missing %': missing_pct_by_var.values})
    qdf = qdf[qdf['Missing Count'] > 0].sort_values('Missing Count', ascending=False)
    st.dataframe(qdf, use_container_width=True, hide_index=True) if len(qdf) > 0 else st.success("✅ No missing data detected in this domain!")
