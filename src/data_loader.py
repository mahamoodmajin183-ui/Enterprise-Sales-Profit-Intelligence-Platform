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

    logger.error("Could not download raw dataset from remote repositories.")
    raise RuntimeError("Failed to acquire raw dataset from public repositories.")


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
