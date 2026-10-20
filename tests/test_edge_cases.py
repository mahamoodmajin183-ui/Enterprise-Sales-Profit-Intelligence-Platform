"""Unit tests for edge cases: empty data, extreme values, and boundary conditions."""

import pytest
import pandas as pd
from src.metrics_engine import MetricsEngine
from src.anomaly_detector import AnomalyDetector


def test_empty_dataframe_kpis(empty_dataframe):
    """Verify empty DataFrame returns zeroed metrics without exceptions."""
    engine = MetricsEngine(data=empty_dataframe)
    kpis = engine.calculate_executive_kpis()

    assert kpis["total_revenue"] == 0.0
    assert kpis["total_profit"] == 0.0
    assert kpis["total_orders"] == 0
    assert kpis["profit_margin_pct"] == 0.0

    monthly = engine.get_monthly_trends()
    assert monthly.empty

    cats = engine.get_category_metrics()
    assert cats.empty


def test_single_row_dataframe():
    """Verify single-row dataset executes cleanly."""
    single_df = pd.DataFrame({
        "order_id": ["O-1"],
        "customer_id": ["C-1"],
        "sales": [150.0],
        "profit": [30.0],
        "quantity": [3],
        "discount": [0.1],
        "is_returned": [False],
        "order_year": [2024],
        "order_month": [5],
        "order_year_month": ["2024-05"],
        "category": ["Technology"],
        "sub_category": ["Phones"],
        "region": ["West"],
        "state": ["California"],
        "discount_bracket": ["1% - 10% (Low)"],
        "row_id": [1],
    })
    engine = MetricsEngine(data=single_df)
    kpis = engine.calculate_executive_kpis()

    assert kpis["total_revenue"] == 150.0
    assert kpis["total_profit"] == 30.0
    assert kpis["profit_margin_pct"] == 20.0
    assert kpis["total_orders"] == 1


def test_anomaly_detector_handles_no_anomalies():
    """Verify anomaly detector does not crash on completely healthy data."""
    healthy_df = pd.DataFrame({
        "order_id": ["O-1", "O-2"],
        "order_date_str": ["2023-01-01", "2023-01-02"],
        "customer_name": ["User A", "User B"],
        "segment": ["Consumer", "Consumer"],
        "city": ["Seattle", "Portland"],
        "state": ["Washington", "Oregon"],
        "region": ["West", "West"],
        "category": ["Technology", "Office Supplies"],
        "sub_category": ["Phones", "Paper"],
        "product_name": ["Phone A", "Paper B"],
        "sales": [500.0, 100.0],
        "quantity": [1, 2],
        "discount": [0.0, 0.05],
        "profit": [100.0, 25.0],
        "profit_margin": [0.20, 0.25],
    })
    detector = AnomalyDetector(df=healthy_df)
    anomalies = detector.detect_loss_anomalies()
    summary = detector.get_anomaly_summary()

    assert len(anomalies) == 0
    assert summary["total_anomaly_count"] == 0
    assert summary["pct_of_profit_destroyed"] == 0.0
