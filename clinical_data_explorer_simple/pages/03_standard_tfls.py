
import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from src.analysis.descriptive import DescriptiveStats
from src.export.cdisc import export_table_to_excel, export_table_to_word

st.title("📋 Standard TFLs")

if not st.session_state.get('data_loaded', False):
    st.warning("⚠️ Please load data from the home page first."); st.stop()

adsl = st.session_state.adsl; sdtm = st.session_state.sdtm_data
trt_var = 'TRT01A' if 'TRT01A' in adsl.columns else ('ARM' if 'ARM' in adsl.columns else None)
if trt_var is None: st.error("No treatment variable found (TRT01A/ARM)"); st.stop()

use_saffl = st.checkbox("Safety population only (SAFFL=Y)", value=('SAFFL' in adsl.columns))
pop_df = adsl[adsl['SAFFL']=='Y'] if (use_saffl and 'SAFFL' in adsl.columns) else adsl.copy()

st.divider(); st.subheader("Table 1: Demographics by Treatment")
cols_cont = [c for c in ['AGE'] if c in pop_df.columns]
cols_cat = [c for c in ['SEX','RACE'] if c in pop_df.columns]

for c in cols_cont:
    by = pop_df.groupby(trt_var)[c].apply(lambda s: DescriptiveStats.calculate_continuous_stats(s))
    df = pd.DataFrame(by.tolist(), index=by.index); df.insert(0,'Parameter', c)
    st.dataframe(df, use_container_width=True)
    col1,col2 = st.columns(2)
    with col1: export_table_to_excel(df, suggested_name=f"table1_{c.lower()}_by_trt.xlsx")
    with col2: export_table_to_word(df, title=f"Table 1: {c} by Treatment", suggested_name=f"table1_{c.lower()}_by_trt.docx")

if cols_cat:
    parts = []
    for c in cols_cat:
        for trt, g in pop_df.groupby(trt_var):
            tbl = DescriptiveStats.calculate_categorical_stats(g[c]); tbl['Treatment'] = trt; tbl['Parameter'] = c
            parts.append(tbl[['Parameter','Category','Treatment','n','Percent','Formatted']])
    dfc = pd.concat(parts, ignore_index=True)
    st.dataframe(dfc, use_container_width=True)
    export_table_to_excel(dfc, suggested_name="table1_categorical_by_trt.xlsx")

st.divider(); st.subheader("AE Summary")
ae = sdtm.get('ae')
if ae is None:
    st.info("AE domain not available.")
else:
    subj_with_ae = ae.groupby('USUBJID').size().rename('AE_COUNT').reset_index()
    base = pop_df[['USUBJID', trt_var]].merge(subj_with_ae, on='USUBJID', how='left')
    base['HAS_AE'] = base['AE_COUNT'].fillna(0) > 0
    if 'AESER' in ae.columns:
        sae_subj = ae[ae['AESER']=='Y']['USUBJID'].unique(); base['HAS_SAE'] = base['USUBJID'].isin(sae_subj)
    else:
        base['HAS_SAE'] = False
    rows = []
    for trt, g in base.groupby(trt_var):
        n = len(g); any_ae = int(g['HAS_AE'].sum()); any_sae = int(g['HAS_SAE'].sum())
        rows.append({trt_var: trt, 'N': n, 'Subjects with ≥1 AE': f"{any_ae} ({any_ae/n*100:.1f}%)", 'Subjects with ≥1 SAE': f"{any_sae} ({any_sae/n*100:.1f}%)"})
    df_sum = pd.DataFrame(rows)
    st.dataframe(df_sum, use_container_width=True, hide_index=True)
    export_table_to_excel(df_sum, suggested_name="table_ae_summary.xlsx")
