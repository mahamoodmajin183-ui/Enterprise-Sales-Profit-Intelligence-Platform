"""Independent SQL vs Python Analytical Validation Module.

Conducts rigorous mathematical reconciliation between independent Python calculations
and DuckDB analytical marts. Asserts zero tolerance for discrete counts (orders,
customers, line items) and strict float tolerances for monetary sums and margins.
Produces a machine-readable JSON validation report.
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

from src.config import QUALITY_REPORTS_DIR, SQL_PYTHON_RECONCILIATION_REPORT_FILE
from src.duckdb_manager import DuckDBWarehouse
from src.metrics_engine import MetricsEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Documented tolerances
TOLERANCE_MONETARY = 0.05       # Max acceptable difference in currency ($0.05)
TOLERANCE_PERCENT = 0.05        # Max acceptable percentage point difference (0.05%)
TOLERANCE_COUNT = 0             # Zero tolerance for discrete counts (orders, customers, units)


class SQLPythonValidator:
    """Independent validator comparing Python Engine against DuckDB Analytical Marts."""

    def __init__(self):
        self.engine = MetricsEngine()
        self.warehouse = DuckDBWarehouse()
        self.warehouse.initialize_warehouse()

    def validate_executive_kpis(self) -> Dict[str, Any]:
        """Compare Executive KPIs calculated by Python vs DuckDB fact/marts."""
        logger.info("Reconciling Executive KPIs...")
        py_kpi = self.engine.calculate_executive_kpis()
        sql_df = self.warehouse.query("""
            SELECT
                ROUND(SUM(sales), 2) AS total_revenue,
                ROUND(SUM(profit), 2) AS total_profit,
                COUNT(DISTINCT order_id) AS total_orders,
                COUNT(DISTINCT customer_id) AS total_customers,
                SUM(quantity) AS total_units,
                ROUND((SUM(profit) / SUM(sales)) * 100, 2) AS profit_margin_pct,
                ROUND(SUM(sales) / COUNT(DISTINCT order_id), 2) AS avg_order_value,
                ROUND(AVG(discount) * 100, 2) AS avg_discount_pct
            FROM fact_sales;
        """).iloc[0]

        checks = {
            "total_revenue": {
                "py": py_kpi["total_revenue"],
                "sql": float(sql_df["total_revenue"]),
                "delta": round(abs(py_kpi["total_revenue"] - float(sql_df["total_revenue"])), 4),
                "tolerance": TOLERANCE_MONETARY,
                "passed": bool(abs(py_kpi["total_revenue"] - float(sql_df["total_revenue"])) <= TOLERANCE_MONETARY),
            },
            "total_profit": {
                "py": py_kpi["total_profit"],
                "sql": float(sql_df["total_profit"]),
                "delta": round(abs(py_kpi["total_profit"] - float(sql_df["total_profit"])), 4),
                "tolerance": TOLERANCE_MONETARY,
                "passed": bool(abs(py_kpi["total_profit"] - float(sql_df["total_profit"])) <= TOLERANCE_MONETARY),
            },
            "total_orders": {
                "py": py_kpi["total_orders"],
                "sql": int(sql_df["total_orders"]),
                "delta": abs(py_kpi["total_orders"] - int(sql_df["total_orders"])),
                "tolerance": TOLERANCE_COUNT,
                "passed": bool(py_kpi["total_orders"] == int(sql_df["total_orders"])),
            },
            "total_customers": {
                "py": py_kpi["total_customers"],
                "sql": int(sql_df["total_customers"]),
                "delta": abs(py_kpi["total_customers"] - int(sql_df["total_customers"])),
                "tolerance": TOLERANCE_COUNT,
                "passed": bool(py_kpi["total_customers"] == int(sql_df["total_customers"])),
            },
            "total_units": {
                "py": py_kpi["total_units"],
                "sql": int(sql_df["total_units"]),
                "delta": abs(py_kpi["total_units"] - int(sql_df["total_units"])),
                "tolerance": TOLERANCE_COUNT,
                "passed": bool(py_kpi["total_units"] == int(sql_df["total_units"])),
            },
            "profit_margin_pct": {
                "py": py_kpi["profit_margin_pct"],
                "sql": float(sql_df["profit_margin_pct"]),
                "delta": round(abs(py_kpi["profit_margin_pct"] - float(sql_df["profit_margin_pct"])), 4),
                "tolerance": TOLERANCE_PERCENT,
                "passed": bool(abs(py_kpi["profit_margin_pct"] - float(sql_df["profit_margin_pct"])) <= TOLERANCE_PERCENT),
            },
            "avg_order_value": {
                "py": py_kpi["avg_order_value"],
                "sql": float(sql_df["avg_order_value"]),
                "delta": round(abs(py_kpi["avg_order_value"] - float(sql_df["avg_order_value"])), 4),
                "tolerance": TOLERANCE_MONETARY,
                "passed": bool(abs(py_kpi["avg_order_value"] - float(sql_df["avg_order_value"])) <= TOLERANCE_MONETARY),
            },
        }

        all_passed = all(item["passed"] for item in checks.values())
        return {"category": "Executive KPIs", "passed": all_passed, "checks": checks}

    def validate_category_mart(self) -> Dict[str, Any]:
        """Reconcile Category & Sub-Category aggregations."""
        logger.info("Reconciling Category Mart...")
        py_cat = self.engine.get_category_metrics()
        sql_cat = self.warehouse.query("""
            SELECT 
                category,
                sub_category,
                total_revenue,
                total_profit,
                total_orders
            FROM mart_category_performance
            ORDER BY category, sub_category;
        """)

        merged = pd.merge(
            py_cat,
            sql_cat,
            on=["category", "sub_category"],
            suffixes=("_py", "_sql"),
        )

        rev_mismatch = (merged["total_revenue_py"] - merged["total_revenue_sql"]).abs().max()
        prof_mismatch = (merged["total_profit_py"] - merged["total_profit_sql"]).abs().max()
        orders_mismatch = (merged["total_orders_py"] - merged["total_orders_sql"]).abs().max()

        passed = bool(
            rev_mismatch <= TOLERANCE_MONETARY
            and prof_mismatch <= TOLERANCE_MONETARY
            and orders_mismatch == 0
        )

        return {
            "category": "Category Mart",
            "passed": passed,
            "max_revenue_delta": round(float(rev_mismatch), 4),
            "max_profit_delta": round(float(prof_mismatch), 4),
            "max_orders_delta": int(orders_mismatch),
            "sub_categories_checked": len(merged),
        }

    def validate_monthly_mart(self) -> Dict[str, Any]:
        """Reconcile Monthly Performance Mart."""
        logger.info("Reconciling Monthly Performance Mart...")
        py_mon = self.engine.get_monthly_trends()
        sql_mon = self.warehouse.query("""
            SELECT 
                order_year,
                order_month,
                total_revenue,
                total_profit,
                total_orders
            FROM mart_monthly_performance
            ORDER BY order_year, order_month;
        """)

        merged = pd.merge(
            py_mon,
            sql_mon,
            on=["order_year", "order_month"],
            suffixes=("_py", "_sql"),
        )

        rev_mismatch = (merged["monthly_revenue"] - merged["total_revenue"]).abs().max()
        prof_mismatch = (merged["monthly_profit"] - merged["total_profit"]).abs().max()
        orders_mismatch = (merged["orders_count"] - merged["total_orders"]).abs().max()

        passed = bool(
            rev_mismatch <= TOLERANCE_MONETARY
            and prof_mismatch <= TOLERANCE_MONETARY
            and orders_mismatch == 0
        )

        return {
            "category": "Monthly Mart",
            "passed": passed,
            "max_revenue_delta": round(float(rev_mismatch), 4),
            "max_profit_delta": round(float(prof_mismatch), 4),
            "max_orders_delta": int(orders_mismatch),
            "months_checked": len(merged),
        }

    def validate_regional_mart(self) -> Dict[str, Any]:
        """Reconcile Regional Performance Mart."""
        logger.info("Reconciling Regional Mart...")
        py_reg = self.engine.get_regional_metrics()
        sql_reg = self.warehouse.query("""
            SELECT 
                region,
                state,
                total_revenue,
                total_profit,
                total_orders
            FROM mart_regional_performance
            ORDER BY region, state;
        """)

        merged = pd.merge(
            py_reg,
            sql_reg,
            on=["region", "state"],
            suffixes=("_py", "_sql"),
        )

        rev_mismatch = (merged["total_revenue_py"] - merged["total_revenue_sql"]).abs().max()
        prof_mismatch = (merged["total_profit_py"] - merged["total_profit_sql"]).abs().max()
        orders_mismatch = (merged["total_orders_py"] - merged["total_orders_sql"]).abs().max()

        passed = bool(
            rev_mismatch <= TOLERANCE_MONETARY
            and prof_mismatch <= TOLERANCE_MONETARY
            and orders_mismatch == 0
        )

        return {
            "category": "Regional Mart",
            "passed": passed,
            "max_revenue_delta": round(float(rev_mismatch), 4),
            "max_profit_delta": round(float(prof_mismatch), 4),
            "max_orders_delta": int(orders_mismatch),
            "states_checked": len(merged),
        }

    def run_full_validation(self) -> Dict[str, Any]:
        """Run all reconciliation audits and write out machine-readable validation summary."""
        kpi_audit = self.validate_executive_kpis()
        cat_audit = self.validate_category_mart()
        mon_audit = self.validate_monthly_mart()
        reg_audit = self.validate_regional_mart()

        overall_status = (
            kpi_audit["passed"]
            and cat_audit["passed"]
            and mon_audit["passed"]
            and reg_audit["passed"]
        )

        full_report = {
            "validation_status": "PASSED" if overall_status else "FAILED",
            "tolerances": {
                "monetary_tolerance_usd": TOLERANCE_MONETARY,
                "percentage_tolerance_pct": TOLERANCE_PERCENT,
                "count_tolerance": TOLERANCE_COUNT,
            },
            "audits": {
                "executive_kpis": kpi_audit,
                "category_mart": cat_audit,
                "monthly_mart": mon_audit,
                "regional_mart": reg_audit,
            },
        }

        QUALITY_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(SQL_PYTHON_RECONCILIATION_REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(full_report, f, indent=2)

        logger.info(f"Saved full validation report to {SQL_PYTHON_RECONCILIATION_REPORT_FILE}")

        if not overall_status:
            raise ValueError(
                f"SQL-Python reconciliation failed critical tolerances: {full_report}"
            )

        return full_report


if __name__ == "__main__":
    validator = SQLPythonValidator()
    report = validator.run_full_validation()
    print("=" * 60)
    print("SQL vs PYTHON INDEPENDENT RECONCILIATION REPORT:")
    print("=" * 60)
    print("Status:", report["validation_status"])
    for name, audit in report["audits"].items():
        print(f"- {audit['category']}: {'PASSED' if audit['passed'] else 'FAILED'}")
    print("=" * 60)
