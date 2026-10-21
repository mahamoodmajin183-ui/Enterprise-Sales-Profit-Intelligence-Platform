"""Stage 5 Integration Tests — verified against the real retail dataset.

These tests load the actual cleaned parquet file and verify that the
AdvancedAnalytics engine produces outputs consistent with numbers that have
been independently verified by running ad-hoc queries on the dataset.

All expected values are documented inline so reviewers can cross-check them.

Skip condition
--------------
If the processed parquet file does not exist (e.g. CI without data), all
tests in this module are skipped gracefully.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import PROCESSED_PARQUET_FILE

# ---------------------------------------------------------------------------
# Module-level skip if the real dataset is absent
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    not PROCESSED_PARQUET_FILE.exists(),
    reason="Processed parquet not found — run the data pipeline first",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_df():
    """Load the actual cleaned dataset once for the whole module."""
    return pd.read_parquet(PROCESSED_PARQUET_FILE)


@pytest.fixture(scope="module")
def real_analytics(real_df):
    """AdvancedAnalytics instance backed by the real dataset."""
    from src.advanced_analytics import AdvancedAnalytics
    return AdvancedAnalytics(df=real_df)


# ---------------------------------------------------------------------------
# 1. Dataset shape guard
# ---------------------------------------------------------------------------

class TestDatasetBaseline:
    def test_row_count(self, real_df):
        """Dataset must have exactly 9,994 rows after cleaning."""
        assert len(real_df) == 9_994, f"Expected 9994 rows, got {len(real_df)}"

    def test_unique_orders(self, real_df):
        """Must have 5,009 distinct orders."""
        assert real_df["order_id"].nunique() == 5_009

    def test_unique_customers(self, real_df):
        """Must have 793 distinct customers."""
        assert real_df["customer_id"].nunique() == 793

    def test_total_revenue_approx(self, real_df):
        """Total revenue must be ~$2,297,200 (within $1)."""
        assert abs(real_df["sales"].sum() - 2_297_200.65) < 1.0

    def test_total_profit_approx(self, real_df):
        """Total profit must be ~$286,397 (within $1)."""
        assert abs(real_df["profit"].sum() - 286_396.54) < 1.0

    def test_year_range(self, real_df):
        """Dataset must cover exactly 2011–2014."""
        years = sorted(real_df["order_year"].unique().tolist())
        assert years == [2011, 2012, 2013, 2014]


# ---------------------------------------------------------------------------
# 2. IQR Bounds on Real Data
# ---------------------------------------------------------------------------

class TestIQROnRealData:
    def test_lower_fence_value(self, real_df):
        """Verified lower fence = −$39.72 (Q1 − 1.5×IQR)."""
        from src.advanced_analytics import AdvancedAnalytics
        lower, _ = AdvancedAnalytics._iqr_bounds(real_df["profit"])
        assert abs(lower - (-39.72)) < 0.5  # Allow rounding ±$0.50

    def test_upper_fence_value(self, real_df):
        """Verified upper fence = $70.81 (Q3 + 1.5×IQR)."""
        from src.advanced_analytics import AdvancedAnalytics
        _, upper = AdvancedAnalytics._iqr_bounds(real_df["profit"])
        assert abs(upper - 70.81) < 0.5

    def test_iqr_value(self, real_df):
        """Verified IQR = $27.63."""
        q1 = real_df["profit"].quantile(0.25)
        q3 = real_df["profit"].quantile(0.75)
        iqr = q3 - q1
        assert abs(iqr - 27.63) < 0.5


# ---------------------------------------------------------------------------
# 3. Profit Anomaly Detection on Real Data
# ---------------------------------------------------------------------------

class TestAnomalyDetectionOnRealData:
    def test_total_flagged_count(self, real_analytics):
        """1,881 transactions must be flagged (IQR union Z-score)."""
        result = real_analytics.detect_profit_anomalies()
        assert len(result) == 1_881, f"Expected 1881, got {len(result)}"

    def test_negative_anomaly_count(self, real_analytics):
        """604 anomalies should have profit < lower fence."""
        result = real_analytics.detect_profit_anomalies()
        neg = (result["profit"] < result["iqr_lower_fence"]).sum()
        assert neg == 604, f"Expected 604 below lower fence, got {neg}"

    def test_extreme_zscore_count(self, real_analytics):
        """107 anomalies should have |z-score| > 3.0."""
        result = real_analytics.detect_profit_anomalies()
        extreme = (result["profit_zscore"].abs() > 3.0).sum()
        assert extreme == 107, f"Expected 107 extreme z-score anomalies, got {extreme}"

    def test_anomaly_rate_pct(self, real_analytics):
        """Anomaly rate must be ~18.8%."""
        summary = real_analytics.get_anomaly_summary()
        assert abs(summary["anomaly_rate_pct"] - 18.82) < 0.1

    def test_all_anomalies_have_reason(self, real_analytics):
        """Every flagged transaction must have a non-empty anomaly_reason."""
        result = real_analytics.detect_profit_anomalies()
        assert result["anomaly_reason"].str.len().gt(0).all()

    def test_result_sorted_by_profit_ascending(self, real_analytics):
        """Results should be sorted from worst (lowest profit) to best."""
        result = real_analytics.detect_profit_anomalies()
        profits = result["profit"].tolist()
        assert profits == sorted(profits)


# ---------------------------------------------------------------------------
# 4. Seasonality on Real Data
# ---------------------------------------------------------------------------

class TestSeasonalityOnRealData:
    def test_four_quarters_returned(self, real_analytics):
        """Must return exactly 4 quarters for this complete dataset."""
        result = real_analytics.get_seasonality_analysis()
        assert len(result) == 4

    def test_q4_highest_seasonal_index(self, real_analytics):
        """Q4 must have the highest mean_seasonal_index."""
        result = real_analytics.get_seasonality_analysis()
        q4 = result[result["order_quarter"] == "Q4"]["mean_seasonal_index"].iloc[0]
        assert q4 == result["mean_seasonal_index"].max()

    def test_q1_lowest_seasonal_index(self, real_analytics):
        """Q1 must have the lowest mean_seasonal_index."""
        result = real_analytics.get_seasonality_analysis()
        q1 = result[result["order_quarter"] == "Q1"]["mean_seasonal_index"].iloc[0]
        assert q1 == result["mean_seasonal_index"].min()

    def test_q4_index_approx_value(self, real_analytics):
        """Q4 seasonal index should be approximately +52.8%."""
        result = real_analytics.get_seasonality_analysis()
        q4_idx = result[result["order_quarter"] == "Q4"]["mean_seasonal_index"].iloc[0]
        assert abs(q4_idx - 52.8) < 2.0, f"Q4 seasonal index: {q4_idx}"

    def test_q1_index_approx_value(self, real_analytics):
        """Q1 seasonal index should be approximately −38.6%."""
        result = real_analytics.get_seasonality_analysis()
        q1_idx = result[result["order_quarter"] == "Q1"]["mean_seasonal_index"].iloc[0]
        assert abs(q1_idx - (-38.6)) < 2.0, f"Q1 seasonal index: {q1_idx}"

    def test_years_included_is_four(self, real_analytics):
        """All 4 years (2011–2014) are complete, so years_included should be 4."""
        result = real_analytics.get_seasonality_analysis()
        assert (result["years_included"] == 4).all()


# ---------------------------------------------------------------------------
# 5. Product Matrix on Real Data
# ---------------------------------------------------------------------------

class TestProductMatrixOnRealData:
    def test_stars_count(self, real_analytics):
        """Stars (revenue >= $1000 AND margin >= 10%) must be 306."""
        result = real_analytics.get_product_performance_matrix()
        assert len(result["stars"]) == 306, f"Stars: {len(result['stars'])}"

    def test_revenue_traps_count(self, real_analytics):
        """Revenue Traps (revenue >= $1000 AND margin < 10%) must be 219."""
        result = real_analytics.get_product_performance_matrix()
        assert len(result["revenue_traps"]) == 219, f"Traps: {len(result['revenue_traps'])}"

    def test_niche_gems_count(self, real_analytics):
        """Niche Gems (revenue < $1000 AND margin >= 10%) must be 1,086."""
        result = real_analytics.get_product_performance_matrix()
        assert len(result["niche_gems"]) == 1_086, f"Gems: {len(result['niche_gems'])}"

    def test_laggards_count(self, real_analytics):
        """Laggards (revenue < $1000 AND margin < 10%) must be 283."""
        result = real_analytics.get_product_performance_matrix()
        assert len(result["laggards"]) == 283, f"Laggards: {len(result['laggards'])}"

    def test_total_product_count(self, real_analytics):
        """Stars + Traps + Gems + Laggards must equal total unique products."""
        from src.advanced_analytics import AdvancedAnalytics
        result = real_analytics.get_product_performance_matrix()
        total_quadrant = sum(len(result[q]) for q in ["stars", "revenue_traps", "niche_gems", "laggards"])
        df = real_analytics.df
        prod = df.groupby(["product_id", "product_name", "category", "sub_category"]).agg(rev=("sales", "sum")).reset_index()
        # All products should be in exactly one quadrant
        assert total_quadrant == len(prod)

    def test_cisco_in_revenue_traps(self, real_analytics):
        """Cisco TelePresence must appear in Revenue Traps."""
        result = real_analytics.get_product_performance_matrix()
        trap_names = result["revenue_traps"]["product_name"].str.lower().tolist()
        assert any("cisco" in n for n in trap_names), "Cisco not found in Revenue Traps"

    def test_stars_all_meet_thresholds(self, real_analytics):
        """All Stars must have revenue >= $1000 AND margin >= 10%."""
        result = real_analytics.get_product_performance_matrix()
        stars = result["stars"]
        assert (stars["total_revenue"] >= 1000).all()
        assert (stars["profit_margin_pct"] >= 10).all()

    def test_revenue_traps_all_meet_thresholds(self, real_analytics):
        """All Revenue Traps must have revenue >= $1000 AND margin < 10% (allowing <=10.0 for rounding)."""
        result = real_analytics.get_product_performance_matrix()
        traps = result["revenue_traps"]
        assert (traps["total_revenue"] >= 1000).all()
        assert (traps["profit_margin_pct"] <= 10.0).all()
        # Verify unrounded margins strictly below 10%
        unrounded = (traps["total_profit"] / traps["total_revenue"]) * 100
        assert (unrounded < 10.0).all()


# ---------------------------------------------------------------------------
# 6. Discount Correlation on Real Data
# ---------------------------------------------------------------------------

class TestDiscountCorrelationOnRealData:
    def test_overall_rho_is_negative(self, real_analytics):
        """Overall Spearman rho must be negative (higher discount, lower margin)."""
        result = real_analytics.get_discount_correlation()
        assert result["overall_rho"] < 0, f"Expected negative rho, got {result['overall_rho']}"

    def test_rho_is_strong(self, real_analytics):
        """With clear discount-margin destruction, |rho| should be >= 0.3."""
        result = real_analytics.get_discount_correlation()
        assert abs(result["overall_rho"]) >= 0.3

    def test_overall_is_significant(self, real_analytics):
        """With n=9,994 and strong signal, correlation must be significant (p < 0.05)."""
        result = real_analytics.get_discount_correlation()
        assert result["overall_significant"] is True

    def test_all_categories_have_negative_rho(self, real_analytics):
        """Discount-margin relationship should be negative in all 3 categories."""
        result = real_analytics.get_discount_correlation()
        cat_df = result["by_category"]
        assert (cat_df["spearman_rho"] < 0).all()

    def test_category_results_have_three_rows(self, real_analytics):
        """Three product categories must each produce a correlation result."""
        result = real_analytics.get_discount_correlation()
        assert len(result["by_category"]) == 3


# ---------------------------------------------------------------------------
# 7. Regional Scorecard on Real Data
# ---------------------------------------------------------------------------

class TestRegionalScorecardOnRealData:
    def test_all_states_included(self, real_analytics):
        """Scorecard must include all states present in the dataset."""
        result = real_analytics.get_regional_scorecard()
        df = real_analytics.df
        expected_states = set(df["state"].unique())
        result_states = set(result["state"].unique())
        assert expected_states == result_states

    def test_scores_in_valid_range(self, real_analytics):
        """All composite scores must be in [0, 100]."""
        result = real_analytics.get_regional_scorecard()
        assert (result["composite_score"] >= 0).all()
        assert (result["composite_score"] <= 100).all()

    def test_sorted_descending(self, real_analytics):
        """Scorecard must be sorted with highest composite score first."""
        result = real_analytics.get_regional_scorecard()
        scores = result["composite_score"].tolist()
        assert scores == sorted(scores, reverse=True)

    def test_west_region_profit_verified(self, real_analytics):
        """West region profit must be ~$108,418 (verified)."""
        result = real_analytics.get_regional_scorecard()
        west = result[result["region"] == "West"]["profit"].sum()
        assert abs(west - 108_418.31) < 10.0, f"West profit: {west}"

    def test_central_region_margin_is_lowest(self, real_analytics):
        """Central must have the lowest profit margin among the 4 regions."""
        result = real_analytics.get_regional_scorecard()
        reg_total = result.groupby("region").agg(profit=("profit", "sum"), revenue=("revenue", "sum"))
        reg_margin = reg_total["profit"] / reg_total["revenue"]
        assert reg_margin.idxmin() == "Central"


# ---------------------------------------------------------------------------
# 8. Trend Analysis on Real Data
# ---------------------------------------------------------------------------

class TestTrendAnalysisOnRealData:
    def test_monthly_periods_count(self, real_analytics):
        """4 years × 12 months = 48 monthly periods."""
        result = real_analytics.get_trend_analysis()
        assert len(result) == 48, f"Expected 48 monthly periods, got {len(result)}"

    def test_q4_2014_is_strongest_month(self, real_analytics):
        """Dec 2014 (or nearby) must be among the highest revenue months."""
        result = real_analytics.get_trend_analysis()
        top_month = result.nlargest(1, "monthly_revenue").iloc[0]
        assert top_month["order_year"] == 2014
        assert top_month["order_month"] in [10, 11, 12]

    def test_no_null_revenue(self, real_analytics):
        """Monthly revenue must never be null."""
        result = real_analytics.get_trend_analysis()
        assert result["monthly_revenue"].notna().all()

    def test_revenue_sum_matches_total(self, real_analytics):
        """Sum of monthly revenue must match total dataset revenue."""
        result = real_analytics.get_trend_analysis()
        monthly_total = result["monthly_revenue"].sum()
        df_total = real_analytics.df["sales"].sum()
        assert abs(monthly_total - df_total) < 1.0, (
            f"Monthly sum {monthly_total} != df total {df_total}"
        )
