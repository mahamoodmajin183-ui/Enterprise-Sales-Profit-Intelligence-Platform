"""Automated Data Profiler for Enterprise Sales Platform.

Performs data profiling: inspects columns, missing values, duplicates,
ranges, cardinalities, and invalid data records.
Outputs report to data/quality_reports/profiling_metrics.json.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pandas as pd

from src.config import PROFILING_REPORT_FILE, QUALITY_REPORTS_DIR
from src.data_loader import load_raw_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def profile_raw_data(df: pd.DataFrame, dataset_name: str = "Raw Orders") -> Dict[str, Any]:
    """Run comprehensive diagnostic profiling on input DataFrame.

    Args:
        df: Input pandas DataFrame.
        dataset_name: Human-readable identifier.

    Returns:
        Dictionary containing profiling metrics.
    """
    logger.info(f"Profiling dataset: {dataset_name} ({len(df):,} rows, {len(df.columns)} columns)")

    # 1. Row counts & duplicate detection
    total_rows = int(len(df))
    duplicate_rows = int(df.duplicated().sum())

    # Check key-level duplicates if order_id / row_id exist
    row_id_col = [c for c in df.columns if "row" in c.lower() and "id" in c.lower()]
    order_id_col = [c for c in df.columns if "order" in c.lower() and "id" in c.lower()]

    row_id_duplicates = int(df[row_id_col[0]].duplicated().sum()) if row_id_col else 0
    unique_orders = int(df[order_id_col[0]].nunique()) if order_id_col else 0

    # 2. Missing values per column
    missing_summary = {}
    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        pct_missing = round((n_missing / total_rows) * 100, 3)
        missing_summary[col] = {
            "missing_count": n_missing,
            "missing_pct": pct_missing,
            "dtype": str(df[col].dtype),
        }

    # 3. Numeric column statistics
    numeric_summary = {}
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    for col in numeric_cols:
        series = df[col].dropna()
        numeric_summary[col] = {
            "min": float(round(series.min(), 4)),
            "max": float(round(series.max(), 4)),
            "mean": float(round(series.mean(), 4)),
            "median": float(round(series.median(), 4)),
            "std": float(round(series.std(), 4)) if len(series) > 1 else 0.0,
            "negative_count": int((series < 0).sum()),
            "zero_count": int((series == 0).sum()),
        }

    # 4. Date range analysis if date columns present
    date_summary = {}
    for col in df.columns:
        if "date" in col.lower():
            try:
                parsed_dates = pd.to_datetime(df[col], errors="coerce")
                valid_dates = parsed_dates.dropna()
                if not valid_dates.empty:
                    date_summary[col] = {
                        "min_date": str(valid_dates.min().strftime("%Y-%m-%d")),
                        "max_date": str(valid_dates.max().strftime("%Y-%m-%d")),
                        "unparseable_count": int(parsed_dates.isna().sum()),
                    }
            except Exception as e:
                date_summary[col] = {"error": str(e)}

    # 5. Categorical cardinality
    cardinality_summary = {}
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    for col in categorical_cols:
        cardinality_summary[col] = {
            "unique_values": int(df[col].nunique()),
            "top_value": str(df[col].mode().iloc[0]) if not df[col].empty else None,
        }

    profile_result = {
        "dataset_name": dataset_name,
        "total_rows": total_rows,
        "total_columns": len(df.columns),
        "columns": df.columns.tolist(),
        "duplicate_rows": duplicate_rows,
        "row_id_duplicates": row_id_duplicates,
        "unique_orders": unique_orders,
        "missing_summary": missing_summary,
        "numeric_summary": numeric_summary,
        "date_summary": date_summary,
        "cardinality_summary": cardinality_summary,
    }

    # Persist report to file
    QUALITY_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROFILING_REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(profile_result, f, indent=2)

    logger.info(f"Saved profiling metrics report to: {PROFILING_REPORT_FILE}")
    return profile_result


if __name__ == "__main__":
    orders, returns = load_raw_data()
    profile = profile_raw_data(orders, "Raw Orders")
    print(f"Total Rows: {profile['total_rows']:,}")
    print(f"Unique Orders: {profile['unique_orders']:,}")
    print("Numeric summary:")
    for k, v in profile["numeric_summary"].items():
        print(f"  {k}: min={v['min']}, max={v['max']}, mean={v['mean']}")
