
import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from src.visualizations.plots import ClinicalPlots

st.title("⏱️ AE Severity Timelines")

if not st.session_state.get('data_loaded', False):
    st.warning("⚠️ Please load data from the home page first."); st.stop()

ae = st.session_state.sdtm_data.get('ae')
if ae is None: st.error("AE domain not available."); st.stop()

subs = sorted(ae['USUBJID'].dropna().unique()); sel_sub = st.selectbox("Select Subject", options=subs)
sub_df = ae[ae['USUBJID'] == sel_sub]
if len(sub_df) > 0:
    fig = ClinicalPlots.create_ae_timeline(sub_df, subject_col='USUBJID', start_col='AESTDTC', end_col='AEENDTC', label_col='AESEV' if 'AESEV' in sub_df.columns else 'AEDECOD')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No AEs for selected subject.")
