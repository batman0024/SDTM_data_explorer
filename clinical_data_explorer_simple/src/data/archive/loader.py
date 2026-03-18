
import pandas as pd
import pyreadstat
from pathlib import Path
import logging
from typing import Dict, Optional, List, Iterable
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def dir_fingerprint(path: str, extensions: Optional[Iterable[str]] = None) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Data path does not exist: {path}")
    if extensions:
        exts = set([e.lower() for e in extensions])
    else:
        exts = {'.xpt', '.sas7bdat'}
    m = hashlib.md5()
    for f in sorted([f for f in p.iterdir() if f.is_file() and f.suffix.lower() in exts]):
        stat = f.stat()
        m.update(f.name.encode()); m.update(str(stat.st_size).encode()); m.update(str(int(stat.st_mtime)).encode())
    return m.hexdigest()

class SDTMLoader:
    REQUIRED_VARS = {
        'dm': ['USUBJID', 'STUDYID'],
        'ae': ['USUBJID', 'STUDYID'],
        'ex': ['USUBJID', 'STUDYID'],
        'lb': ['USUBJID', 'STUDYID'],
        'vs': ['USUBJID', 'STUDYID']
    }
    def __init__(self, domain_whitelist: Optional[List[str]] = None):
        self.domain_whitelist = [d.lower() for d in domain_whitelist] if domain_whitelist else None
        self.domains_loaded: Dict[str, pd.DataFrame] = {}
    def _detect_domain(self, file: Path) -> str:
        stem = file.stem.lower()
        for token in [stem, *stem.split('_')]:
            if len(token) == 2 and token.isalpha():
                return token
        return stem[:2]
    def load_domain(self, file_path: str) -> Optional[pd.DataFrame]:
        file = Path(file_path)
        try:
            if file.suffix.lower() == '.xpt':
                df, meta = pyreadstat.read_xport(str(file))
            elif file.suffix.lower() == '.sas7bdat':
                df, meta = pyreadstat.read_sas7bdat(str(file))
            else:
                logger.warning(f"Unsupported file type: {file.suffix} for {file}")
                return None
            logger.info(f"Loaded {file.name}: {len(df)} records, {len(df.columns)} variables")
            df = self._normalize(df); df = self._convert_dates(df); return df
        except Exception as e:
            logger.error(f"Error loading {file}: {str(e)}"); return None
    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [c.strip() for c in df.columns]
        for c in df.select_dtypes(include=['object']).columns:
            df[c] = df[c].astype('string').str.strip()
        return df
    def _convert_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in df.columns:
            u = col.upper()
            if u.endswith('DTC') or u.endswith('DT') or 'DATE' in u:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except Exception:
                    pass
        return df
    def load_all_domains(self, data_path: str) -> Dict[str, pd.DataFrame]:
        path = Path(data_path)
        if not path.exists():
            raise FileNotFoundError(f"Data path does not exist: {data_path}")
        domains: Dict[str, pd.DataFrame] = {}
        files = [*path.glob('*.xpt'), *path.glob('*.sas7bdat')]
        for file in files:
            domain = self._detect_domain(file)
            if self.domain_whitelist and domain not in self.domain_whitelist:
                continue
            df = self.load_domain(str(file))
            if df is not None:
                if self.validate_domain(df, domain):
                    domains[domain] = df
                    logger.info(f"Successfully loaded {domain.upper()}")
                else:
                    logger.warning(f"Validation failed for {domain.upper()}")
        logger.info(f"Loaded {len(domains)} domains: {list(domains.keys())}")
        return domains
    def validate_domain(self, df: pd.DataFrame, domain: str) -> bool:
        req = self.REQUIRED_VARS.get(domain)
        if req:
            missing = [v for v in req if v not in df.columns]
            if missing:
                logger.warning(f"Missing required variables in {domain}: {missing}")
                return False
        return True
