
import streamlit as st
import pandas as pd
import numpy as np
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from src.visualizations.plots import ClinicalPlots

st.title("🎯 Subgroup Analysis (Forest Plot)")

if not st.session_state.get('data_loaded', False):
    st.warning("⚠️ Please load data from the home page first."); st.stop()

adsl = st.session_state.adsl; sdtm = st.session_state.sdtm_data

# Endpoint: any AE
ae = sdtm.get('ae')
if ae is None: st.error("AE domain required for this example (any AE endpoint)"); st.stop()

trt = 'TRT01A' if 'TRT01A' in adsl.columns else ('ARM' if 'ARM' in adsl.columns else None)
if trt is None: st.error("TRT01A/ARM not found in ADSL"); st.stop()

adsl = adsl[["USUBJID", trt, "AGE", "SEX"]].copy()
subj_with_ae = ae['USUBJID'].dropna().unique(); adsl['ANY_AE'] = adsl['USUBJID'].isin(subj_with_ae)

adsl['AGEGRP'] = pd.cut(adsl['AGE'], bins=[-np.inf, 65, np.inf], labels=['<65','≥65']) if 'AGE' in adsl.columns else 'All'
subgroups = {'Overall': None,'Sex: Male': ('SEX','M'),'Sex: Female': ('SEX','F'),'Age <65': ('AGEGRP','<65'),'Age ≥65': ('AGEGRP','≥65')}

levels = [*adsl[trt].dropna().unique()]
if len(levels) < 2: st.error("Need at least 2 treatment groups for comparison."); st.stop()
ref = levels[0]

rows = []
for label, cond in subgroups.items():
    g = adsl.copy()
    if cond is not None:
        var, val = cond; g = g[g[var] == val]
    if g.empty: continue
    g_ref = g[g[trt] == ref]; g_alt = g[g[trt] != ref]
    p_ref = g_ref['ANY_AE'].mean() if len(g_ref) else np.nan
    p_alt = g_alt['ANY_AE'].mean() if len(g_alt) else np.nan
    rd = (p_alt - p_ref) if pd.notna(p_ref) and pd.notna(p_alt) else np.nan
    se = np.sqrt((p_ref*(1-p_ref)/max(1,len(g_ref))) + (p_alt*(1-p_alt)/max(1,len(g_alt)))) if pd.notna(rd) else np.nan
    lower = rd - 1.96*se if pd.notna(se) else np.nan; upper = rd + 1.96*se if pd.notna(se) else np.nan
    rows.append({'Subgroup': label, 'Effect': rd, 'Lower': lower, 'Upper': upper, 'N': len(g)})

res = pd.DataFrame(rows)
st.dataframe(res, use_container_width=True, hide_index=True)
from src.visualizations.plots import ClinicalPlots
fig = ClinicalPlots.create_forest_plot(res, 'Subgroup', 'Effect', 'Lower', 'Upper', title='Risk Difference (ANY AE)')
st.plotly_chart(fig, use_container_width=True)
