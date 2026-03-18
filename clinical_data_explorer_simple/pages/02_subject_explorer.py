
import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

st.title("👥 Subject Explorer")

if not st.session_state.get('data_loaded', False):
    st.warning("⚠️ Please load data from the home page first."); st.stop()

adsl = st.session_state.adsl; sdtm_data = st.session_state.sdtm_data

col1, col2 = st.columns([3, 1])
with col1:
    subject_search = st.text_input("🔍 Search Subject ID", placeholder="Enter subject ID or part of it...")
    matching_subjects = adsl[adsl['USUBJID'].str.contains(subject_search, case=False, na=False)]['USUBJID'].tolist() if subject_search else adsl['USUBJID'].tolist()
with col2:
    if st.button("🎲 Random Subject"):
        import random; st.session_state.selected_subject = random.choice(adsl['USUBJID'].tolist())

if not matching_subjects:
    st.error("No subjects found."); st.stop()

def_idx = matching_subjects.index(st.session_state.selected_subject) if st.session_state.selected_subject in matching_subjects else 0
subject_id = st.selectbox("Select Subject", options=matching_subjects, index=def_idx)

st.session_state.selected_subject = subject_id
row = adsl[adsl['USUBJID'] == subject_id].iloc[0]

st.markdown("### 📋 Subject Profile")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("**Treatment**"); trt = row.get('TRT01A', row.get('ARM', 'N/A')); st.markdown(f"*{trt}*")
    st.markdown("**Age / Sex**"); st.markdown(f"*{row.get('AGE','N/A')}y / {row.get('SEX','N/A')}*")
with col2:
    st.markdown("**Study Status**"); st.markdown("*Active*")
    st.markdown("**Race**"); st.markdown(f"*{row.get('RACE','N/A')}*")
with col3:
    st.markdown("**Treatment Duration**"); st.markdown(f"*{row.get('TRTDURD','N/A')} days*")
    st.markdown("**First Dose**"); st.markdown(f"*{row.get('TRTSDT','N/A')}*")
with col4:
    ae = sdtm_data.get('ae'); sub_ae = ae[ae['USUBJID'] == subject_id] if ae is not None else pd.DataFrame()
    total_aes = len(sub_ae); saes = int((sub_ae['AESER'] == 'Y').sum()) if 'AESER' in sub_ae.columns else 0
    st.markdown("**Total AEs**"); st.markdown(f"*{total_aes}*")
    st.markdown("**SAEs**"); st.markdown(f"*{saes}*")

st.divider()

tab1, tab2, tab3 = st.tabs(["💊 Exposure", "⚠️ Adverse Events", "🧪 Labs"])
with tab1:
    st.subheader("Treatment Exposure")
    ex = sdtm_data.get('ex')
    if ex is not None:
        sub = ex[ex['USUBJID'] == subject_id]
        if len(sub) > 0:
            cols = [c for c in ['EXTRT','EXDOSE','EXDOSU','EXSTDTC','EXENDTC','EXDOSFRQ'] if c in sub.columns]
            st.dataframe(sub[cols], use_container_width=True, hide_index=True)
        else:
            st.info("No exposure records found for this subject.")
    else:
        st.warning("EX domain not available.")

with tab2:
    st.subheader("Adverse Events")
    if ae is not None:
        sub = ae[ae['USUBJID'] == subject_id]
        if len(sub) > 0:
            c1,c2,c3 = st.columns(3)
            with c1: st.metric("Total AEs", len(sub))
            with c2: st.metric("Serious AEs", int((sub['AESER']=='Y').sum()) if 'AESER' in sub.columns else 0)
            with c3: st.metric("Grade 3+ AEs", int((sub['AESEV'].isin(['SEVERE','GRADE 3','GRADE 4'])).sum()) if 'AESEV' in sub.columns else 0)
            dcols = [c for c in ['AEDECOD','AESTDTC','AEENDTC','AESEV','AESER','AEREL','AEOUT'] if c in sub.columns]
            st.dataframe(sub[dcols], use_container_width=True, hide_index=True)
        else:
            st.success("✅ No adverse events reported for this subject.")
    else:
        st.warning("AE domain not available.")

with tab3:
    st.subheader("Laboratory Results")
    lb = sdtm_data.get('lb')
    if lb is not None:
        slb = lb[lb['USUBJID'] == subject_id]
        if len(slb) > 0 and 'LBTESTCD' in slb.columns:
            params = sorted(slb['LBTESTCD'].dropna().unique()); param = st.selectbox("Select Lab Parameter", options=params)
            pdata = slb[slb['LBTESTCD'] == param]
            time_var = 'VISIT' if 'VISIT' in pdata.columns else ('LBDY' if 'LBDY' in pdata.columns else None)
            if time_var and 'LBSTRESN' in pdata.columns:
                from src.visualizations.plots import ClinicalPlots
                pdata = pdata.sort_values(time_var)
                fig = ClinicalPlots.create_line_plot(pdata, time_var, 'LBSTRESN', title=f"{param} Over Time")
                st.plotly_chart(fig, use_container_width=True)
            dcols = [c for c in ['VISIT','LBDTC','LBSTRESN','LBSTRESU','LBNRIND'] if c in pdata.columns]
            st.dataframe(pdata[dcols], use_container_width=True, hide_index=True)
        else:
            st.info("No lab records found or LBTESTCD not available.")
    else:
        st.warning("LB domain not available.")
