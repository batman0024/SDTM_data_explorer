
import pandas as pd
import numpy as np
from typing import List, Dict, Optional

class DescriptiveStats:
    @staticmethod
    def calculate_continuous_stats(data: pd.Series, stats: Optional[List[str]] = None, decimals: int = 1) -> Dict[str, float]:
        if stats is None:
            stats = ['n', 'mean', 'sd', 'median', 'min', 'max']
        data_clean = data.dropna(); results = {}
        results['N'] = int(len(data_clean)) if ('n' in stats or 'N' in stats) else None
        if 'mean' in stats or 'Mean' in stats:
            results['Mean'] = round(float(data_clean.mean()), decimals) if len(data_clean) > 0 else np.nan
        if 'sd' in stats or 'SD' in stats:
            results['SD'] = round(float(data_clean.std()), decimals) if len(data_clean) > 0 else np.nan
        if 'median' in stats or 'Median' in stats:
            results['Median'] = round(float(data_clean.median()), decimals) if len(data_clean) > 0 else np.nan
        if 'min' in stats or 'Min' in stats:
            results['Min'] = round(float(data_clean.min()), decimals) if len(data_clean) > 0 else np.nan
        if 'max' in stats or 'Max' in stats:
            results['Max'] = round(float(data_clean.max()), decimals) if len(data_clean) > 0 else np.nan
        if 'q1' in stats or 'Q1' in stats:
            results['Q1'] = round(float(data_clean.quantile(0.25)), decimals) if len(data_clean) > 0 else np.nan
        if 'q3' in stats or 'Q3' in stats:
            results['Q3'] = round(float(data_clean.quantile(0.75)), decimals) if len(data_clean) > 0 else np.nan
        return results
    @staticmethod
    def calculate_categorical_stats(data: pd.Series, denominator: Optional[int] = None, format_str: str = 'n (%)') -> pd.DataFrame:
        counts = data.value_counts(dropna=True)
        if denominator is None:
            denominator = int(data.dropna().shape[0])
        percentages = (counts / denominator * 100).round(1)
        return pd.DataFrame({'Category': counts.index, 'n': counts.values, 'Percent': percentages.values, 'Formatted': [f"{int(n)} ({p:.1f}%)" for n,p in zip(counts.values, percentages.values)]})
