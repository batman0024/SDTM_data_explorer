
import duckdb
import pandas as pd
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.tables = []
    def initialize(self, sdtm_data: Dict[str, pd.DataFrame]):
        self.conn = duckdb.connect(':memory:')
        for domain, df in sdtm_data.items():
            if df is not None:
                self.conn.register(domain, df)
                self.tables.append(domain)
                logger.info(f"Registered {domain} in DuckDB")
        self.create_views()
    def create_views(self):
        if 'ae' in self.tables and 'dm' in self.tables:
            try:
                self.conn.execute("""
                    CREATE VIEW ae_analysis AS
                    SELECT ae.*, dm.ARM, dm.ACTARM, dm.AGE, dm.SEX, dm.RFSTDTC
                    FROM ae LEFT JOIN dm ON ae.USUBJID = dm.USUBJID
                """)
                logger.info("Created ae_analysis view")
            except Exception as e:
                logger.warning(f"Could not create ae_analysis view: {str(e)}")
        if 'lb' in self.tables and 'dm' in self.tables:
            try:
                self.conn.execute("""
                    CREATE VIEW lb_analysis AS
                    SELECT lb.*, dm.ARM, dm.ACTARM, dm.RFSTDTC
                    FROM lb LEFT JOIN dm ON lb.USUBJID = dm.USUBJID
                """)
                logger.info("Created lb_analysis view")
            except Exception as e:
                logger.warning(f"Could not create lb_analysis view: {str(e)}")
    def execute_query(self, query: str) -> pd.DataFrame:
        try:
            return self.conn.execute(query).df()
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}"); raise
    def get_connection(self):
        return self.conn
