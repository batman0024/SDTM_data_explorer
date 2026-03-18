
import pandas as pd
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class PopulationDerivation:
    def create_adsl(self, dm: pd.DataFrame, ex: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        if dm is None:
            raise ValueError("DM domain is required")
        adsl = dm.copy()
        adsl = self.derive_treatment_variables(adsl)
        if ex is not None:
            adsl = self.derive_treatment_dates(adsl, ex)
            adsl = self.derive_safety_flag(adsl, ex)
        else:
            adsl['SAFFL'] = 'N'
        adsl = self.derive_itt_flag(adsl)
        logger.info(f"Created ADSL with {len(adsl)} subjects")
        return adsl
    def derive_treatment_variables(self, adsl: pd.DataFrame) -> pd.DataFrame:
        if 'ARM' in adsl.columns:
            adsl['TRT01P'] = adsl['ARM']
        if 'ACTARM' in adsl.columns:
            adsl['TRT01A'] = adsl['ACTARM']
        elif 'ARM' in adsl.columns:
            adsl['TRT01A'] = adsl['ARM']
        if 'TRT01A' in adsl.columns:
            treatment_map = {trt: i + 1 for i, trt in enumerate(sorted(adsl['TRT01A'].dropna().unique()))}
            adsl['TRT01AN'] = adsl['TRT01A'].map(treatment_map)
        return adsl
    def derive_treatment_dates(self, adsl: pd.DataFrame, ex: pd.DataFrame) -> pd.DataFrame:
        ex_dates = ex.groupby('USUBJID').agg({'EXSTDTC': 'min', 'EXENDTC': 'max'}).reset_index()
        ex_dates.columns = ['USUBJID', 'TRTSDT', 'TRTEDT']
        adsl = adsl.merge(ex_dates, on='USUBJID', how='left')
        adsl['TRTSDT'] = pd.to_datetime(adsl['TRTSDT'], errors='coerce')
        adsl['TRTEDT'] = pd.to_datetime(adsl['TRTEDT'], errors='coerce')
        if 'TRTSDT' in adsl.columns and 'TRTEDT' in adsl.columns:
            adsl['TRTDURD'] = (adsl['TRTEDT'] - adsl['TRTSDT']).dt.days + 1
        return adsl
    def derive_safety_flag(self, adsl: pd.DataFrame, ex: pd.DataFrame) -> pd.DataFrame:
        treated_subjects = ex[ex['EXDOSE'].notna()]['USUBJID'].unique()
        adsl['SAFFL'] = adsl['USUBJID'].isin(treated_subjects).map({True: 'Y', False: 'N'})
        return adsl
    def derive_itt_flag(self, adsl: pd.DataFrame) -> pd.DataFrame:
        if 'ARMCD' in adsl.columns:
            adsl['ITTFL'] = adsl['ARMCD'].notna().map({True: 'Y', False: 'N'})
        else:
            adsl['ITTFL'] = 'Y'
        return adsl
