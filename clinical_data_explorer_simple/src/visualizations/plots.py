
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional

CLINICAL_COLORS = {'primary': '#2E86AB','secondary': '#A23B72','tertiary': '#F18F01','neutral': '#C73E1D','success': '#6A994E','warning': '#BC4B51'}
PLOT_LAYOUT = {'font': {'family': 'Arial, sans-serif', 'size': 12},'plot_bgcolor': 'white','paper_bgcolor': 'white','margin': {'l': 60, 'r': 30, 't': 60, 'b': 60},'hovermode': 'closest'}

class ClinicalPlots:
    @staticmethod
    def create_boxplot(data: pd.DataFrame, value_var: str, group_var: Optional[str] = None, title: Optional[str] = None):
        if group_var:
            fig = px.box(data, x=group_var, y=value_var, color=group_var, color_discrete_sequence=list(CLINICAL_COLORS.values()))
        else:
            fig = go.Figure(data=[go.Box(y=data[value_var])])
        fig.update_layout(**PLOT_LAYOUT, title=title, yaxis_title=value_var, xaxis_title=group_var if group_var else '', showlegend=bool(group_var))
        return fig
    @staticmethod
    def create_histogram(data: pd.Series, bins: int = 30, title: Optional[str] = None):
        fig = go.Figure(data=[go.Histogram(x=data.dropna(), nbinsx=bins, marker_color=CLINICAL_COLORS['primary'])])
        fig.update_layout(**PLOT_LAYOUT, title=title, xaxis_title=getattr(data, 'name', 'Value'), yaxis_title='Count'); return fig
    @staticmethod
    def create_bar_chart(data: pd.DataFrame, x_var: str, y_var: str, group_var: Optional[str] = None, title: Optional[str] = None):
        if group_var:
            fig = px.bar(data, x=x_var, y=y_var, color=group_var, barmode='group', color_discrete_sequence=list(CLINICAL_COLORS.values()))
        else:
            fig = go.Figure(data=[go.Bar(x=data[x_var], y=data[y_var], marker_color=CLINICAL_COLORS['primary'])])
        fig.update_layout(**PLOT_LAYOUT, title=title, xaxis_title=x_var, yaxis_title=y_var); return fig
    @staticmethod
    def create_line_plot(data: pd.DataFrame, x_var: str, y_var: str, group_var: Optional[str] = None, title: Optional[str] = None):
        if group_var:
            fig = px.line(data, x=x_var, y=y_var, color=group_var, color_discrete_sequence=list(CLINICAL_COLORS.values()), markers=True)
        else:
            fig = px.line(data, x=x_var, y=y_var, markers=True)
        fig.update_layout(**PLOT_LAYOUT, title=title, xaxis_title=x_var, yaxis_title=y_var); return fig
    @staticmethod
    def create_forest_plot(df: pd.DataFrame, label_col: str, est_col: str, lower_col: str, upper_col: str, title: str = 'Subgroup Analysis'):
        fig = go.Figure();
        fig.add_trace(go.Scatter(x=df[est_col], y=df[label_col], mode='markers', name='Effect', marker=dict(color=CLINICAL_COLORS['primary'], size=10)))
        for _, r in df.iterrows():
            fig.add_trace(go.Scatter(x=[r[lower_col], r[upper_col]], y=[r[label_col], r[label_col]], mode='lines', line=dict(color=CLINICAL_COLORS['primary']), showlegend=False))
        fig.add_vline(x=0, line_dash='dash', line_color='gray')
        fig.update_layout(**PLOT_LAYOUT, title=title, xaxis_title='Effect Size', yaxis_title='Subgroup'); return fig
    @staticmethod
    def create_ae_timeline(ae: pd.DataFrame, subject_col: str = 'USUBJID', start_col: str = 'AESTDTC', end_col: str = 'AEENDTC', label_col: str = 'AEDECOD', title: str = 'AE Timeline'):
        df = ae.copy()
        for c in [start_col, end_col]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors='coerce')
        df = df.dropna(subset=[start_col]); df[end_col] = df[end_col].fillna(df[start_col])
        df['_y'] = df[subject_col].astype(str) + ' • ' + df.get(label_col, 'AE').astype(str)
        fig = go.Figure()
        for _, r in df.iterrows():
            fig.add_trace(go.Bar(x=[(r[end_col] - r[start_col]).days + 1], y=[r['_y']], base=r[start_col], orientation='h', marker=dict(color=CLINICAL_COLORS['secondary']), showlegend=False))
        fig.update_layout(**PLOT_LAYOUT, title=title, xaxis_title='Date', yaxis_title='Subject • PT'); fig.update_yaxes(automargin=True); return fig
