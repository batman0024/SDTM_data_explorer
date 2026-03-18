
import pandas as pd
from typing import Dict

class ADaMGenerator:
    def __init__(self, sdtm: Dict[str, pd.DataFrame], adsl: pd.DataFrame):
        self.sdtm = sdtm; self.adsl = adsl
    def make_adsl(self) -> pd.DataFrame: return self.adsl.copy()
    def make_adae(self) -> pd.DataFrame:
        ae = self.sdtm.get('ae');
        if ae is None: return pd.DataFrame()
        keep = [c for c in ['USUBJID','AEDECOD','AESTDTC','AEENDTC','AESEV','AESER','AEREL','AEOUT'] if c in ae.columns]
        adae = ae[keep].copy(); adae = adae.merge(self.adsl[['USUBJID','TRT01A']], on='USUBJID', how='left')
        return adae
    def make_adlb(self) -> pd.DataFrame:
        lb = self.sdtm.get('lb');
        if lb is None: return pd.DataFrame()
        keep = [c for c in ['USUBJID','LBTESTCD','LBDTC','LBSTRESN','LBSTRESU','LBNRIND','VISIT','LBDY'] if c in lb.columns]
        adlb = lb[keep].copy(); adlb = adlb.merge(self.adsl[['USUBJID','TRT01A']], on='USUBJID', how='left')
        if 'LBDTC' in adlb.columns and 'LBSTRESN' in adlb.columns:
            base = adlb.sort_values('LBDTC').groupby(['USUBJID','LBTESTCD']).head(1)
            base = base[['USUBJID','LBTESTCD','LBSTRESN']].rename(columns={'LBSTRESN':'BASE'})
            adlb = adlb.merge(base, on=['USUBJID','LBTESTCD'], how='left')
            adlb['CHG'] = adlb['LBSTRESN'] - adlb['BASE']
        return adlb
