"""Unit tests for deterministic metric calculations and zero division safety."""

import pytest
import pandas as pd
import numpy as np
from src.metrics_engine import MetricsEngine, safe_divide


def test_safe_divide():
    """Verify safe_divide prevents zero division and handles edge values."""
    assert safe_divide(100, 2) == 50.0
    assert safe_divide(100, 0) == 0.0
    assert safe_divide(100, None) == 0.0
    assert safe_divide(100, np.nan) == 0.0
    assert safe_divide(0, 50) == 0.0
    assert safe_divide(-100, 2) == -50.0


def test_kpi_calculations_with_zero_revenue():
    """Verify KPIs when revenue is 0.0."""
    zero_rev_df = pd.DataFrame({
        "order_id": ["ORD-1"],
        "customer_id": ["CUST-1"],
        "sales": [0.0],
        "profit": [0.0],
        "quantity": [1],
        "discount": [0.0],
        "is_returned": [False]
    })
    engine = MetricsEngine(data=zero_rev_df)
    kpis = engine.calculate_executive_kpis()

    assert kpis["total_revenue"] == 0.0
    assert kpis["profit_margin_pct"] == 0.0
    assert kpis["total_orders"] == 1


def test_metrics_engine_aggregations():
    """Verify category and regional calculations with valid mock data."""
    mock_df = pd.DataFrame({
        "row_id": [1, 2, 3],
        "order_id": ["O-1", "O-2", "O-3"],
        "order_year": [2023, 2023, 2023],
        "order_month": [1, 2, 3],
        "order_year_month": ["2023-01", "2023-02", "2023-03"],
        "customer_id": ["C-1", "C-2", "C-3"],
        "category": ["Technology", "Technology", "Furniture"],
        "sub_category": ["Phones", "Accessories", "Chairs"],
        "region": ["West", "East", "West"],
        "state": ["California", "New York", "California"],
        "sales": [500.0, 300.0, 200.0],
        "quantity": [2, 3, 1],
        "discount": [0.1, 0.0, 0.2],
        "profit": [100.0, 60.0, -40.0],
        "is_returned": [False, False, True],
        "discount_bracket": ["1% - 10% (Low)", "0% (None)", "11% - 20% (Moderate)"]
    })

    engine = MetricsEngine(data=mock_df)
    kpis = engine.calculate_executive_kpis()

    assert kpis["total_revenue"] == 1000.0
    assert kpis["total_profit"] == 120.0
    assert kpis["profit_margin_pct"] == 12.0
    assert kpis["total_orders"] == 3
    assert kpis["return_rate_pct"] == 33.33

    cat_df = engine.get_category_metrics()
    tech_row = cat_df[cat_df["category"] == "Technology"]
    assert len(tech_row) == 2
    assert tech_row["total_revenue"].sum() == 800.0


def test_customer_metrics_deciles():
    """Verify customer metrics grouping, lifetime profit margin, and decile assignment."""
    mock_df = pd.DataFrame({
        "customer_id": ["C1", "C1", "C2", "C3"],
        "customer_name": ["Alice", "Alice", "Bob", "Charlie"],
        "segment": ["Consumer", "Consumer", "Corporate", "Home Office"],
        "order_id": ["O1", "O2", "O3", "O4"],
        "quantity": [2, 3, 1, 4],
        "sales": [200.0, 300.0, 150.0, 400.0],
        "profit": [40.0, 60.0, -15.0, 100.0],
        "discount": [0.0, 0.1, 0.2, 0.0],
    })
    engine = MetricsEngine(data=mock_df)
    cust_df = engine.get_customer_metrics()

    assert len(cust_df) == 3
    alice = cust_df[cust_df["customer_id"] == "C1"].iloc[0]
    assert alice["total_orders"] == 2
    assert alice["lifetime_revenue_usd"] == 500.0
    assert alice["lifetime_profit_usd"] == 100.0
    assert alice["lifetime_margin_pct"] == 20.0


def test_multi_line_order_aggregation_no_double_counting():
    """Ensure multi-item baskets count total_orders accurately as distinct orders."""
    multi_line_df = pd.DataFrame({
        "order_id": ["ORD-100", "ORD-100", "ORD-100", "ORD-101"],
        "customer_id": ["C-1", "C-1", "C-1", "C-2"],
        "sales": [100.0, 200.0, 300.0, 150.0],
        "profit": [20.0, 40.0, 60.0, 30.0],
        "quantity": [1, 2, 3, 1],
        "discount": [0.0, 0.0, 0.0, 0.0],
        "is_returned": [False, False, False, False],
    })
    engine = MetricsEngine(data=multi_line_df)
    kpis = engine.calculate_executive_kpis()

    assert kpis["total_orders"] == 2  # Not 4
    assert kpis["total_revenue"] == 750.0
    assert kpis["avg_order_value"] == 375.0  # 750 / 2, not 750 / 4


def test_top_bottom_product_cohorts():
    """Verify top/bottom product extraction and revenue trap detection."""
    prod_df = pd.DataFrame({
        "product_id": ["P1", "P2", "P3"],
        "product_name": ["Printer Pro", "Cheap Paper", "Expensive Machine"],
        "category": ["Technology", "Office Supplies", "Technology"],
        "sub_category": ["Machines", "Paper", "Machines"],
        "order_id": ["O1", "O2", "O3"],
        "quantity": [2, 10, 1],
        "sales": [6000.0, 100.0, 8000.0],
        "profit": [60.0, 40.0, 2000.0],  # P1 has $6000 sales but only 1% margin (revenue trap)
    })
    engine = MetricsEngine(data=prod_df)
    cohorts = engine.get_top_bottom_products(n=2)

    assert len(cohorts["top_profitable"]) == 2
    assert cohorts["top_profitable"].iloc[0]["product_id"] == "P3"
    assert len(cohorts["revenue_traps"]) == 1
    assert cohorts["revenue_traps"].iloc[0]["product_id"] == "P1"
