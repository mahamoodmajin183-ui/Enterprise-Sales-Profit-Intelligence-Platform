"""Unit tests for Python vs DuckDB end-to-end data reconciliation."""

import pytest
from src.duckdb_manager import DuckDBWarehouse
from src.metrics_engine import MetricsEngine


def test_python_duckdb_reconciliation():
    """Verify that Python MetricsEngine and DuckDB warehouse match exactly."""
    warehouse = DuckDBWarehouse()
    warehouse.initialize_warehouse()

    engine = MetricsEngine()
    reconciliation = engine.reconcile_with_duckdb()

    assert reconciliation["reconciled"] is True, f"Reconciliation failed: {reconciliation['deltas']}"
    assert reconciliation["deltas"]["revenue_delta"] < 0.01
    assert reconciliation["deltas"]["profit_delta"] < 0.01
    assert reconciliation["deltas"]["orders_delta"] == 0


def test_category_mart_reconciliation():
    """Verify category totals in DuckDB mart match Python calculations."""
    warehouse = DuckDBWarehouse()
    db_cat = warehouse.query("""
        SELECT 
            category,
            ROUND(SUM(total_revenue), 2) AS cat_revenue,
            ROUND(SUM(total_profit), 2) AS cat_profit
        FROM mart_category_performance
        GROUP BY category
        ORDER BY category;
    """)

    engine = MetricsEngine()
    py_cat = engine.get_category_metrics()
    py_cat_grouped = (
        py_cat.groupby("category")[["total_revenue", "total_profit"]]
        .sum()
        .round(2)
        .reset_index()
        .sort_values("category")
    )

    for _, row in db_cat.iterrows():
        cat = row["category"]
        py_row = py_cat_grouped[py_cat_grouped["category"] == cat].iloc[0]
        assert abs(row["cat_revenue"] - py_row["total_revenue"]) < 0.01
        assert abs(row["cat_profit"] - py_row["total_profit"]) < 0.01


def test_customer_mart_reconciliation():
    """Verify customer totals in DuckDB customer mart match fact table totals."""
    warehouse = DuckDBWarehouse()
    totals = warehouse.query("""
        SELECT 
            ROUND(SUM(total_revenue), 2) AS cust_rev,
            ROUND(SUM(total_profit), 2) AS cust_prof,
            COUNT(DISTINCT customer_id) AS cust_count
        FROM mart_customer_performance;
    """).iloc[0]

    fact_totals = warehouse.query("""
        SELECT 
            ROUND(SUM(sales), 2) AS fact_rev,
            ROUND(SUM(profit), 2) AS fact_prof,
            COUNT(DISTINCT customer_id) AS fact_cust_count
        FROM fact_sales;
    """).iloc[0]

    assert abs(totals["cust_rev"] - fact_totals["fact_rev"]) < 0.01
    assert abs(totals["cust_prof"] - fact_totals["fact_prof"]) < 0.01
    assert totals["cust_count"] == fact_totals["fact_cust_count"]


def test_regional_mart_reconciliation():
    """Verify regional mart totals in DuckDB match fact table totals."""
    warehouse = DuckDBWarehouse()
    reg_totals = warehouse.query("""
        SELECT 
            ROUND(SUM(total_revenue), 2) AS reg_rev,
            ROUND(SUM(total_profit), 2) AS reg_prof
        FROM mart_regional_performance;
    """).iloc[0]

    fact_totals = warehouse.query("""
        SELECT 
            ROUND(SUM(sales), 2) AS fact_rev,
            ROUND(SUM(profit), 2) AS fact_prof
        FROM fact_sales;
    """).iloc[0]

    assert abs(reg_totals["reg_rev"] - fact_totals["fact_rev"]) < 0.01
    assert abs(reg_totals["reg_prof"] - fact_totals["fact_prof"]) < 0.01
