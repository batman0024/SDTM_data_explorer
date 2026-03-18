
import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from src.visualizations.plots import ClinicalPlots

st.title("🧪 Lab Explorer")

if not st.session_state.get('data_loaded', False):
    st.warning("⚠️ Please load data from the home page first."); st.stop()

lb = st.session_state.sdtm_data.get('lb'); adsl = st.session_state.adsl
if lb is None: st.error("LB domain not available."); st.stop()

params = sorted(lb['LBTESTCD'].dropna().unique()) if 'LBTESTCD' in lb.columns else []
if not params: st.error("LBTESTCD not found."); st.stop()

param = st.selectbox("Parameter (LBTESTCD)", options=params)
param_df = lb[lb['LBTESTCD'] == param].copy()

x_var = 'VISIT' if 'VISIT' in param_df.columns else ('LBDY' if 'LBDY' in param_df.columns else None)
if x_var and 'LBSTRESN' in param_df.columns:
    st.subheader("Trend by Treatment")
    if 'USUBJID' in param_df.columns and 'TRT01A' in adsl.columns:
        param_df = param_df.merge(adsl[['USUBJID','TRT01A']], on='USUBJID', how='left')
        agg = param_df.groupby([x_var, 'TRT01A'])['LBSTRESN'].mean().reset_index()
        fig = ClinicalPlots.create_line_plot(agg, x_var, 'LBSTRESN', group_var='TRT01A', title=f"{param} Mean Over {x_var}")
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Shift Table (Baseline → Worst)")
if {'LBNRIND','USUBJID'}.issubset(param_df.columns):
    base = param_df.sort_values('LBDTC' if 'LBDTC' in param_df.columns else x_var).groupby('USUBJID').first().reset_index()[['USUBJID','LBNRIND']].rename(columns={'LBNRIND':'BASE'})
    worst = param_df.groupby('USUBJID')['LBNRIND'].apply(lambda s: s.mode().iat[0] if not s.mode().empty else s.dropna().iloc[0] if s.dropna().shape[0] else None).reset_index().rename(columns={'LBNRIND':'WORST'})
    shift = base.merge(worst, on='USUBJID', how='left')
    st.dataframe(shift.value_counts(['BASE','WORST']).reset_index(name='N'), use_container_width=True)
else:
    st.info("LBNRIND not available for shift table.")
