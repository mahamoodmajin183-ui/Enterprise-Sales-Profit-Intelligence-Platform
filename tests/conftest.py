"""Pytest shared fixtures and mock datasets for unit testing."""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture
def sample_raw_dataframe():
    """Generates a small representative raw dataframe for testing transformations."""
    data = {
        "Row ID": [1, 2, 3, 4, 5],
        "Order ID": ["ORD-001", "ORD-001", "ORD-002", "ORD-003", "ORD-004"],
        "Order Date": ["1/15/2023", "1/15/2023", "2/20/2023", "3/10/2023", "invalid-date"],
        "Ship Date": ["1/18/2023", "1/18/2023", "2/22/2023", "3/12/2023", "3/15/2023"],
        "Ship Mode": ["Standard Class", "Standard Class", "Second Class", "First Class", "Standard Class"],
        "Customer ID": ["CUST-1", "CUST-1", "CUST-2", "CUST-3", "CUST-4"],
        "Customer Name": ["Alice Smith", "Alice Smith", "Bob Jones", "Charlie Brown", "David Miller"],
        "Segment": ["Consumer", "Consumer", "Corporate", "Home Office", "Consumer"],
        "Country": ["United States", "United States", "United States", "United States", "United States"],
        "City": ["New York City", "New York City", "Los Angeles", "Chicago", "Houston"],
        "State": ["New York", "New York", "California", "Illinois", "Texas"],
        "Postal Code": [10001, 10001, 90001, 60601, 77001],
        "Region": ["East", "East", "West", "Central", "Central"],
        "Product ID": ["PROD-A", "PROD-B", "PROD-C", "PROD-D", "PROD-E"],
        "Category": ["Technology", "Office Supplies", "Furniture", "Technology", "Furniture"],
        "Sub-Category": ["Phones", "Paper", "Chairs", "Machines", "Tables"],
        "Product Name": ["Smartphone X", "Copy Paper", "Ergo Chair", "Laser Printer", "Dining Table"],
        "Sales": [1000.0, 50.0, 400.0, 1200.0, -100.0],  # Includes negative sales row
        "Quantity": [2, 5, 2, 1, 0],                      # Includes 0 quantity row
        "Discount": [0.10, 0.0, 0.20, 0.70, 1.5],         # Includes invalid discount row
        "Profit": [250.0, 20.0, 80.0, -400.0, -50.0],
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_returns_dataframe():
    """Generates mock returns dataframe."""
    return pd.DataFrame({
        "Returned": ["Yes", "Yes"],
        "Order ID": ["ORD-001", "ORD-003"]
    })


@pytest.fixture
def empty_dataframe():
    """Generates an empty dataframe with standard columns."""
    from src.config import REQUIRED_COLUMNS
    return pd.DataFrame(columns=REQUIRED_COLUMNS)
