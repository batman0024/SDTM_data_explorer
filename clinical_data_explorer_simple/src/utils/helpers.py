
import pandas as pd
from typing import Optional

def format_number(value: float, decimals: int = 1) -> str:
    if pd.isna(value): return '-'
    if decimals == 0: return f"{int(value)}"
    return f"{value:.{decimals}f}"

def get_domain_label(domain: str) -> str:
    labels = {'dm': 'Demographics','ae': 'Adverse Events','ex': 'Exposure','lb': 'Laboratory','vs': 'Vital Signs','mh': 'Medical History','cm': 'Concomitant Medications','ds': 'Disposition','rs': 'Response','tu': 'Tumor Assessment'}
    return labels.get(domain.lower(), domain.upper())

def detect_variable_type(data: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(data): return 'date'
    if pd.api.types.is_numeric_dtype(data): return 'continuous'
    return 'categorical'

def safe_divide(numerator: float, denominator: float) -> Optional[float]:
    if denominator == 0 or pd.isna(denominator): return None
    return numerator / denominator

def create_frequency_table(data: pd.Series, include_missing: bool = False) -> pd.DataFrame:
    freq = data.value_counts(dropna=True); total = len(data) if include_missing else data.notna().sum(); pct = (freq / total * 100).round(1)
    result = pd.DataFrame({'Value': freq.index, 'Frequency': freq.values, 'Percent': pct.values})
    if include_missing and data.isna().any():
        missing_count = data.isna().sum(); missing_pct = (missing_count / len(data) * 100)
        result = pd.concat([result, pd.DataFrame({'Value': ['Missing'], 'Frequency': [missing_count], 'Percent': [missing_pct]})], ignore_index=True)
    return result
