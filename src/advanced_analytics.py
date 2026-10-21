"""Advanced Analytics Engine — Stage 5.

Implements statistically grounded analyses on top of the cleaned retail dataset:
  - Profit anomaly detection: IQR fences and Z-score flagging (documented thresholds).
  - Sales trend change-point detection: rolling mean slope and MoM acceleration.
  - Discount-profitability correlation: Spearman rho per sub-category.
  - Product performance matrix: high-revenue / low-margin 'revenue traps'.
  - Regional performance composite scoring.
  - Seasonality: quarter-over-quarter average deviation from annual mean.

Methodology notes
-----------------
  * IQR fences: Q1 - 1.5*IQR  (lower)  Q3 + 1.5*IQR  (upper).
  * Z-score flagging: |z| > 3.0 (configurable via ANOMALY_ZSCORE_THRESHOLD).
  * Spearman rho is used (not Pearson) because discount and margin are not normally
    distributed. Correlation != causation; findings are labelled as associations.
  * All analyses operate on the passed DataFrame (never mutate the original).
  * Small-sample guards: groups with fewer than MIN_SAMPLE rows are excluded from
    correlation and seasonality analyses and reported separately.

All public methods return plain pandas DataFrames or typed dicts for easy serialisation.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import ANOMALY_ZSCORE_THRESHOLD, PROCESSED_PARQUET_FILE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Minimum sample size for statistical analysis (suppress noisy small-n groups)
MIN_SAMPLE = 10


class AdvancedAnalytics:
    """Statistically rigorous advanced analytics over retail transaction data."""

    def __init__(self, df: Optional[pd.DataFrame] = None):
        if df is not None:
            self.df = df.copy()
        elif PROCESSED_PARQUET_FILE.exists():
            self.df = pd.read_parquet(PROCESSED_PARQUET_FILE)
        else:
            raise FileNotFoundError(f"Processed dataset not found at {PROCESSED_PARQUET_FILE}")
        self._validate_schema()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_schema(self) -> None:
        required = {"profit", "sales", "discount", "order_date", "category",
                    "sub_category", "region", "state", "product_name",
                    "order_year", "order_month", "order_quarter"}
        missing = required - set(self.df.columns)
        if missing:
            raise ValueError(f"Dataset missing required columns: {missing}")

    @staticmethod
    def _iqr_bounds(series: pd.Series) -> Tuple[float, float]:
        """Return (lower_fence, upper_fence) using Tukey's 1.5xIQR method."""
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        return float(q1 - 1.5 * iqr), float(q3 + 1.5 * iqr)

    @staticmethod
    def _zscore(series: pd.Series) -> pd.Series:
        """Return Z-scores; returns zero series if std == 0."""
        mu, sigma = series.mean(), series.std()
        if sigma == 0:
            return pd.Series(np.zeros(len(series)), index=series.index)
        return (series - mu) / sigma

    # ------------------------------------------------------------------
    # 1. Profit Anomaly Detection
    # ------------------------------------------------------------------

    def detect_profit_anomalies(self) -> pd.DataFrame:
        """Identify transactions with statistically unusual profit values.

        Method
        ------
        Two independent criteria — any transaction matching either is flagged:
          (a) Profit lies below the IQR lower fence  (Q1 - 1.5*IQR).
          (b) |Z-score| > ANOMALY_ZSCORE_THRESHOLD (default 3.0).

        Returns
        -------
        DataFrame with one row per flagged transaction, including flag reasons
        and both the IQR fence and Z-score values for full auditability.
        """
        df = self.df.copy()
        lower_fence, upper_fence = self._iqr_bounds(df["profit"])
        df["profit_zscore"] = self._zscore(df["profit"]).round(4)
        df["iqr_lower_fence"] = round(lower_fence, 2)
        df["iqr_upper_fence"] = round(upper_fence, 2)

        below_iqr = df["profit"] < lower_fence
        above_iqr = df["profit"] > upper_fence
        high_zscore = df["profit_zscore"].abs() > ANOMALY_ZSCORE_THRESHOLD

        df["is_anomaly"] = below_iqr | above_iqr | high_zscore

        def _reason(row) -> str:
            reasons = []
            if row["profit"] < row["iqr_lower_fence"]:
                reasons.append(f"Below IQR fence (${row['iqr_lower_fence']:.0f})")
            if row["profit"] > row["iqr_upper_fence"]:
                reasons.append(f"Above IQR fence (${row['iqr_upper_fence']:.0f})")
            if abs(row["profit_zscore"]) > ANOMALY_ZSCORE_THRESHOLD:
                reasons.append(f"|Z-score|={abs(row['profit_zscore']):.2f}>{ANOMALY_ZSCORE_THRESHOLD}")
            return "; ".join(reasons) if reasons else ""

        anomalies = df[df["is_anomaly"]].copy()
        anomalies["anomaly_reason"] = anomalies.apply(_reason, axis=1)

        display_cols = [
            "order_id", "order_date_str", "customer_name", "segment",
            "city", "state", "region", "category", "sub_category", "product_name",
            "sales", "quantity", "discount", "profit", "profit_margin",
            "profit_zscore", "iqr_lower_fence", "iqr_upper_fence", "anomaly_reason",
        ]
        available = [c for c in display_cols if c in anomalies.columns]
        result = anomalies[available].sort_values("profit").reset_index(drop=True)
        logger.info(
            "Profit anomaly detection: %d flagged (IQR fence [%.2f, %.2f], Z-threshold %.1f)",
            len(result), lower_fence, upper_fence, ANOMALY_ZSCORE_THRESHOLD,
        )
        return result

    def get_anomaly_summary(self) -> Dict[str, Any]:
        """Aggregate statistics on detected profit anomalies."""
        anomalies = self.detect_profit_anomalies()
        total_profit = float(self.df["profit"].sum())
        anomaly_profit = float(anomalies["profit"].sum()) if not anomalies.empty else 0.0
        lower_fence, upper_fence = self._iqr_bounds(self.df["profit"])
        return {
            "total_flagged": len(anomalies),
            "total_transactions": len(self.df),
            "anomaly_rate_pct": round(len(anomalies) / max(len(self.df), 1) * 100, 2),
            "total_anomaly_profit": round(anomaly_profit, 2),
            "negative_anomaly_count": int((anomalies["profit"] < 0).sum()) if not anomalies.empty else 0,
            "positive_anomaly_count": int((anomalies["profit"] > 0).sum()) if not anomalies.empty else 0,
            "pct_profit_impact": round(abs(anomaly_profit) / max(abs(total_profit), 1) * 100, 2),
            "iqr_lower_fence": round(lower_fence, 2),
            "iqr_upper_fence": round(upper_fence, 2),
            "zscore_threshold": ANOMALY_ZSCORE_THRESHOLD,
            "methodology": "IQR Tukey fences (1.5xIQR) + Z-score |z|>3.0",
        }

    # ------------------------------------------------------------------
    # 2. Sales Trend Analysis
    # ------------------------------------------------------------------

    def get_trend_analysis(self) -> pd.DataFrame:
        """Monthly revenue with rolling statistics and trend direction.

        Computed fields
        ---------------
        - rolling_3m_avg : 3-month centred rolling mean of revenue.
        - mom_change_pct : Month-over-month % revenue change.
        - mom_acceleration: Change in MoM% (2nd derivative proxy).
        - trend_signal   : 'Accelerating growth' / 'Accelerating decline' / 'Stable' etc.

        Thresholds
        ----------
        Signal applied only when |mom_change_pct| >= 5% AND
        |mom_acceleration| >= 2% to avoid noise on small fluctuations.
        """
        monthly = (
            self.df.groupby(["order_year", "order_month", "order_year_month"])
            .agg(monthly_revenue=("sales", "sum"), monthly_profit=("profit", "sum"))
            .reset_index()
            .sort_values(["order_year", "order_month"])
            .reset_index(drop=True)
        )
        monthly["monthly_revenue"] = monthly["monthly_revenue"].round(2)
        monthly["monthly_profit"] = monthly["monthly_profit"].round(2)

        monthly["rolling_3m_avg"] = (
            monthly["monthly_revenue"].rolling(window=3, center=True, min_periods=2).mean().round(2)
        )
        monthly["mom_change_pct"] = (
            monthly["monthly_revenue"].pct_change() * 100
        ).round(2)
        monthly["mom_acceleration"] = monthly["mom_change_pct"].diff().round(2)

        def _signal(row) -> str:
            if pd.isna(row["mom_change_pct"]) or pd.isna(row["mom_acceleration"]):
                return "Insufficient data"
            chg, acc = row["mom_change_pct"], row["mom_acceleration"]
            if abs(chg) < 5:
                return "Stable"
            if chg > 5 and acc > 2:
                return "Accelerating growth"
            if chg > 5 and acc < -2:
                return "Growth but decelerating"
            if chg < -5 and acc < -2:
                return "Accelerating decline"
            if chg < -5 and acc > 2:
                return "Decline but recovering"
            return "Stable"

        monthly["trend_signal"] = monthly.apply(_signal, axis=1)
        return monthly

    def get_seasonality_analysis(self) -> pd.DataFrame:
        """Quarter-based seasonality: mean deviation from annual average per quarter.

        Method
        ------
        For each (year, quarter) cell compute quarterly revenue.
        Annual mean = simple average of 4 quarters in that year.
        Deviation = (quarterly_revenue - annual_mean) / annual_mean * 100.
        Only years with all 4 quarters of data are included to avoid
        partial-year bias.

        Returns
        -------
        DataFrame with mean seasonal index per quarter across all complete years,
        +/- standard deviation across years.
        """
        quarterly = (
            self.df.groupby(["order_year", "order_quarter"])
            .agg(quarterly_revenue=("sales", "sum"))
            .reset_index()
        )

        # Keep only years with all 4 distinct quarters
        year_quarter_count = quarterly.groupby("order_year")["order_quarter"].nunique()
        complete_years = year_quarter_count[year_quarter_count == 4].index.tolist()

        if len(complete_years) < 2:
            logger.warning("Fewer than 2 complete years; seasonality analysis has limited validity.")

        quarterly = quarterly[quarterly["order_year"].isin(complete_years)].copy()

        annual_means = quarterly.groupby("order_year")["quarterly_revenue"].mean().rename("annual_mean")
        quarterly = quarterly.join(annual_means, on="order_year")
        quarterly["seasonal_deviation_pct"] = (
            (quarterly["quarterly_revenue"] - quarterly["annual_mean"]) / quarterly["annual_mean"] * 100
        ).round(2)

        seasonality = (
            quarterly.groupby("order_quarter")
            .agg(
                mean_seasonal_index=("seasonal_deviation_pct", "mean"),
                std_seasonal_index=("seasonal_deviation_pct", "std"),
                years_included=("order_year", "count"),
            )
            .reset_index()
        )
        seasonality["mean_seasonal_index"] = seasonality["mean_seasonal_index"].round(2)
        seasonality["std_seasonal_index"] = seasonality["std_seasonal_index"].round(2)
        # order_quarter is stored as string ("Q1", "Q2", "Q3", "Q4")
        seasonality["quarter_label"] = seasonality["order_quarter"].map(
            {"Q1": "Q1 (Jan-Mar)", "Q2": "Q2 (Apr-Jun)", "Q3": "Q3 (Jul-Sep)", "Q4": "Q4 (Oct-Dec)"}
        )
        return seasonality

    # ------------------------------------------------------------------
    # 3. Discount-Profitability Correlation
    # ------------------------------------------------------------------

    def get_discount_correlation(self) -> Dict[str, Any]:
        """Compute Spearman rank correlation between discount and profit margin.

        Spearman rho is used instead of Pearson because:
          - Discount values form discrete clusters (0, 0.1, 0.2, ...).
          - Profit margin is bounded but skewed.
          - No normality assumption required.

        Groups with < MIN_SAMPLE transactions are excluded and reported.

        Returns
        -------
        dict with overall rho, by_category DataFrame, by_sub_category DataFrame,
        excluded groups list, and a plain-language interpretation.
        """
        df = self.df[["discount", "profit_margin", "category", "sub_category"]].dropna()

        # Overall
        if df.empty or df["discount"].nunique() <= 1 or df["profit_margin"].nunique() <= 1:
            rho_all, p_all = 0.0, 1.0
        else:
            rho_all, p_all = stats.spearmanr(df["discount"], df["profit_margin"])

        # Per category
        cat_results = []
        excluded = []
        for cat, grp in df.groupby("category"):
            if len(grp) < MIN_SAMPLE:
                excluded.append({"group": cat, "n": len(grp), "reason": f"n < {MIN_SAMPLE}"})
                continue
            if grp["discount"].nunique() <= 1 or grp["profit_margin"].nunique() <= 1:
                rho, p = 0.0, 1.0
            else:
                rho, p = stats.spearmanr(grp["discount"], grp["profit_margin"])
            cat_results.append({
                "category": cat,
                "n": len(grp),
                "spearman_rho": round(float(rho), 4),
                "p_value": round(float(p), 6),
                "significant_at_05": bool(p < 0.05),
                "direction": "Negative (higher discount, lower margin)" if rho < 0 else "Positive",
                "strength": (
                    "Strong" if abs(rho) >= 0.6
                    else "Moderate" if abs(rho) >= 0.3
                    else "Weak"
                ),
            })

        cat_df = pd.DataFrame(cat_results)

        # Per sub-category
        sub_results = []
        for (cat, sub), grp in df.groupby(["category", "sub_category"]):
            if len(grp) < MIN_SAMPLE:
                excluded.append({"group": f"{cat}/{sub}", "n": len(grp), "reason": f"n < {MIN_SAMPLE}"})
                continue
            if grp["discount"].nunique() <= 1 or grp["profit_margin"].nunique() <= 1:
                rho, p = 0.0, 1.0
            else:
                rho, p = stats.spearmanr(grp["discount"], grp["profit_margin"])
            sub_results.append({
                "category": cat,
                "sub_category": sub,
                "n": len(grp),
                "spearman_rho": round(float(rho), 4),
                "p_value": round(float(p), 6),
                "significant_at_05": bool(p < 0.05),
            })
        sub_df = pd.DataFrame(sub_results)

        direction = "negative" if rho_all < 0 else "positive"
        strength = "strong" if abs(rho_all) >= 0.6 else "moderate" if abs(rho_all) >= 0.3 else "weak"
        sig_str = "statistically significant (p<0.05)" if p_all < 0.05 else "not statistically significant at p<0.05"
        interpretation = (
            f"Overall Spearman rho = {rho_all:.3f} ({direction}, {strength}, {sig_str}). "
            "This is an association, not proof of causation. Confounding factors "
            "(product mix, customer segment, order size) are not controlled for."
        )

        return {
            "overall_rho": round(float(rho_all), 4),
            "overall_p_value": round(float(p_all), 6),
            "overall_significant": bool(p_all < 0.05),
            "interpretation": interpretation,
            "by_category": cat_df,
            "by_sub_category": sub_df,
            "excluded_groups": excluded,
            "methodology": "Spearman rank correlation; groups with n<10 excluded",
        }

    # ------------------------------------------------------------------
    # 4. Product Performance Matrix
    # ------------------------------------------------------------------

    def get_product_performance_matrix(
        self,
        revenue_threshold: float = 1000.0,
        margin_warning_pct: float = 10.0,
    ) -> Dict[str, Any]:
        """Classify products into four performance quadrants.

        Quadrants
        ---------
        - Stars        : High revenue AND high margin
        - Revenue Traps: High revenue AND low/negative margin
        - Niche Gems   : Low revenue AND high margin
        - Laggards     : Low revenue AND low margin

        Parameters
        ----------
        revenue_threshold : Revenue cutoff (USD) between high/low revenue.
        margin_warning_pct: Margin % cutoff between high/low performance.
        """
        prod = (
            self.df.groupby(["product_id", "product_name", "category", "sub_category"])
            .agg(
                orders_count=("order_id", "nunique"),
                units_sold=("quantity", "sum"),
                total_revenue=("sales", "sum"),
                total_profit=("profit", "sum"),
                avg_discount_pct=("discount", lambda s: round(s.mean() * 100, 2)),
            )
            .reset_index()
        )
        prod["total_revenue"] = prod["total_revenue"].round(2)
        prod["total_profit"] = prod["total_profit"].round(2)
        unrounded_margin = prod["total_profit"] / prod["total_revenue"].replace(0, np.nan) * 100
        prod["profit_margin_pct"] = unrounded_margin.round(2)

        high_rev = prod["total_revenue"] >= revenue_threshold
        high_margin = unrounded_margin >= margin_warning_pct

        stars = prod[high_rev & high_margin].sort_values("total_profit", ascending=False).reset_index(drop=True)
        revenue_traps = prod[high_rev & ~high_margin].sort_values("total_revenue", ascending=False).reset_index(drop=True)
        niche_gems = prod[~high_rev & high_margin].sort_values("profit_margin_pct", ascending=False).reset_index(drop=True)
        laggards = prod[~high_rev & ~high_margin].sort_values("total_profit").reset_index(drop=True)

        logger.info(
            "Product matrix: %d stars, %d revenue traps, %d niche gems, %d laggards",
            len(stars), len(revenue_traps), len(niche_gems), len(laggards),
        )
        return {
            "stars": stars,
            "revenue_traps": revenue_traps,
            "niche_gems": niche_gems,
            "laggards": laggards,
            "thresholds": {
                "revenue_threshold_usd": revenue_threshold,
                "margin_warning_pct": margin_warning_pct,
            },
        }

    # ------------------------------------------------------------------
    # 5. Regional Performance Scoring
    # ------------------------------------------------------------------

    def get_regional_scorecard(self) -> pd.DataFrame:
        """Score each state on a composite performance index (0-100).

        Composite score is the equal-weighted average of percentile ranks for:
          - Profit margin % (higher is better)
          - Revenue per order (higher is better)
          - Return rate     (lower is better, rank inverted)
          - Average discount given (lower is better, rank inverted)

        Using percentile ranks makes the composite robust to outliers and
        scale differences between metrics.
        """
        reg = (
            self.df.groupby(["region", "state"])
            .agg(
                orders=("order_id", "nunique"),
                revenue=("sales", "sum"),
                profit=("profit", "sum"),
                returns=("is_returned", "sum"),
                avg_discount=("discount", "mean"),
            )
            .reset_index()
        )
        reg["revenue"] = reg["revenue"].round(2)
        reg["profit"] = reg["profit"].round(2)
        reg["profit_margin_pct"] = (reg["profit"] / reg["revenue"].replace(0, np.nan) * 100).round(2)
        reg["revenue_per_order"] = (reg["revenue"] / reg["orders"].replace(0, np.nan)).round(2)
        reg["return_rate_pct"] = (reg["returns"] / reg["orders"].replace(0, np.nan) * 100).round(2)
        reg["avg_discount_pct"] = (reg["avg_discount"] * 100).round(2)

        # Percentile ranks (higher = better)
        reg["rank_margin"] = reg["profit_margin_pct"].rank(pct=True)
        reg["rank_rev_per_order"] = reg["revenue_per_order"].rank(pct=True)
        reg["rank_return"] = (1 - reg["return_rate_pct"].rank(pct=True))
        reg["rank_discount"] = (1 - reg["avg_discount_pct"].rank(pct=True))

        reg["composite_score"] = (
            (reg["rank_margin"] + reg["rank_rev_per_order"] + reg["rank_return"] + reg["rank_discount"]) / 4 * 100
        ).round(1)

        return reg.sort_values("composite_score", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    analytics = AdvancedAnalytics()

    print("\n=== Profit Anomaly Summary ===")
    summary = analytics.get_anomaly_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")

    print("\n=== Discount Correlation (Overall) ===")
    corr = analytics.get_discount_correlation()
    print(f"  Rho: {corr['overall_rho']}  p={corr['overall_p_value']}")
    print(f"  {corr['interpretation']}")

    print("\n=== Product Matrix Summary ===")
    matrix = analytics.get_product_performance_matrix()
    for quad, val in matrix.items():
        if isinstance(val, pd.DataFrame):
            print(f"  {quad}: {len(val)} products")

    print("\n=== Seasonality ===")
    seas = analytics.get_seasonality_analysis()
    print(seas[["quarter_label", "mean_seasonal_index", "years_included"]].to_string(index=False))
