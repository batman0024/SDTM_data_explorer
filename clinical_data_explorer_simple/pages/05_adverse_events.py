
import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from src.visualizations.plots import ClinicalPlots

st.title("⚠️ Adverse Events Analysis")

if not st.session_state.get('data_loaded', False):
    st.warning("⚠️ Please load data from the home page first."); st.stop()

ae = st.session_state.sdtm_data.get('ae')
if ae is None:
    st.error("❌ AE domain not available in loaded data."); st.stop()

col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("Total AEs", len(ae))
with col2: st.metric("Subjects with AEs", ae['USUBJID'].nunique())
with col3: st.metric("Serious AEs", int((ae['AESER']=='Y').sum()) if 'AESER' in ae.columns else 0)
with col4: st.metric("Deaths", 0)

st.divider()

tab1, tab2, tab3 = st.tabs(["Overview", "By SOC/PT", "Timelines"])
with tab1:
    st.subheader("Most Frequent Adverse Events")
    if 'AEDECOD' in ae.columns:
        top_aes = ae['AEDECOD'].value_counts().head(10).reset_index(); top_aes.columns = ['Preferred Term', 'Count']
        fig = ClinicalPlots.create_bar_chart(top_aes, 'Preferred Term', 'Count', title="Top 10 Adverse Events")
        st.plotly_chart(fig, use_container_width=True); st.dataframe(top_aes, use_container_width=True, hide_index=True)
with tab2:
    st.subheader("AE Hierarchy Explorer")
    if 'AEBODSYS' in ae.columns:
        socs = ['All'] + sorted(ae['AEBODSYS'].dropna().unique().tolist()); soc = st.selectbox("System Organ Class", options=socs)
        if soc != 'All':
            soc_data = ae[ae['AEBODSYS'] == soc]
            if 'AEDECOD' in soc_data.columns:
                pt_counts = soc_data['AEDECOD'].value_counts().reset_index(); pt_counts.columns = ['Preferred Term', 'Count']
                st.dataframe(pt_counts, use_container_width=True, hide_index=True)
        else:
            soc_counts = ae['AEBODSYS'].value_counts().reset_index(); soc_counts.columns = ['SOC', 'Count']
            fig = ClinicalPlots.create_bar_chart(soc_counts, 'SOC', 'Count', title="AEs by System Organ Class")
            st.plotly_chart(fig, use_container_width=True)
with tab3:
    st.subheader("AE Timelines (Subject-level)")
    subs = sorted(ae['USUBJID'].dropna().unique()); sel_sub = st.selectbox("Select Subject", options=subs)
    sub_df = ae[ae['USUBJID'] == sel_sub]
    if len(sub_df) > 0:
        fig = ClinicalPlots.create_ae_timeline(sub_df, subject_col='USUBJID', start_col='AESTDTC', end_col='AEENDTC', label_col='AEDECOD')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No AEs for selected subject.")
