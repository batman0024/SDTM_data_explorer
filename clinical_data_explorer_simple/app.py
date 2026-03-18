# app.py — Clinical Data Explorer
# - Adds "Browse files" (upload) OR "Folder path"
# - Robust Quick Actions navigation:
#     * Use Streamlit's registered page links when available
#     * Otherwise fall back to running the page script inline (importlib)

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os
import tempfile
import hashlib
import importlib.util

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data.loader import SDTMLoader, dir_fingerprint
from src.data.database import DatabaseManager
from src.derivations.populations import PopulationDerivation


st.set_page_config(
    page_title="Clinical Data Explorer",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)


# -----------------------------
# Styling / Session state setup
# -----------------------------
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
    # inline router
    st.session_state.setdefault('_inline_page', None)


# -----------------------------
# Cache helpers for data loading
# -----------------------------
def uploaded_files_fingerprint(files) -> str:
    """
    Create a stable hash for a set of uploaded files (name + size + first/last bytes)
    to drive Streamlit cache invalidation for uploads.
    """
    m = hashlib.md5()
    for f in sorted(files, key=lambda x: (x.name, x.size or 0)):
        m.update(f.name.encode())
        m.update(str(f.size or 0).encode())
        content = f.getvalue()
        if content:
            m.update(content[:1024])
            m.update(content[-1024:] if len(content) > 1024 else content)
    return m.hexdigest()


@st.cache_data(show_spinner=False)
def load_study_data_cached(data_path: str, fingerprint: str):
    """
    Cached loader for a folder path (uses dir_fingerprint for invalidation).
    """
    loader = SDTMLoader(domain_whitelist=None)
    sdtm_data = loader.load_all_domains(data_path)

    pop = PopulationDerivation()
    adsl = pop.create_adsl(sdtm_data.get('dm'), sdtm_data.get('ex'))
    return sdtm_data, adsl


@st.cache_data(show_spinner=False)
def load_study_data_from_uploads(files, uploads_fp: str):
    """
    Save uploaded files into a temp folder and load with the normal SDTMLoader.
    Returns sdtm_data and adsl.
    """
    temp_root = tempfile.mkdtemp(prefix="sdtm_uploads_")

    # Persist each uploaded file using its original name
    for upl in files:
        suffix = Path(upl.name).suffix.lower()
        if suffix not in (".xpt", ".sas7bdat"):
            continue
        tgt = Path(temp_root) / Path(upl.name).name
        with open(tgt, "wb") as out:
            out.write(upl.getvalue())

    loader = SDTMLoader(domain_whitelist=None)
    sdtm_data = loader.load_all_domains(temp_root)

    pop = PopulationDerivation()
    adsl = pop.create_adsl(sdtm_data.get('dm'), sdtm_data.get('ex'))
    return sdtm_data, adsl, temp_root


@st.cache_resource(show_spinner=False)
def get_db_manager(sdtm_data: dict):
    db_manager = DatabaseManager()
    db_manager.initialize(sdtm_data)
    return db_manager


# ---------------------------------
# Page registry for robust nav
# ---------------------------------
def get_registered_pages_map() -> dict:
    """
    Returns a dict mapping the RELATIVE page path Streamlit expects
    (e.g., 'pages/03_standard_tfls.py') -> absolute path on disk.

    Uses Streamlit's internal page registry so our Quick Actions
    only render links that Streamlit can actually open.
    """
    try:
        # Supported in Streamlit 1.22–1.31
        from streamlit.source_util import get_pages
        pages_dict = get_pages(str(Path(__file__)))
    except Exception:
        pages_dict = {}

    rel_to_abs = {}
    here = Path(__file__).parent.resolve()
    for _, meta in pages_dict.items():
        abs_path = Path(meta.get("page_script_path", "")).resolve()
        rel = Path(os.path.relpath(abs_path, start=here)).as_posix()
        rel_to_abs[rel] = str(abs_path)
    return rel_to_abs


# ---------------------------------
# Inline fallback loader (importlib)
# ---------------------------------
def run_page_script_inline(rel_path: str):
    """
    Import and execute a page script inline (inside the current app),
    so navigation works even if Streamlit hasn't registered the page.

    This does NOT rely on st.switch_page / st.page_link. It uses
    importlib to execute the .py file under pages/.
    """
    if not rel_path:
        return
    here = Path(__file__).parent.resolve()
    file = (here / rel_path).resolve()
    if not file.exists():
        st.error(f"Inline loader couldn't find: `{rel_path}`")
        return

    # Unique module name to allow re-execution on changes
    mod_name = f"_inline_{file.stem}_{int(file.stat().st_mtime)}"
    spec = importlib.util.spec_from_file_location(mod_name, str(file))
    if spec is None or spec.loader is None:
        st.error(f"Unable to load spec for `{rel_path}`")
        return

    try:
        module = importlib.util.module_from_spec(spec)
        # Ensure fresh import
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        spec.loader.exec_module(module)  # Page code executes here
    except SystemExit:
        # st.stop() raises SystemExit internally; ignore to avoid killing host app
        pass
    except Exception as e:
        st.error(f"Error while rendering `{rel_path}` inline: {e}")


# -----------------------------
# Sidebar (load data UI)
# -----------------------------
def render_sidebar():
    with st.sidebar:
        st.header("🔧 Global Settings")

        # Data source toggle
        data_source = st.radio(
            "Data Source",
            options=["Folder path", "Upload files"],
            horizontal=True
        )

        # Common options
        col_a, col_b = st.columns([1, 1])
        with col_a:
            file_types = st.multiselect(
                "File types",
                options=['.xpt', '.sas7bdat'],
                default=['.xpt', '.sas7bdat'],
                help="Choose which SDTM file types to scan",
            )
        with col_b:
            st.session_state['filters']['population'] = st.selectbox(
                "Analysis Population",
                options=['All Subjects', 'Safety', 'ITT', 'PP'],
                index=1,
            )

        # Source-specific inputs
        uploaded_files = None
        data_path = None

        if data_source == "Folder path":
            data_path = st.text_input(
                "SDTM Data Path",
                value=str(Path('data') / 'sdtm'),
                help="Folder with SDTM .xpt and/or .sas7bdat files (tip: use forward slashes on Windows, e.g., data/sdtm)"
            )
        else:
            uploaded_files = st.file_uploader(
                "Upload SDTM files (.xpt or .sas7bdat) – multiple allowed",
                type=["xpt", "sas7bdat"],
                accept_multiple_files=True
            )

        if st.button("🔄 Load Data", type="primary", use_container_width=True):
            try:
                with st.spinner("Loading SDTM data..."):
                    if data_source == "Folder path":
                        # Use directory fingerprint for caching invalidation
                        fp = dir_fingerprint(data_path, extensions=file_types)
                        sdtm_data, adsl = load_study_data_cached(data_path, fp)
                        st.session_state.sdtm_data = sdtm_data
                        st.session_state.adsl = adsl
                        st.session_state.db_manager = get_db_manager(sdtm_data)
                        st.session_state.data_loaded = True
                        st.success("✅ Data loaded successfully!")
                        st.rerun()
                    else:
                        if not uploaded_files:
                            st.warning("Please upload one or more SDTM files.")
                            st.stop()
                        uploads_fp = uploaded_files_fingerprint(uploaded_files)
                        sdtm_data, adsl, _temp = load_study_data_from_uploads(uploaded_files, uploads_fp)
                        st.session_state.sdtm_data = sdtm_data
                        st.session_state.adsl = adsl
                        st.session_state.db_manager = get_db_manager(sdtm_data)
                        st.session_state.data_loaded = True
                        st.success("✅ Data loaded successfully from uploaded files!")
                        st.rerun()

            except FileNotFoundError as e:
                st.error(f"❌ Error loading data: {str(e)}")
                st.info("Tip: On Windows, use forward slashes like `data/sdtm` instead of backslashes.")
            except Exception as e:
                st.error(f"❌ Error loading data: {str(e)}")

        # The rest of the sidebar after data load
        if st.session_state.data_loaded and st.session_state.adsl is not None:
            st.divider()
            adsl = st.session_state.adsl

            # Treatments list
            if 'TRT01A' in adsl.columns:
                trts = sorted(adsl['TRT01A'].dropna().unique().tolist())
            elif 'ARM' in adsl.columns:
                trts = sorted(adsl['ARM'].dropna().unique().tolist())
            else:
                trts = []
            st.session_state.filters['treatments'] = st.multiselect(
                "Treatment Groups",
                options=trts,
                default=trts,
            )

            st.divider()
            st.subheader("📊 Data Summary")
            n_subj = len(adsl)
            st.metric("Total Subjects", n_subj)
            if 'SAFFL' in adsl.columns:
                n_pop = (adsl['SAFFL'] == 'Y').sum()
                pct = (n_pop / n_subj * 100) if n_subj else 0
                st.metric("Safety Population", f"{int(n_pop)} ({pct:.1f}%)")
            if 'ITTFL' in adsl.columns:
                n_pop = (adsl['ITTFL'] == 'Y').sum()
                pct = (n_pop / n_subj * 100) if n_subj else 0
                st.metric("ITT Population", f"{int(n_pop)} ({pct:.1f}%)")


# -----------------------------
# Main dashboard (home page)
# -----------------------------
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
        ae = sdtm_data.get('ae')
        st.metric("Total AEs", len(ae) if ae is not None else 0)
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
                age_stats = pd.DataFrame({
                    'Statistic': ['N','Mean','SD','Median','Min','Max'],
                    'Value': [adsl['AGE'].count(), adsl['AGE'].mean(), adsl['AGE'].std(),
                              adsl['AGE'].median(), adsl['AGE'].min(), adsl['AGE'].max()]
                })
                age_stats['Value'] = age_stats['Value'].round(1)
                st.dataframe(age_stats, hide_index=True, use_container_width=True)
        with col2:
            st.subheader("Sex Distribution")
            if 'SEX' in adsl.columns:
                sex_counts = adsl['SEX'].value_counts()
                sex_pct = (sex_counts / len(adsl) * 100).round(1)
                st.dataframe(pd.DataFrame({'Sex': sex_counts.index, 'N': sex_counts.values, 'Percent': sex_pct.values}),
                             hide_index=True, use_container_width=True)

    with tab2:
        st.subheader("Data Completeness")
        rows = []
        for domain, df in sdtm_data.items():
            if df is not None and len(df.columns) > 0:
                total_cells = len(df) * len(df.columns)
                missing_cells = df.isna().sum().sum()
                completeness = ((total_cells - missing_cells) / total_cells * 100) if total_cells else 0
                rows.append({'Domain': domain.upper(), 'Records': len(df), 'Variables': len(df.columns),
                             'Completeness': f"{completeness:.1f}%"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    with tab3:
        st.subheader("Quick Actions")

        # Use Streamlit's registered page list (prevents broken links when available)
        reg_map = get_registered_pages_map()
        c1, c2, c3 = st.columns(3)

        def add_link_or_inline(col, rel_path: str, label: str, key_btn: str):
            """
            If Streamlit registered the page, show a proper page link.
            Otherwise, show a button that renders the page inline as a fallback.
            """
            with col:
                if rel_path in reg_map and hasattr(st, "page_link"):
                    st.page_link(rel_path, label=label)
                else:
                    if st.button(label, use_container_width=True, key=key_btn):
                        st.session_state['_inline_page'] = rel_path

        # Point to the pages you have (simple names):
        add_link_or_inline(c1, "pages/03_standard_tfls.py", "📋 Standard TFLs", "btn_std_tfls")
        add_link_or_inline(c2, "pages/05_adverse_events.py", "⚠️ AE Analysis", "btn_ae")
        add_link_or_inline(c3, "pages/06_lab_explorer.py", "🧪 Lab Explorer", "btn_lab")

        # Inline fallback renderer (if a button above was clicked)
        if st.session_state.get('_inline_page'):
            st.divider()
            target = st.session_state['_inline_page']
            st.subheader(f"Inline view • {Path(target).name}")
            run_page_script_inline(target)

        # --- Optional diagnostics ---
        with st.expander("⚙️ Navigation diagnostics"):
            here = Path(__file__).parent.resolve()
            st.write("**Main script folder:**", f"`{here}`")
            st.write("**Registered pages (as seen by Streamlit):**")
            df = pd.DataFrame(
                [{"RelPath": k, "ExistsOnDisk": Path(v).exists(), "AbsPath": v} for k, v in reg_map.items()]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.info(
                "If a page is missing here, Streamlit didn't register it at startup:\n"
                "- Ensure the file exists BEFORE starting `streamlit run app.py`\n"
                "- Folder must be named `pages` (sibling to `app.py`)\n"
                "- Filenames must end with `.py` (Windows may hide extensions)\n"
                "- If you added/renamed a page, stop & restart Streamlit\n"
                "- Prefer running from a local path or mapped drive vs UNC share"
            )


# -----------------------------
# Entrypoint
# -----------------------------
def main():
    load_custom_css()
    initialize_session_state()
    render_sidebar()
    if not st.session_state.data_loaded:
        st.markdown('<p class="main-header">🔬 Clinical Data Explorer</p>', unsafe_allow_html=True)
        st.info("👈 Load SDTM data using the sidebar to begin.")
        st.markdown("""
        ### Getting Started
        1. Set SDTM Data Path (folder with .xpt or .sas7bdat) **or** upload files
        2. Click Load Data
        3. Configure filters
        4. Navigate pages
        """)
    else:
        render_dashboard()


if __name__ == "__main__":
    main()