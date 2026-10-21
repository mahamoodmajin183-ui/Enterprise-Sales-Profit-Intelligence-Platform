"""Data Cleaning and Transformation Pipeline.

Applies documented enterprise cleaning rules, deduplication, date normalization,
derived analytical feature engineering, and validation checks.
Saves processed Parquet & CSV files and writes validation_summary.json.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pandas as pd

from src.config import (
    PROCESSED_CSV_FILE,
    PROCESSED_PARQUET_FILE,
    QUALITY_REPORTS_DIR,
    VALIDATION_REPORT_FILE,
)
from src.data_loader import load_raw_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert column headers to standardized snake_case."""
    col_mapping = {
        "Row ID": "row_id",
        "Order ID": "order_id",
        "Order Date": "order_date",
        "Ship Date": "ship_date",
        "Ship Mode": "ship_mode",
        "Customer ID": "customer_id",
        "Customer Name": "customer_name",
        "Segment": "segment",
        "Country": "country",
        "City": "city",
        "State": "state",
        "Postal Code": "postal_code",
        "Region": "region",
        "Product ID": "product_id",
        "Category": "category",
        "Sub-Category": "sub_category",
        "Product Name": "product_name",
        "Sales": "sales",
        "Quantity": "quantity",
        "Discount": "discount",
        "Profit": "profit",
    }
    df = df.rename(columns=col_mapping)
    # Lowercase and clean any remaining column names
    df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    return df


def assign_discount_bracket(discount: float) -> str:
    """Classify discount rates into analytical tiers."""
    if discount == 0.0:
        return "0% (None)"
    elif discount <= 0.10:
        return "1% - 10% (Low)"
    elif discount <= 0.20:
        return "11% - 20% (Moderate)"
    elif discount <= 0.40:
        return "21% - 40% (High)"
    else:
        return "> 40% (Deep Discount)"


def clean_and_transform(
    df_orders: pd.DataFrame, df_returns: pd.DataFrame, save: bool = False
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Clean raw orders, join returns, calculate metrics, and validate integrity.

    Args:
        df_orders: Raw orders DataFrame.
        df_returns: Raw returns lookup DataFrame.

    Returns:
        Tuple of (cleaned_df, validation_summary_dict).
    """
    from src.config import (
        PROCESSED_CSV_FILE,
        PROCESSED_PARQUET_FILE,
        QUALITY_REPORTS_DIR,
        REJECTED_RECORDS_FILE,
        REQUIRED_COLUMNS,
        VALIDATION_REPORT_FILE,
    )

    logger.info("Starting data cleaning and transformation pipeline...")
    initial_row_count = len(df_orders)

    # Handle empty dataset cleanly
    if df_orders.empty:
        logger.warning("Received empty orders dataframe. Returning empty processed dataframe.")
        empty_clean = pd.DataFrame(columns=REQUIRED_COLUMNS + [
            "order_year", "order_month", "order_year_month", "order_quarter",
            "order_day_name", "shipping_days", "unit_price", "estimated_cost",
            "profit_margin", "is_profitable", "discount_bracket", "is_returned",
            "order_date_str", "ship_date_str"
        ])
        empty_summary = {
            "status": "PASSED_EMPTY",
            "initial_raw_rows": 0,
            "final_cleaned_rows": 0,
            "dropped_rows": 0,
            "rejected_rows": 0,
            "reconciliation_check": True,
            "unique_orders": 0,
            "unique_customers": 0,
            "unique_products": 0,
            "min_order_date": None,
            "max_order_date": None,
            "total_revenue": 0.0,
            "total_profit": 0.0,
            "overall_profit_margin_pct": 0.0,
            "unprofitable_rows_count": 0,
            "unprofitable_rows_pct": 0.0,
            "total_loss_amount": 0.0,
            "returned_orders_count": 0,
            "return_rate_pct": 0.0,
            "validation_checks": {
                "no_duplicate_rows": True,
                "no_negative_sales": True,
                "no_zero_or_negative_quantity": True,
                "valid_discount_range": True,
                "valid_shipping_dates": True,
                "safe_profit_margin_guard": True,
            },
        }
        return empty_clean, empty_summary

    # 1. Standardize column names
    df = standardize_columns(df_orders.copy())

    # Schema validation against REQUIRED_COLUMNS
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        logger.error(f"Missing required schema columns: {missing_cols}")
        raise ValueError(f"Schema validation failed. Required columns missing: {missing_cols}")

    # Track rejected records systematically
    rejected_rows_list = []

    # 2. Deduplication check
    exact_dup_mask = df.duplicated(keep="first")
    exact_duplicates = int(exact_dup_mask.sum())
    if exact_duplicates > 0:
        logger.warning(f"Found {exact_duplicates} exact duplicate rows. Recording for rejection.")
        for idx, row in df[exact_dup_mask].iterrows():
            rej = row.to_dict()
            rej["rejection_reason"] = "EXACT_DUPLICATE_ROW"
            rejected_rows_list.append(rej)
        df = df[~exact_dup_mask].copy()

    # 3. String sanitation: strip whitespace & non-printable characters
    str_cols = df.select_dtypes(include=["object", "string"]).columns
    for c in str_cols:
        df[c] = df[c].astype(str).str.strip()

    # 4. Standardize Postal Code (handle float representation and zero padding)
    if "postal_code" in df.columns:
        df["postal_code"] = (
            df["postal_code"]
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(5)
        )

    # 5. Robust Date Parsing
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["ship_date"] = pd.to_datetime(df["ship_date"], errors="coerce")

    invalid_date_mask = df["order_date"].isna() | df["ship_date"].isna()
    invalid_dates_count = int(invalid_date_mask.sum())
    if invalid_dates_count > 0:
        logger.warning(f"Found {invalid_dates_count} rows with unparseable dates. Recording for rejection.")
        for idx, row in df[invalid_date_mask].iterrows():
            rej = row.to_dict()
            rej["rejection_reason"] = "INVALID_UNPARSEABLE_DATE"
            rejected_rows_list.append(rej)
        df = df[~invalid_date_mask].copy()

    # Shipping order logic check: ship_date must be on or after order_date
    invalid_ship_order = int((df["ship_date"] < df["order_date"]).sum())
    if invalid_ship_order > 0:
        logger.warning(f"Found {invalid_ship_order} records where ship_date preceded order_date. Adjusting to order_date.")
        df.loc[df["ship_date"] < df["order_date"], "ship_date"] = df["order_date"]

    # 6. Numeric bounds validation
    # Sales must be non-negative; Quantity must be >= 1; Discount between 0 and 1
    invalid_sales_mask = df["sales"] < 0
    invalid_qty_mask = df["quantity"] < 1
    invalid_disc_mask = (df["discount"] < 0) | (df["discount"] > 1.0)
    numeric_violations = invalid_sales_mask | invalid_qty_mask | invalid_disc_mask

    invalid_sales = int(invalid_sales_mask.sum())
    invalid_quantity = int(invalid_qty_mask.sum())
    invalid_discount = int(invalid_disc_mask.sum())

    if numeric_violations.any():
        logger.warning(
            f"Invalid records: {invalid_sales} negative sales, {invalid_quantity} zero/negative qty, "
            f"{invalid_discount} invalid discount. Recording for rejection."
        )
        for idx, row in df[numeric_violations].iterrows():
            rej = row.to_dict()
            reasons = []
            if row["sales"] < 0:
                reasons.append("NEGATIVE_SALES")
            if row["quantity"] < 1:
                reasons.append("INVALID_QUANTITY")
            if row["discount"] < 0 or row["discount"] > 1.0:
                reasons.append("INVALID_DISCOUNT_OUT_OF_BOUNDS")
            rej["rejection_reason"] = ";".join(reasons)
            rejected_rows_list.append(rej)
        df = df[~numeric_violations].copy()

    # 7. Derived Analytical Feature Engineering
    # Date dimensions
    df["order_year"] = df["order_date"].dt.year
    df["order_month"] = df["order_date"].dt.month
    df["order_year_month"] = df["order_date"].dt.strftime("%Y-%m")
    df["order_quarter"] = "Q" + df["order_date"].dt.quarter.astype(str)
    df["order_day_name"] = df["order_date"].dt.day_name()
    df["shipping_days"] = (df["ship_date"] - df["order_date"]).dt.days

    # Pricing & Margin dimensions
    df["sales"] = df["sales"].round(2)
    df["profit"] = df["profit"].round(2)
    df["unit_price"] = (df["sales"] / df["quantity"]).round(2)
    df["estimated_cost"] = (df["sales"] - df["profit"]).round(2)

    # Safe Profit Margin calculation (zero denominator handling)
    df["profit_margin"] = np.where(
        df["sales"] > 0,
        (df["profit"] / df["sales"]).round(4),
        0.0
    )
    df["is_profitable"] = df["profit"] > 0

    # Discount categorization
    df["discount_bracket"] = df["discount"].apply(assign_discount_bracket)

    # 8. Join Returns status
    if not df_returns.empty:
        # Standardize returns headers
        ret = df_returns.copy()
        ret.columns = [c.strip().lower().replace(" ", "_") for c in ret.columns]
        order_col = [c for c in ret.columns if "order" in c and "id" in c]
        if order_col:
            returned_order_ids = set(ret[order_col[0]].astype(str).str.strip())
            df["is_returned"] = df["order_id"].isin(returned_order_ids)
        else:
            df["is_returned"] = False
    else:
        df["is_returned"] = False

    # Format dates as ISO string for Parquet / SQL interoperability
    df["order_date_str"] = df["order_date"].dt.strftime("%Y-%m-%d")
    df["ship_date_str"] = df["ship_date"].dt.strftime("%Y-%m-%d")

    # 9. Quality & Integrity Summary
    final_row_count = len(df)
    rejected_count = len(rejected_rows_list)
    total_revenue = float(round(df["sales"].sum(), 2)) if not df.empty else 0.0
    total_profit = float(round(df["profit"].sum(), 2)) if not df.empty else 0.0
    overall_margin = round((total_profit / total_revenue) * 100, 2) if total_revenue > 0 else 0.0
    total_loss_orders = int((df["profit"] < 0).sum()) if not df.empty else 0
    loss_amount = float(round(df[df["profit"] < 0]["profit"].sum(), 2)) if not df.empty else 0.0
    return_orders_count = int(df["order_id"][df["is_returned"]].nunique()) if not df.empty else 0
    total_orders_count = int(df["order_id"].nunique()) if not df.empty else 0
    return_rate_pct = round((return_orders_count / total_orders_count) * 100, 2) if total_orders_count > 0 else 0.0

    min_date_str = str(df["order_date"].min().strftime("%Y-%m-%d")) if not df.empty and pd.notna(df["order_date"].min()) else None
    max_date_str = str(df["order_date"].max().strftime("%Y-%m-%d")) if not df.empty and pd.notna(df["order_date"].max()) else None

    validation_summary = {
        "status": "PASSED",
        "initial_raw_rows": initial_row_count,
        "final_cleaned_rows": final_row_count,
        "rejected_rows": rejected_count,
        "reconciliation_check": bool(initial_row_count == (final_row_count + rejected_count)),
        "unique_orders": total_orders_count,
        "unique_customers": int(df["customer_id"].nunique()) if not df.empty else 0,
        "unique_products": int(df["product_id"].nunique()) if not df.empty else 0,
        "min_order_date": min_date_str,
        "max_order_date": max_date_str,
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "overall_profit_margin_pct": overall_margin,
        "unprofitable_rows_count": total_loss_orders,
        "unprofitable_rows_pct": round((total_loss_orders / final_row_count) * 100, 2) if final_row_count > 0 else 0.0,
        "total_loss_amount": loss_amount,
        "returned_orders_count": return_orders_count,
        "return_rate_pct": return_rate_pct,
        "validation_checks": {
            "no_duplicate_rows": bool(exact_duplicates == 0),
            "no_negative_sales": bool(invalid_sales == 0),
            "no_zero_or_negative_quantity": bool(invalid_quantity == 0),
            "valid_discount_range": bool(invalid_discount == 0),
            "valid_shipping_dates": bool(invalid_ship_order == 0),
            "safe_profit_margin_guard": True,
        },
    }

    # 10. Persist processed files & rejected records
    if save:
        PROCESSED_PARQUET_FILE.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(PROCESSED_PARQUET_FILE, index=False, engine="pyarrow")
        df.to_csv(PROCESSED_CSV_FILE, index=False)
        logger.info(f"Saved cleaned parquet to {PROCESSED_PARQUET_FILE} and CSV to {PROCESSED_CSV_FILE}")

        # Persist rejected records
        QUALITY_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        if rejected_rows_list:
            rejected_df = pd.DataFrame(rejected_rows_list)
            rejected_df.to_csv(REJECTED_RECORDS_FILE, index=False)
            logger.warning(f"Saved {len(rejected_df)} rejected records with reasons to {REJECTED_RECORDS_FILE}")
        else:
            # Create empty rejected records file with standard columns
            empty_rej = pd.DataFrame(columns=list(df.columns) + ["rejection_reason"])
            empty_rej.to_csv(REJECTED_RECORDS_FILE, index=False)
            logger.info(f"No records rejected. Wrote blank schema to {REJECTED_RECORDS_FILE}")

        # Persist validation report
        with open(VALIDATION_REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(validation_summary, f, indent=2)
        logger.info(f"Saved validation summary to {VALIDATION_REPORT_FILE}")

    return df, validation_summary


def run_pipeline() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Execute complete data extraction, cleaning, and validation pipeline."""
    orders_raw, returns_raw = load_raw_data()
    return clean_and_transform(orders_raw, returns_raw, save=True)


if __name__ == "__main__":
    cleaned_df, summary = run_pipeline()
    print("=" * 60)
    print("DATA PIPELINE VALIDATION SUMMARY:")
    print("=" * 60)
    for k, v in summary.items():
        if k != "validation_checks":
            print(f"{k}: {v}")
        else:
            print("Validation Checks:")
            for check, status in v.items():
                print(f"  - {check}: {status}")
    print("=" * 60)
