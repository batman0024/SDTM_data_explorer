
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data.loader import SDTMLoader, dir_fingerprint
from src.data.database import DatabaseManager
from src.derivations.populations import PopulationDerivation

st.set_page_config(page_title="Clinical Data Explorer", page_icon="🔬", layout="wide", initial_sidebar_state="expanded")


def load_custom_css():
    st.markdown(
        """
        <style>
            .main-header {font-size: 2.2rem; font-weight: 700; color: #2E86AB; margin-bottom: 1rem;}
            .stTabs [data-baseweb="tab-list"] {gap: 1.25rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_session_state():
    st.session_state.setdefault('data_loaded', False)
    st.session_state.setdefault('sdtm_data', {})
    st.session_state.setdefault('db_manager', None)
    st.session_state.setdefault('adsl', None)
    st.session_state.setdefault('filters', {'population': 'Safety', 'treatments': [], 'date_range': None})
    st.session_state.setdefault('selected_subject', None)


@st.cache_data(show_spinner=False)
def load_study_data_cached(data_path: str, fingerprint: str):
    loader = SDTMLoader(domain_whitelist=None)
    sdtm_data = loader.load_all_domains(data_path)
    pop = PopulationDerivation()
    adsl = pop.create_adsl(sdtm_data.get('dm'), sdtm_data.get('ex'))
    return sdtm_data, adsl


@st.cache_resource(show_spinner=False)
def get_db_manager(sdtm_data: dict):
    db_manager = DatabaseManager()
    db_manager.initialize(sdtm_data)
    return db_manager


def render_sidebar():
    with st.sidebar:
        st.header("🔧 Global Settings")
        data_path = st.text_input("SDTM Data Path", value=str(Path('data') / 'sdtm'), help="Folder with SDTM .xpt and/or .sas7bdat files")
        col_a, col_b = st.columns([1,1])
        with col_a:
            file_types = st.multiselect("File types", options=['.xpt', '.sas7bdat'], default=['.xpt', '.sas7bdat'])
        with col_b:
            st.session_state['filters']['population'] = st.selectbox("Analysis Population", options=['All Subjects', 'Safety', 'ITT', 'PP'], index=1)

        if st.button("🔄 Load Data", type="primary", use_container_width=True):
            try:
                with st.spinner("Loading SDTM data..."):
                    fp = dir_fingerprint(data_path, extensions=file_types)
                    sdtm_data, adsl = load_study_data_cached(data_path, fp)
                    st.session_state.sdtm_data = sdtm_data
                    st.session_state.adsl = adsl
                    st.session_state.db_manager = get_db_manager(sdtm_data)
                    st.session_state.data_loaded = True
                    st.success("✅ Data loaded successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error loading data: {str(e)}")

        if st.session_state.data_loaded and st.session_state.adsl is not None:
            st.divider()
            adsl = st.session_state.adsl
            if 'TRT01A' in adsl.columns:
                trts = sorted(adsl['TRT01A'].dropna().unique().tolist())
            elif 'ARM' in adsl.columns:
                trts = sorted(adsl['ARM'].dropna().unique().tolist())
            else:
                trts = []
            st.session_state.filters['treatments'] = st.multiselect("Treatment Groups", options=trts, default=trts)

            st.divider()
            st.subheader("📊 Data Summary")
            n_subj = len(adsl)
            st.metric("Total Subjects", n_subj)
            if 'SAFFL' in adsl.columns:
                n_pop = (adsl['SAFFL'] == 'Y').sum(); pct = (n_pop / n_subj * 100) if n_subj else 0
                st.metric("Safety Population", f"{int(n_pop)} ({pct:.1f}%)")
            if 'ITTFL' in adsl.columns:
                n_pop = (adsl['ITTFL'] == 'Y').sum(); pct = (n_pop / n_subj * 100) if n_subj else 0
                st.metric("ITT Population", f"{int(n_pop)} ({pct:.1f}%)")


def render_dashboard():
    st.markdown('<p class="main-header">📊 Study Overview</p>', unsafe_allow_html=True)
    adsl = st.session_state.adsl
    sdtm_data = st.session_state.sdtm_data

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Subjects", len(adsl))
    with col2:
        safety_n = (adsl['SAFFL'] == 'Y').sum() if 'SAFFL' in adsl.columns else len(adsl)
        st.metric("Safety Population", int(safety_n))
    with col3:
        ae = sdtm_data.get('ae'); st.metric("Total AEs", len(ae) if ae is not None else 0)
    with col4:
        sae_n = int((ae['AESER'] == 'Y').sum()) if ae is not None and 'AESER' in ae.columns else 0
        st.metric("Serious AEs", sae_n)

    st.divider()
    tab1, tab2, tab3 = st.tabs(["📈 Overview", "✅ Data Status", "⚡ Quick Actions"])

    with tab1:
        st.subheader("Treatment Distribution")
        if 'TRT01A' in adsl.columns:
            trt_counts = adsl['TRT01A'].value_counts()
            import plotly.graph_objects as go
            fig = go.Figure(data=[go.Bar(x=trt_counts.index, y=trt_counts.values)])
            fig.update_layout(xaxis_title="Treatment", yaxis_title="Number of Subjects", showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Demographics Summary")
            if 'AGE' in adsl.columns:
                age_stats = pd.DataFrame({'Statistic': ['N','Mean','SD','Median','Min','Max'],
                                          'Value': [adsl['AGE'].count(), adsl['AGE'].mean(), adsl['AGE'].std(), adsl['AGE'].median(), adsl['AGE'].min(), adsl['AGE'].max()]})
                age_stats['Value'] = age_stats['Value'].round(1)
                st.dataframe(age_stats, hide_index=True, use_container_width=True)
        with col2:
            st.subheader("Sex Distribution")
            if 'SEX' in adsl.columns:
                sex_counts = adsl['SEX'].value_counts(); sex_pct = (sex_counts / len(adsl) * 100).round(1)
                st.dataframe(pd.DataFrame({'Sex': sex_counts.index, 'N': sex_counts.values, 'Percent': sex_pct.values}), hide_index=True, use_container_width=True)

    with tab2:
        st.subheader("Data Completeness")
        rows = []
        for domain, df in sdtm_data.items():
            if df is not None and len(df.columns) > 0:
                total_cells = len(df) * len(df.columns)
                missing_cells = df.isna().sum().sum()
                completeness = ((total_cells - missing_cells) / total_cells * 100) if total_cells else 0
                rows.append({'Domain': domain.upper(), 'Records': len(df), 'Variables': len(df.columns), 'Completeness': f"{completeness:.1f}%"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    with tab3:
        st.subheader("Quick Actions")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📋 Standard TFLs", use_container_width=True):
                st.switch_page("pages/03_standard_tfls.py")
        with col2:
            if st.button("⚠️ AE Analysis", use_container_width=True):
                st.switch_page("pages/05_adverse_events.py")
        with col3:
            if st.button("🧪 Lab Explorer", use_container_width=True):
                st.switch_page("pages/06_lab_explorer.py")


def main():
    load_custom_css()
    initialize_session_state()
    render_sidebar()
    if not st.session_state.data_loaded:
        st.markdown('<p class="main-header">🔬 Clinical Data Explorer</p>', unsafe_allow_html=True)
        st.info("👈 Load SDTM data using the sidebar to begin.")
        st.markdown("""
        ### Getting Started
        1. Set SDTM Data Path (folder with .xpt or .sas7bdat)
        2. Click Load Data
        3. Configure filters
        4. Navigate pages
        """)
    else:
        render_dashboard()

if __name__ == "__main__":
    main()
