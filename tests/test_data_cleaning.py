"""Unit tests for data cleaning and transformation pipeline."""

import pytest
import pandas as pd
from src.data_cleaner import clean_and_transform, standardize_columns, assign_discount_bracket


def test_standardize_columns(sample_raw_dataframe):
    """Verify headers are lowercased and snake_cased."""
    df_std = standardize_columns(sample_raw_dataframe)
    assert "row_id" in df_std.columns
    assert "order_id" in df_std.columns
    assert "sub_category" in df_std.columns
    assert "Row ID" not in df_std.columns


def test_discount_bracket_tiers():
    """Verify correct classification across discount brackets."""
    assert assign_discount_bracket(0.0) == "0% (None)"
    assert assign_discount_bracket(0.05) == "1% - 10% (Low)"
    assert assign_discount_bracket(0.15) == "11% - 20% (Moderate)"
    assert assign_discount_bracket(0.35) == "21% - 40% (High)"
    assert assign_discount_bracket(0.60) == "> 40% (Deep Discount)"


def test_duplicate_and_invalid_filtering(sample_raw_dataframe, sample_returns_dataframe):
    """Ensure invalid rows (negative sales, zero quantity, invalid dates, invalid discounts) are filtered."""
    cleaned_df, summary = clean_and_transform(sample_raw_dataframe, sample_returns_dataframe)

    # Row 5 had negative sales, quantity 0, invalid date, discount > 1.0 -> should be filtered
    assert len(cleaned_df) == 4
    assert (cleaned_df["sales"] >= 0).all()
    assert (cleaned_df["quantity"] >= 1).all()
    assert (cleaned_df["discount"] <= 1.0).all()
    assert (cleaned_df["discount"] >= 0.0).all()
    assert summary["status"] == "PASSED"


def test_returns_flagging(sample_raw_dataframe, sample_returns_dataframe):
    """Verify returns are accurately joined by Order ID."""
    cleaned_df, _ = clean_and_transform(sample_raw_dataframe, sample_returns_dataframe)
    returned_orders = cleaned_df[cleaned_df["is_returned"]]["order_id"].unique()
    assert "ORD-001" in returned_orders
    assert "ORD-003" in returned_orders
    assert "ORD-002" not in returned_orders


def test_shipping_logic(sample_raw_dataframe, sample_returns_dataframe):
    """Verify ship date is never prior to order date."""
    cleaned_df, _ = clean_and_transform(sample_raw_dataframe, sample_returns_dataframe)
    assert (cleaned_df["shipping_days"] >= 0).all()
