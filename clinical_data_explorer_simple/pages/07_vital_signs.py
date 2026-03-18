
import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from src.visualizations.plots import ClinicalPlots

st.title("❤️ Vital Signs Trends")

if not st.session_state.get('data_loaded', False):
    st.warning("⚠️ Please load data from the home page first."); st.stop()

vs = st.session_state.sdtm_data.get('vs'); adsl = st.session_state.adsl
if vs is None: st.error("VS domain not available."); st.stop()

tests = sorted(vs['VSTESTCD'].dropna().unique()) if 'VSTESTCD' in vs.columns else []
if not tests: st.error("VSTESTCD not found."); st.stop()

test = st.selectbox("Vital Sign (VSTESTCD)", options=tests)

vdf = vs[vs['VSTESTCD'] == test].copy()
xt = 'VISIT' if 'VISIT' in vdf.columns else ('VSDY' if 'VSDY' in vdf.columns else None)
if xt and 'VSSTRESN' in vdf.columns and 'USUBJID' in vdf.columns:
    vdf = vdf.merge(adsl[['USUBJID','TRT01A']], on='USUBJID', how='left')
    agg = vdf.groupby([xt, 'TRT01A'])['VSSTRESN'].mean().reset_index()
    fig = ClinicalPlots.create_line_plot(agg, xt, 'VSSTRESN', group_var='TRT01A', title=f"{test} Mean Over {xt}")
    st.plotly_chart(fig, use_container_width=True)

if 'VSSTRESN' in vdf.columns and 'TRT01A' in vdf.columns:
    fig2 = ClinicalPlots.create_boxplot(vdf, value_var='VSSTRESN', group_var='TRT01A', title=f"{test} by Treatment")
    st.plotly_chart(fig2, use_container_width=True)
