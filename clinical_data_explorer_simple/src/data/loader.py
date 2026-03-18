import pandas as pd
import pyreadstat
from pathlib import Path
import logging
from typing import Dict, Optional, List, Iterable, Tuple
import hashlib
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def dir_fingerprint(path: str, extensions: Optional[Iterable[str]] = None) -> str:
    """
    Create a fingerprint for a directory based on the set of files with matching extensions.
    Used by Streamlit caching to invalidate only when files change.
    """
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
        m.update(f.name.encode())
        m.update(str(stat.st_size).encode())
        m.update(str(int(stat.st_mtime)).encode())
    return m.hexdigest()


class SDTMLoader:
    """
    SDTM Loader that supports:
      - SAS XPORT (.xpt) and SAS7BDAT (.sas7bdat)
      - Domain auto-detection from filenames
      - Flexible file discovery (no need to pass a fixed path)

    Usage patterns:
      1) Legacy (fixed folder):
         loader.load_all_domains("data/sdtm")

      2) Auto-discover from current folder (no arguments):
         loader.load_all_domains()  # searches recursively from cwd

      3) Auto-discover from a chosen start directory with controls:
         loader.load_all_domains(
             data_path=None,
             auto_discover=True,
             search_from="/path/to/search",
             extensions=[".xpt",".sas7bdat"],
             recursive=True,
             max_depth=6,
             include_hidden=False
         )
    """

    REQUIRED_VARS = {
        'dm': ['USUBJID', 'STUDYID'],
        'ae': ['USUBJID', 'STUDYID'],
        'ex': ['USUBJID', 'STUDYID'],
        'lb': ['USUBJID', 'STUDYID'],
        'vs': ['USUBJID', 'STUDYID'],
    }

    def __init__(self, domain_whitelist: Optional[List[str]] = None):
        self.domain_whitelist = [d.lower() for d in domain_whitelist] if domain_whitelist else None
        self.domains_loaded: Dict[str, pd.DataFrame] = {}

    # -------------------------------
    # New: file discovery capabilities
    # -------------------------------
    @staticmethod
    def _within_depth(base: Path, target: Path, max_depth: Optional[int]) -> bool:
        if max_depth is None:
            return True
        try:
            rel = target.relative_to(base)
        except Exception:
            return False
        depth = len(rel.parts) - 1  # files at base have depth 0
        return depth <= max_depth

    @staticmethod
    def find_sdtm_files(
        start_dir: str = ".",
        extensions: Optional[Iterable[str]] = None,
        recursive: bool = True,
        max_depth: Optional[int] = 6,
        include_hidden: bool = False,
    ) -> List[Path]:
        """
        Search for SDTM files from a starting directory.

        Args:
            start_dir: root folder to start searching from (default: current working dir).
            extensions: file extensions to include (default: .xpt + .sas7bdat).
            recursive: whether to search recursively (default: True).
            max_depth: maximum directory depth relative to start_dir (default: 6).
                       Set to None for unlimited depth.
            include_hidden: include hidden directories/files (default: False).

        Returns:
            List[Path]: files discovered that match extensions.
        """
        exts = set([e.lower() for e in (extensions or [".xpt", ".sas7bdat"])])
        root = Path(start_dir).resolve()
        if not root.exists():
            logger.warning(f"Search root does not exist: {root}")
            return []

        files: List[Path] = []
        if recursive:
            # Walk directory tree respecting depth and hidden filters
            for dirpath, dirnames, filenames in os.walk(root):
                # Skip hidden directories if required
                if not include_hidden:
                    dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                current_dir = Path(dirpath)
                if not SDTMLoader._within_depth(root, current_dir, max_depth):
                    # Prune deeper traversal by mutating dirnames
                    dirnames[:] = []
                    continue
                for fn in filenames:
                    if not include_hidden and fn.startswith("."):
                        continue
                    p = current_dir / fn
                    if p.suffix.lower() in exts:
                        files.append(p)
        else:
            # Only the top-level directory
            for p in root.iterdir():
                if p.is_file() and p.suffix.lower() in exts:
                    if include_hidden or not p.name.startswith("."):
                        files.append(p)

        files_sorted = sorted(set(files))
        logger.info(f"Discovered {len(files_sorted)} SDTM file(s) under {root}")
        return files_sorted

    # -------------------------------
    # Core reading logic
    # -------------------------------
    def _detect_domain(self, file: Path) -> str:
        stem = file.stem.lower()
        # Accept common patterns: dm.xpt, sdtm_dm.sas7bdat, xyz_dm.xpt
        for token in [stem, *stem.split('_')]:
            if len(token) == 2 and token.isalpha():
                return token
        # fallback: first two chars
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
            df = self._normalize(df)
            df = self._convert_dates(df)
            return df
        except Exception as e:
            logger.error(f"Error loading {file}: {str(e)}")
            return None

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

    # ------------------------------------
    # New: auto-discovery-aware entrypoint
    # ------------------------------------
    def load_all_domains(
        self,
        data_path: Optional[str] = None,
        *,
        auto_discover: bool = True,
        search_from: str = ".",
        extensions: Optional[Iterable[str]] = None,
        recursive: bool = True,
        max_depth: Optional[int] = 6,
        include_hidden: bool = False,
    ) -> Dict[str, pd.DataFrame]:
        """
        Load all SDTM domains from either:
          - a fixed directory (data_path), or
          - auto-discovery (search_from) when data_path is None and auto_discover=True.

        Returns:
            dict: {domain_name (lower): DataFrame}
        """
        domains: Dict[str, pd.DataFrame] = {}

        if data_path:
            # Classic behavior from a fixed folder (non-recursive)
            path = Path(data_path)
            if not path.exists():
                raise FileNotFoundError(f"Data path does not exist: {data_path}")
            files = [*path.glob("*.xpt"), *path.glob("*.sas7bdat")]
            logger.info(f"Scanning fixed path: {path} ({len(files)} candidate file(s))")
        else:
            if not auto_discover:
                raise ValueError(
                    "Either provide 'data_path' or set 'auto_discover=True' to enable searching."
                )
            files = self.find_sdtm_files(
                start_dir=search_from,
                extensions=extensions,
                recursive=recursive,
                max_depth=max_depth,
                include_hidden=include_hidden,
            )
            if not files:
                raise FileNotFoundError(
                    f"No SDTM files found via auto-discovery from '{Path(search_from).resolve()}'"
                )

        # Read files -> register valid domains
        for file in files:
            domain = self._detect_domain(file)
            if self.domain_whitelist and domain not in self.domain_whitelist:
                continue
            df = self.load_domain(str(file))
            if df is not None:
                if self.validate_domain(df, domain):
                    domains[domain] = df
                    logger.info(f"Registered domain: {domain.upper()} from {file.name}")
                else:
                    logger.warning(f"Validation failed: {domain.upper()} from {file.name}")

        logger.info(f"Loaded {len(domains)} domain(s): {list(domains.keys())}")
        return domains

    def validate_domain(self, df: pd.DataFrame, domain: str) -> bool:
        req = self.REQUIRED_VARS.get(domain)
        if req:
            missing = [v for v in req if v not in df.columns]
            if missing:
                logger.warning(f"Missing required variables in {domain}: {missing}")
                return False
        return True

    def get_domain_statistics(self, df: pd.DataFrame) -> Dict:
        stats = {
            'n_records': len(df),
            'n_subjects': df['USUBJID'].nunique() if 'USUBJID' in df.columns else None,
            'n_variables': len(df.columns),
            'missing_pct': (df.isna().sum().sum() / max(1, (len(df) * len(df.columns))) * 100),
        }
        return stats