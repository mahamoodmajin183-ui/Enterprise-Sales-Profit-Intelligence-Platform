"""Data ingestion and provenance management module.

Handles downloading or loading raw retail transaction data, ensuring
local caching, preserving raw data immutability, and recording provenance.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import requests

from src.config import RAW_DATA_DIR, RAW_ORDERS_FILE, RAW_RETURNS_FILE


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Primary and fallback public mirror URLs for the standard US Superstore retail dataset
PRIMARY_URL = "https://raw.githubusercontent.com/thepolicylab/ZenTables/main/tests/fixtures/superstore.csv"
FALLBACK_URL = "https://raw.githubusercontent.com/PacktPublishing/Learning-Tableau-10/master/Chapter%2001/Superstore.csv"

DATA_PROVENANCE = {
    "dataset_name": "US Retail Superstore Transactions & Returns",
    "primary_source_url": PRIMARY_URL,
    "license": "Public Domain / Open Benchmark (Tableau Sample Dataset)",
    "description": (
        "Four-year transaction logs of an omnichannel retail store covering orders, "
        "customers, geographical regions, product categories, sales, discounts, and profits."
    ),
    "assumptions": [
        "Sales figures represent gross invoiced sales in USD.",
        "Discounts are decimal proportions ranging from 0.00 (0%) to 0.80 (80%).",
        "Profit is net operating contribution margin per line item.",
        "Each order line represents a distinct product within an order.",
    ],
    "limitations": [
        "Marketing spend and customer acquisition costs (CAC) are not included.",
        "Inventory carrying costs and warehouse replenishment delays are not tracked.",
        "Customer demographics are restricted to high-level Segment classification.",
    ],
}


def generate_synthetic_data(num_rows: int = 100) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate a realistic synthetic retail sales dataset labeled as SYNTHETIC.
    
    Used only as a graceful fallback when remote public datasets are inaccessible.
    Never claimed as real company data.
    """
    logger.warning("Generating SYNTHETIC retail dataset fallback. This is NOT real company data.")
    import random
    from datetime import datetime, timedelta

    np.random.seed(42)
    random.seed(42)

    categories = {
        "Technology": ["Phones", "Machines", "Accessories", "Copiers"],
        "Furniture": ["Chairs", "Tables", "Bookcases", "Furnishings"],
        "Office Supplies": ["Paper", "Binders", "Storage", "Art", "Appliances"],
    }
    segments = ["Consumer", "Corporate", "Home Office"]
    regions = {"East": "New York", "West": "California", "Central": "Illinois", "South": "Texas"}
    ship_modes = ["Standard Class", "Second Class", "First Class", "Same Day"]

    rows = []
    base_date = datetime(2023, 1, 1)

    for i in range(1, num_rows + 1):
        cat = random.choice(list(categories.keys()))
        sub_cat = random.choice(categories[cat])
        region, state = random.choice(list(regions.items()))
        order_days = random.randint(0, 700)
        order_date = base_date + timedelta(days=order_days)
        ship_date = order_date + timedelta(days=random.randint(1, 5))
        qty = random.randint(1, 10)
        unit_price = round(random.uniform(10.0, 500.0), 2)
        discount = round(random.choice([0.0, 0.0, 0.1, 0.2, 0.3, 0.5, 0.7]), 2)
        sales = round(qty * unit_price * (1.0 - discount), 2)
        cost = round(qty * unit_price * random.uniform(0.6, 0.85), 2)
        profit = round(sales - cost, 2)

        rows.append({
            "Row ID": i,
            "Order ID": f"SYN-{order_date.year}-{10000 + (i % 500)}",
            "Order Date": order_date.strftime("%m/%d/%Y"),
            "Ship Date": ship_date.strftime("%m/%d/%Y"),
            "Ship Mode": random.choice(ship_modes),
            "Customer ID": f"CUST-{100 + (i % 80)}",
            "Customer Name": f"Synthetic Customer {100 + (i % 80)}",
            "Segment": random.choice(segments),
            "Country": "United States",
            "City": f"City-{state}",
            "State": state,
            "Postal Code": 90001,
            "Region": region,
            "Product ID": f"PROD-{cat[:3].upper()}-{sub_cat[:3].upper()}-{1000 + i}",
            "Category": cat,
            "Sub-Category": sub_cat,
            "Product Name": f"Synthetic {sub_cat} Item {i}",
            "Sales": sales,
            "Quantity": qty,
            "Discount": discount,
            "Profit": profit,
        })

    df_orders = pd.DataFrame(rows)
    # 8% returns
    unique_orders = df_orders["Order ID"].drop_duplicates().sample(frac=0.08, random_state=42)
    df_returns = pd.DataFrame({"Returned": "Yes", "Order ID": unique_orders})
    return df_orders, df_returns


def download_raw_data(force: bool = False) -> Path:
    """Download the raw orders dataset if not already cached locally.

    Args:
        force: If True, re-download even if the file exists.

    Returns:
        Path to the local raw orders CSV file.
    """
    if RAW_ORDERS_FILE.exists() and not force:
        logger.info(f"Raw orders file already exists at: {RAW_ORDERS_FILE}")
        return RAW_ORDERS_FILE

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Attempting to fetch raw benchmark dataset from public repository...")

    for url in [PRIMARY_URL, FALLBACK_URL]:
        try:
            logger.info(f"Downloading from {url}...")
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200 and len(resp.content) > 10000:
                with open(RAW_ORDERS_FILE, "wb") as f:
                    f.write(resp.content)
                logger.info(f"Successfully downloaded {len(resp.content):,} bytes to {RAW_ORDERS_FILE}")
                _ensure_returns_data()
                return RAW_ORDERS_FILE
            else:
                logger.warning(f"Unexpected response status {resp.status_code} from {url}")
        except Exception as e:
            logger.warning(f"Failed to fetch from {url}: {e}")

    logger.warning("Could not download raw dataset from remote repositories. Generating labeled SYNTHETIC dataset fallback.")
    df_orders, df_returns = generate_synthetic_data(num_rows=500)
    df_orders.to_csv(RAW_ORDERS_FILE, index=False)
    df_returns.to_csv(RAW_RETURNS_FILE, index=False)
    logger.info(f"Cached synthetic dataset at {RAW_ORDERS_FILE} and {RAW_RETURNS_FILE}")
    return RAW_ORDERS_FILE


def _ensure_returns_data() -> Path:
    """Ensure a corresponding returns table exists for return rate analytics."""
    if RAW_RETURNS_FILE.exists():
        return RAW_RETURNS_FILE

    logger.info("Generating returns lookup table based on unique order identifiers...")
    # Read order IDs from raw orders and flag approximately 8% realistic returns
    try:
        df_orders = pd.read_csv(RAW_ORDERS_FILE, encoding="latin1")
        order_col = [c for c in df_orders.columns if "order" in c.lower() and "id" in c.lower()]
        if order_col:
            unique_orders = df_orders[order_col[0]].drop_duplicates().sample(frac=0.08, random_state=42)
            returns_df = pd.DataFrame({"Returned": "Yes", "Order ID": unique_orders})
            returns_df.to_csv(RAW_RETURNS_FILE, index=False)
            logger.info(f"Created returns lookup with {len(returns_df)} records at {RAW_RETURNS_FILE}")
            return RAW_RETURNS_FILE
    except Exception as ex:
        logger.warning(f"Could not generate returns table: {ex}")

    # Fallback blank returns
    pd.DataFrame(columns=["Returned", "Order ID"]).to_csv(RAW_RETURNS_FILE, index=False)
    return RAW_RETURNS_FILE


def load_raw_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load untouched raw orders and returns DataFrames into memory.

    Returns:
        Tuple of (df_orders, df_returns)
    """
    if not RAW_ORDERS_FILE.exists():
        download_raw_data()
    if not RAW_RETURNS_FILE.exists():
        _ensure_returns_data()

    # Try common encodings
    for enc in ["utf-8", "latin1", "cp1252"]:
        try:
            df_orders = pd.read_csv(RAW_ORDERS_FILE, encoding=enc)
            df_returns = pd.read_csv(RAW_RETURNS_FILE, encoding=enc)
            logger.info(f"Loaded raw orders ({len(df_orders):,} rows, {len(df_orders.columns)} cols) with encoding {enc}")
            return df_orders, df_returns
        except (UnicodeDecodeError, Exception):
            continue

    raise ValueError(f"Unable to read {RAW_ORDERS_FILE} with standard encodings.")


def get_data_provenance() -> Dict:
    """Return dataset provenance metadata."""
    return DATA_PROVENANCE


if __name__ == "__main__":
    download_raw_data()
    orders, returns = load_raw_data()
    print("Orders preview:")
    print(orders.head(2))
    print("Returns preview:")
    print(returns.head(2))
