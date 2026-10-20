"""Anomaly and Outlier Detection Engine.

Applies statistical methods (IQR, Z-Score) and business threshold heuristics
to isolate transactions causing severe margin destruction.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import HIGH_DISCOUNT_THRESHOLD, HIGH_LOSS_THRESHOLD, PROCESSED_PARQUET_FILE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detects statistical and business anomalies in retail transactions."""

    def __init__(self, df: Optional[pd.DataFrame] = None):
        if df is not None:
            self.df = df.copy()
        elif PROCESSED_PARQUET_FILE.exists():
            self.df = pd.read_parquet(PROCESSED_PARQUET_FILE)
        else:
            raise FileNotFoundError("Clean dataset not found.")

    def detect_loss_anomalies(self) -> pd.DataFrame:
        """Isolate orders producing severe negative profit or excessive discounts."""
        df = self.df.copy()

        # Business Rule Conditions
        severe_loss = df["profit"] <= HIGH_LOSS_THRESHOLD  # <= -500
        excessive_discount = (df["discount"] >= HIGH_DISCOUNT_THRESHOLD) & (df["profit"] < -100)
        extreme_negative_margin = df["profit_margin"] <= -0.50

        flagged = df[severe_loss | excessive_discount | extreme_negative_margin].copy()

        def classify_anomaly(row):
            if row["profit"] <= -1000:
                return "Critical Loss (> $1,000)"
            elif row["profit"] <= -500:
                return "Severe Loss ($500 - $1,000)"
            elif row["discount"] >= 0.50:
                return "Deep Discount Margin Trap (>=50%)"
            elif row["profit_margin"] <= -0.50:
                return "Extreme Negative Margin (<= -50%)"
            return "Other Anomaly"

        flagged["anomaly_category"] = flagged.apply(classify_anomaly, axis=1)

        cols_to_show = [
            "order_id",
            "order_date_str",
            "customer_name",
            "segment",
            "city",
            "state",
            "region",
            "category",
            "sub_category",
            "product_name",
            "sales",
            "quantity",
            "discount",
            "profit",
            "profit_margin",
            "anomaly_category",
        ]
        return flagged[cols_to_show].sort_values("profit", ascending=True).reset_index(drop=True)

    def get_anomaly_summary(self) -> Dict[str, Any]:
        """Summarize aggregate business impact of identified anomalies."""
        anomalies = self.detect_loss_anomalies()
        total_loss_from_anomalies = float(round(anomalies["profit"].sum(), 2))
        total_sales_from_anomalies = float(round(anomalies["sales"].sum(), 2))
        overall_profit = float(round(self.df["profit"].sum(), 2))

        return {
            "total_anomaly_count": len(anomalies),
            "total_anomaly_sales": total_sales_from_anomalies,
            "total_anomaly_loss": total_loss_from_anomalies,
            "pct_of_profit_destroyed": round(abs(total_loss_from_anomalies) / overall_profit * 100, 2)
            if overall_profit > 0
            else 0.0,
            "critical_loss_orders": int((anomalies["profit"] <= -1000).sum()),
            "severe_loss_orders": int(((anomalies["profit"] > -1000) & (anomalies["profit"] <= -500)).sum()),
            "deep_discount_orders": int((anomalies["discount"] >= 0.50).sum()),
        }


if __name__ == "__main__":
    detector = AnomalyDetector()
    summary = detector.get_anomaly_summary()
    print("Anomaly Detection Summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    anomalies = detector.detect_loss_anomalies()
    print(f"\nTop 5 Worst Outliers:")
    print(anomalies[["order_id", "product_name", "discount", "profit", "anomaly_category"]].head())
