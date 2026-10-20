"""Configuration module for Enterprise Sales & Profit Intelligence Platform.

Defines project directory paths, data schemas, validation rules,
and analytical thresholds.
"""

import sys
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
QUALITY_REPORTS_DIR = DATA_DIR / "quality_reports"
DATABASE_DIR = BASE_DIR / "database"
SQL_DIR = BASE_DIR / "sql"
DOCS_DIR = BASE_DIR / "docs"

# Specific File Paths
RAW_ORDERS_FILE = RAW_DATA_DIR / "superstore_orders.csv"
RAW_RETURNS_FILE = RAW_DATA_DIR / "superstore_returns.csv"
PROCESSED_PARQUET_FILE = PROCESSED_DATA_DIR / "retail_sales_clean.parquet"
PROCESSED_CSV_FILE = PROCESSED_DATA_DIR / "retail_sales_clean.csv"
DUCKDB_DATABASE_FILE = DATABASE_DIR / "sales_warehouse.duckdb"

PROFILING_REPORT_FILE = QUALITY_REPORTS_DIR / "profiling_metrics.json"
VALIDATION_REPORT_FILE = QUALITY_REPORTS_DIR / "validation_summary.json"
REJECTED_RECORDS_FILE = QUALITY_REPORTS_DIR / "rejected_records.csv"

# Ensure all directories exist
for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, QUALITY_REPORTS_DIR, DATABASE_DIR, SQL_DIR, DOCS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Required Schema for Clean Ingestion
REQUIRED_COLUMNS = [
    "row_id",
    "order_id",
    "order_date",
    "ship_date",
    "ship_mode",
    "customer_id",
    "customer_name",
    "segment",
    "country",
    "city",
    "state",
    "postal_code",
    "region",
    "product_id",
    "category",
    "sub_category",
    "product_name",
    "sales",
    "quantity",
    "discount",
    "profit",
]

# Analytical Thresholds
MIN_DATE = "2015-01-01"
MAX_DATE = "2030-12-31"
HIGH_DISCOUNT_THRESHOLD = 0.40  # 40% discount or higher
HIGH_LOSS_THRESHOLD = -500.0    # Losses exceeding $500
ANOMALY_ZSCORE_THRESHOLD = 3.0  # 3 standard deviations for volume/sales
