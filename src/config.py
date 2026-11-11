from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SQL_DIR = BASE_DIR / "sql"

# Files
RAW_SALES_CSV = RAW_DATA_DIR / "sales_data.csv"
RAW_STORES_JSON = RAW_DATA_DIR / "stores.json"
DATABASE_PATH = PROCESSED_DATA_DIR / "retail_dw.db"
SCHEMA_SQL_PATH = SQL_DIR / "schema.sql"
QUERIES_SQL_PATH = SQL_DIR / "analytical_queries.sql"
