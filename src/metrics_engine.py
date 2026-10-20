"""Deterministic Metrics Calculation Engine.

Calculates enterprise KPIs, time-series aggregations, dimensional metrics,
and validates mathematical reconciliation between Python and DuckDB.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import PROCESSED_PARQUET_FILE
from src.duckdb_manager import DuckDBWarehouse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division guarding against division by zero, nulls, and infinities."""
    if denominator is None or pd.isna(denominator) or denominator == 0:
        return default
    try:
        val = numerator / denominator
        if np.isinf(val) or np.isnan(val):
            return default
        return float(val)
    except ZeroDivisionError:
        return default


class MetricsEngine:
    """Calculates deterministic enterprise retail metrics from clean dataset."""

    def __init__(self, data: Optional[pd.DataFrame] = None):
        if data is not None:
            self.df = data.copy()
        elif PROCESSED_PARQUET_FILE.exists():
            self.df = pd.read_parquet(PROCESSED_PARQUET_FILE)
        else:
            raise FileNotFoundError(f"Processed dataset not found at {PROCESSED_PARQUET_FILE}")

    def calculate_executive_kpis(self, df_subset: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Compute top-level business health metrics."""
        df = df_subset if df_subset is not None else self.df

        if df.empty:
            return {
                "total_revenue": 0.0,
                "total_profit": 0.0,
                "total_orders": 0,
                "total_customers": 0,
                "total_units": 0,
                "profit_margin_pct": 0.0,
                "avg_order_value": 0.0,
                "avg_profit_per_order": 0.0,
                "avg_discount_pct": 0.0,
                "return_rate_pct": 0.0,
            }

        total_rev = float(round(df["sales"].sum(), 2))
        total_prof = float(round(df["profit"].sum(), 2))
        total_orders = int(df["order_id"].nunique())
        total_cust = int(df["customer_id"].nunique())
        total_units = int(df["quantity"].sum())

        margin_pct = round(safe_divide(total_prof, total_rev) * 100, 2)
        aov = round(safe_divide(total_rev, total_orders), 2)
        prof_per_order = round(safe_divide(total_prof, total_orders), 2)
        avg_disc = round(float(df["discount"].mean()) * 100, 2)

        returned_orders = int(df[df["is_returned"]]["order_id"].nunique())
        return_rate = round(safe_divide(returned_orders, total_orders) * 100, 2)

        return {
            "total_revenue": total_rev,
            "total_profit": total_prof,
            "total_orders": total_orders,
            "total_customers": total_cust,
            "total_units": total_units,
            "profit_margin_pct": margin_pct,
            "avg_order_value": aov,
            "avg_profit_per_order": prof_per_order,
            "avg_discount_pct": avg_disc,
            "return_rate_pct": return_rate,
        }

    def get_monthly_trends(self, df_subset: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Calculate monthly revenue, profit, margins, and YoY growth."""
        df = df_subset if df_subset is not None else self.df
        if df.empty:
            return pd.DataFrame()

        monthly = (
            df.groupby(["order_year", "order_month", "order_year_month"])
            .agg(
                orders_count=("order_id", "nunique"),
                units_sold=("quantity", "sum"),
                monthly_revenue=("sales", "sum"),
                monthly_profit=("profit", "sum"),
                avg_discount=("discount", "mean"),
            )
            .reset_index()
        )
        monthly["monthly_revenue"] = monthly["monthly_revenue"].round(2)
        monthly["monthly_profit"] = monthly["monthly_profit"].round(2)
        monthly["profit_margin_pct"] = monthly.apply(
            lambda r: round(safe_divide(r["monthly_profit"], r["monthly_revenue"]) * 100, 2), axis=1
        )
        monthly = monthly.sort_values(["order_year", "order_month"]).reset_index(drop=True)

        # YoY Growth
        monthly["py_revenue"] = monthly["monthly_revenue"].shift(12)
        monthly["yoy_growth_pct"] = monthly.apply(
            lambda r: round(safe_divide(r["monthly_revenue"] - r["py_revenue"], r["py_revenue"]) * 100, 2)
            if pd.notna(r["py_revenue"]) and r["py_revenue"] > 0
            else None,
            axis=1,
        )
        return monthly

    def get_category_metrics(self, df_subset: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Calculate performance across category and sub-category."""
        df = df_subset if df_subset is not None else self.df
        if df.empty:
            return pd.DataFrame()

        cat = (
            df.groupby(["category", "sub_category"])
            .agg(
                total_orders=("order_id", "nunique"),
                units_sold=("quantity", "sum"),
                total_revenue=("sales", "sum"),
                total_profit=("profit", "sum"),
                avg_discount=("discount", "mean"),
                unprofitable_items=("profit", lambda s: int((s < 0).sum())),
                total_loss_dollars=("profit", lambda s: round(float(s[s < 0].sum()), 2)),
                total_items=("row_id", "count"),
            )
            .reset_index()
        )
        cat["total_revenue"] = cat["total_revenue"].round(2)
        cat["total_profit"] = cat["total_profit"].round(2)
        cat["profit_margin_pct"] = cat.apply(
            lambda r: round(safe_divide(r["total_profit"], r["total_revenue"]) * 100, 2), axis=1
        )
        cat["avg_discount_pct"] = (cat["avg_discount"] * 100).round(2)
        cat["unprofitable_item_pct"] = cat.apply(
            lambda r: round(safe_divide(r["unprofitable_items"], r["total_items"]) * 100, 2), axis=1
        )
        return cat.sort_values("total_profit", ascending=False).reset_index(drop=True)

    def get_regional_metrics(self, df_subset: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Calculate state and regional performance metrics."""
        df = df_subset if df_subset is not None else self.df
        if df.empty:
            return pd.DataFrame()

        reg = (
            df.groupby(["region", "state"])
            .agg(
                total_orders=("order_id", "nunique"),
                unique_customers=("customer_id", "nunique"),
                units_sold=("quantity", "sum"),
                total_revenue=("sales", "sum"),
                total_profit=("profit", "sum"),
                avg_discount=("discount", "mean"),
                returned_orders=("order_id", lambda s: int(df.loc[s.index, "is_returned"].sum())),
            )
            .reset_index()
        )
        reg["total_revenue"] = reg["total_revenue"].round(2)
        reg["total_profit"] = reg["total_profit"].round(2)
        reg["profit_margin_pct"] = reg.apply(
            lambda r: round(safe_divide(r["total_profit"], r["total_revenue"]) * 100, 2), axis=1
        )
        reg["avg_discount_pct"] = (reg["avg_discount"] * 100).round(2)
        reg["return_rate_pct"] = reg.apply(
            lambda r: round(safe_divide(r["returned_orders"], r["total_orders"]) * 100, 2), axis=1
        )
        return reg.sort_values("total_profit", ascending=False).reset_index(drop=True)

    def get_discount_metrics(self, df_subset: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Analyze margin erosion by discount tier."""
        df = df_subset if df_subset is not None else self.df
        if df.empty:
            return pd.DataFrame()

        disc = (
            df.groupby("discount_bracket")
            .agg(
                total_transactions=("row_id", "count"),
                total_orders=("order_id", "nunique"),
                avg_discount=("discount", "mean"),
                total_sales=("sales", "sum"),
                total_profit=("profit", "sum"),
                unprofitable_items=("profit", lambda s: int((s < 0).sum())),
                total_loss_dollars=("profit", lambda s: round(float(s[s < 0].sum()), 2)),
            )
            .reset_index()
        )
        disc["total_sales"] = disc["total_sales"].round(2)
        disc["total_profit"] = disc["total_profit"].round(2)
        disc["avg_discount_pct"] = (disc["avg_discount"] * 100).round(2)
        disc["profit_margin_pct"] = disc.apply(
            lambda r: round(safe_divide(r["total_profit"], r["total_sales"]) * 100, 2), axis=1
        )
        disc["unprofitable_item_pct"] = disc.apply(
            lambda r: round(safe_divide(r["unprofitable_items"], r["total_transactions"]) * 100, 2), axis=1
        )
        return disc.sort_values("avg_discount_pct").reset_index(drop=True)

    def reconcile_with_duckdb(self) -> Dict[str, Any]:
        """Perform reconciliation check between Python engine and DuckDB warehouse."""
        py_kpis = self.calculate_executive_kpis()

        warehouse = DuckDBWarehouse()
        db_df = warehouse.query("""
            SELECT 
                ROUND(SUM(sales), 2) AS total_revenue,
                ROUND(SUM(profit), 2) AS total_profit,
                COUNT(DISTINCT order_id) AS total_orders,
                COUNT(DISTINCT customer_id) AS total_customers,
                SUM(quantity) AS total_units
            FROM fact_sales;
        """)

        db_rev = float(db_df["total_revenue"].iloc[0])
        db_prof = float(db_df["total_profit"].iloc[0])
        db_orders = int(db_df["total_orders"].iloc[0])
        db_cust = int(db_df["total_customers"].iloc[0])
        db_units = int(db_df["total_units"].iloc[0])

        rev_diff = abs(py_kpis["total_revenue"] - db_rev)
        prof_diff = abs(py_kpis["total_profit"] - db_prof)
        orders_diff = abs(py_kpis["total_orders"] - db_orders)

        is_reconciled = (rev_diff < 0.01) and (prof_diff < 0.01) and (orders_diff == 0)

        return {
            "reconciled": is_reconciled,
            "python": py_kpis,
            "duckdb": {
                "total_revenue": db_rev,
                "total_profit": db_prof,
                "total_orders": db_orders,
                "total_customers": db_cust,
                "total_units": db_units,
            },
            "deltas": {
                "revenue_delta": rev_diff,
                "profit_delta": prof_diff,
                "orders_delta": orders_diff,
            },
        }


if __name__ == "__main__":
    engine = MetricsEngine()
    reconciliation = engine.reconcile_with_duckdb()
    print("Reconciliation Audit Result:", "SUCCESS" if reconciliation["reconciled"] else "FAILED")
    print(f"Revenue Delta: ${reconciliation['deltas']['revenue_delta']:.4f}")
    print(f"Profit Delta:  ${reconciliation['deltas']['profit_delta']:.4f}")
    print(f"Orders Delta:  {reconciliation['deltas']['orders_delta']}")
