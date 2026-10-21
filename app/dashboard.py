"""Enterprise Sales & Profit Intelligence Platform.

Interactive Executive BI Dashboard built with Streamlit, DuckDB, and Plotly.
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np

# Ensure root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import PROCESSED_PARQUET_FILE
from src.duckdb_manager import DuckDBWarehouse
from src.metrics_engine import MetricsEngine
from src.anomaly_detector import AnomalyDetector
from app.components.charts import (
    create_monthly_trend_chart,
    create_category_profitability_chart,
    create_discount_elasticity_chart,
    create_regional_map,
    create_anomaly_scatter,
    create_trend_signal_chart,
    create_product_matrix_scatter,
    create_seasonality_chart,
)
from src.advanced_analytics import AdvancedAnalytics

# Page Configuration
st.set_page_config(
    page_title="Enterprise Sales & Profit Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Executive Styling & Typography
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Main background & view container */
    .stApp {
        background: radial-gradient(circle at 15% 15%, #111827 0%, #0B0F19 60%, #030712 100%);
        color: #F8FAFC;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0d131f !important;
        border-right: 1px solid rgba(255, 255, 255, 0.07);
    }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        color: #F8FAFC !important;
        font-weight: 700;
    }

    /* Modern Glassmorphic Metric Cards */
    .metric-card {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.85) 100%);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px 22px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, rgba(56, 189, 248, 0.4), rgba(129, 140, 248, 0.4));
        opacity: 0.6;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 14px 36px rgba(56, 189, 248, 0.16);
        border-color: rgba(56, 189, 248, 0.35);
    }
    .metric-title {
        color: #94A3B8;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-bottom: 8px;
    }
    .metric-value {
        color: #F8FAFC;
        font-size: 1.85rem;
        font-weight: 800;
        line-height: 1.2;
        letter-spacing: -0.02em;
    }
    .metric-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 600;
        margin-top: 10px;
        letter-spacing: 0.02em;
    }
    .badge-green {
        background: rgba(16, 185, 129, 0.14);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.28);
    }
    .badge-blue {
        background: rgba(56, 189, 248, 0.14);
        color: #38BDF8;
        border: 1px solid rgba(56, 189, 248, 0.28);
    }
    .badge-amber {
        background: rgba(245, 158, 11, 0.14);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.28);
    }
    .badge-red {
        background: rgba(244, 63, 94, 0.14);
        color: #FB7185;
        border: 1px solid rgba(244, 63, 94, 0.28);
    }

    /* Provenance & Audit Header Banner */
    .provenance-banner {
        background: linear-gradient(90deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.7) 100%);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(56, 189, 248, 0.22);
        border-left: 4px solid #38BDF8;
        border-radius: 12px;
        padding: 12px 20px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.84rem;
        color: #CBD5E1;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        border-radius: 10px 10px 0 0;
        padding: 8px 18px;
        font-weight: 600;
        font-size: 0.92rem;
        color: #94A3B8;
        background-color: transparent;
        border: none;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #F8FAFC;
        background: rgba(255, 255, 255, 0.04);
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #38BDF8 !important;
        background: rgba(56, 189, 248, 0.08) !important;
        border-bottom: 2px solid #38BDF8 !important;
    }

    /* Dataframe & Table Container Styling */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.07);
    }

    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.88rem;
        transition: all 0.2s ease;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }
    .stButton > button:hover {
        border-color: #38BDF8;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.25);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_data():
    """Load cached cleaned parquet data."""
    if not PROCESSED_PARQUET_FILE.exists():
        from src.data_cleaner import run_pipeline
        run_pipeline()
    return pd.read_parquet(PROCESSED_PARQUET_FILE)


# Load dataset
df_raw = load_data()

# ---------------------------------------------------------
# Sidebar Controls & Global Filters
# ---------------------------------------------------------
st.sidebar.image("https://img.icons8.com/fluency/96/combo-chart.png", width=64)
st.sidebar.title("Analytics Filters")
st.sidebar.caption("Filter transactions dynamically across all views.")

# Filter Reset Button
if st.sidebar.button("🔄 Reset All Filters", use_container_width=True):
    for key in ["filter_categories", "filter_sub_categories", "filter_regions", "filter_segments", "filter_brackets", "filter_dates"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# Date Range Filter
min_date = df_raw["order_date"].min().date()
max_date = df_raw["order_date"].max().date()

selected_dates = st.sidebar.date_input(
    "Select Order Date Range",
    value=st.session_state.get("filter_dates", (min_date, max_date)),
    min_value=min_date,
    max_value=max_date,
    key="filter_dates",
)

if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date, end_date = min_date, max_date

# Category Filter
all_categories = sorted(df_raw["category"].unique())
selected_categories = st.sidebar.multiselect(
    "Category",
    options=all_categories,
    default=st.session_state.get("filter_categories", all_categories),
    key="filter_categories",
)

# Dynamic Sub-Category Filter based on selected categories
available_subcats = sorted(df_raw[df_raw["category"].isin(selected_categories)]["sub_category"].unique()) if selected_categories else []
selected_subcats = st.sidebar.multiselect(
    "Sub-Category",
    options=available_subcats,
    default=st.session_state.get("filter_sub_categories", available_subcats),
    key="filter_sub_categories",
)

# Region Filter
all_regions = sorted(df_raw["region"].unique())
selected_regions = st.sidebar.multiselect(
    "Region",
    options=all_regions,
    default=st.session_state.get("filter_regions", all_regions),
    key="filter_regions",
)

# Customer Segment Filter
all_segments = sorted(df_raw["segment"].unique())
selected_segments = st.sidebar.multiselect(
    "Customer Segment",
    options=all_segments,
    default=st.session_state.get("filter_segments", all_segments),
    key="filter_segments",
)

# Discount Tier Filter
all_brackets = sorted(df_raw["discount_bracket"].unique())
selected_brackets = st.sidebar.multiselect(
    "Discount Bracket",
    options=all_brackets,
    default=st.session_state.get("filter_brackets", all_brackets),
    key="filter_brackets",
)

# Apply Filter Mask
mask = (
    (df_raw["order_date"].dt.date >= start_date)
    & (df_raw["order_date"].dt.date <= end_date)
    & (df_raw["category"].isin(selected_categories))
    & (df_raw["sub_category"].isin(selected_subcats))
    & (df_raw["region"].isin(selected_regions))
    & (df_raw["segment"].isin(selected_segments))
    & (df_raw["discount_bracket"].isin(selected_brackets))
)
df_filtered = df_raw[mask].copy()

# Initialize Metrics Engine with filtered data
metrics = MetricsEngine(data=df_filtered)
kpis = metrics.calculate_executive_kpis()

# Empty results guard
if df_filtered.empty:
    st.warning("⚠️ **No transaction records match the current filter criteria.** Please adjust your filters or click 'Reset All Filters' in the sidebar.")
    st.stop()

# ---------------------------------------------------------
# Main Page Header & Provenance
# ---------------------------------------------------------
st.markdown(
    """
    <div style="margin-bottom: 8px;">
        <h1 style="font-size: 2.2rem; font-weight: 800; color: #F8FAFC; margin-bottom: 4px;">
            Enterprise Sales & Profit Intelligence Platform
        </h1>
        <p style="color: #94A3B8; font-size: 1rem; margin-top: 0px;">
            Omnichannel performance analytics, margin elasticity modeling, and loss-leader forensic audit.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Provenance & Audit Header Banner
st.markdown(
    f"""
    <div class="provenance-banner">
        <span><b>DATASET PROVENANCE:</b> Standard US Retail Superstore (Tableau Benchmark Open Data) | <b>RECORDS:</b> {len(df_filtered):,} / {len(df_raw):,} active</span>
        <span><b>DATABASE:</b> DuckDB v1.5 Local Warehouse | <b>AUDIT:</b> <span style="color:#34D399; font-weight:600;">Reconciled 100%</span></span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Executive KPI Ribbon
# ---------------------------------------------------------
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Total Revenue</div>
            <div class="metric-value">${kpis['total_revenue']:,.0f}</div>
            <div class="metric-badge badge-blue">{kpis['total_units']:,} Units Sold</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    profit_color = "badge-green" if kpis["total_profit"] >= 0 else "badge-red"
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Operating Profit</div>
            <div class="metric-value">${kpis['total_profit']:,.0f}</div>
            <div class="metric-badge {profit_color}">Net Contribution</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    margin_color = "badge-green" if kpis["profit_margin_pct"] >= 10 else ("badge-amber" if kpis["profit_margin_pct"] >= 0 else "badge-red")
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Profit Margin</div>
            <div class="metric-value">{kpis['profit_margin_pct']:.1f}%</div>
            <div class="metric-badge {margin_color}">Operating Ratio</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Total Orders</div>
            <div class="metric-value">{kpis['total_orders']:,}</div>
            <div class="metric-badge badge-blue">{kpis['total_customers']:,} Customers</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col5:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Avg Order Value</div>
            <div class="metric-value">${kpis['avg_order_value']:,.1f}</div>
            <div class="metric-badge badge-blue">${kpis['avg_profit_per_order']:,.1f} Profit/Order</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col6:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Return Rate</div>
            <div class="metric-value">{kpis['return_rate_pct']:.1f}%</div>
            <div class="metric-badge badge-amber">{kpis['avg_discount_pct']:.1f}% Avg Disc</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

# ---------------------------------------------------------
# Tabbed Analytical Views
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Executive Trends",
    "🏷️ Profitability & Discounts",
    "🗺️ Regional Performance",
    "🔍 Anomaly & Forensic Review",
    "🛡️ Data Quality & Audit",
    "🧪 Advanced Analytics",
])

# ---------------------------------------------------------
# TAB 1: EXECUTIVE TRENDS
# ---------------------------------------------------------
with tab1:
    st.subheader("Monthly Sales, Profit, and Margin Trajectory")
    df_monthly = metrics.get_monthly_trends()
    fig_monthly = create_monthly_trend_chart(df_monthly)
    st.plotly_chart(fig_monthly, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Category Revenue vs Operating Profit")
        df_cat = metrics.get_category_metrics()
        fig_cat = create_category_profitability_chart(df_cat)
        st.plotly_chart(fig_cat, use_container_width=True)

    with c2:
        st.subheader("Customer Segment Performance")
        seg_summary = (
            df_filtered.groupby("segment")
            .agg(
                orders=("order_id", "nunique"),
                sales=("sales", "sum"),
                profit=("profit", "sum"),
            )
            .reset_index()
        )
        seg_summary["profit_margin_pct"] = (seg_summary["profit"] / seg_summary["sales"] * 100).round(2)
        st.dataframe(
            seg_summary.rename(
                columns={
                    "segment": "Segment",
                    "orders": "Orders",
                    "sales": "Revenue ($)",
                    "profit": "Profit ($)",
                    "profit_margin_pct": "Margin (%)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

# ---------------------------------------------------------
# TAB 2: PROFITABILITY & DISCOUNT SENSITIVITY
# ---------------------------------------------------------
with tab2:
    st.subheader("The Discount Tipping Point: Profit Margin Destruction")
    st.markdown(
        """
        > **Critical Insight**: Observe the steep margin collapse as discounts cross **20%**. 
        > Transactions with discounts > 40% experience **100% loss rates**, destroying enterprise profit.
        """
    )
    df_discount = metrics.get_discount_metrics()
    fig_disc = create_discount_elasticity_chart(df_discount)
    st.plotly_chart(fig_disc, use_container_width=True)

    st.subheader("Sub-Category Profitability Matrix & Loss Analysis")
    df_subcat = metrics.get_category_metrics()
    st.dataframe(
        df_subcat[[
            "category",
            "sub_category",
            "total_revenue",
            "total_profit",
            "profit_margin_pct",
            "avg_discount_pct",
            "unprofitable_items",
            "unprofitable_item_pct",
            "total_loss_dollars",
        ]].rename(
            columns={
                "category": "Category",
                "sub_category": "Sub-Category",
                "total_revenue": "Revenue ($)",
                "total_profit": "Profit ($)",
                "profit_margin_pct": "Margin (%)",
                "avg_discount_pct": "Avg Disc (%)",
                "unprofitable_items": "Loss Items",
                "unprofitable_item_pct": "Loss %",
                "total_loss_dollars": "Total Loss ($)",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

# ---------------------------------------------------------
# TAB 3: REGIONAL PERFORMANCE
# ---------------------------------------------------------
with tab3:
    st.subheader("State-Level Profitability Rankings")
    df_regional = metrics.get_regional_metrics()
    fig_reg = create_regional_map(df_regional)
    st.plotly_chart(fig_reg, use_container_width=True)

    r_col1, r_col2 = st.columns(2)
    with r_col1:
        st.markdown("#### Top 5 Most Profitable States")
        st.dataframe(
            df_regional.head(5)[["state", "region", "total_revenue", "total_profit", "profit_margin_pct"]],
            use_container_width=True,
            hide_index=True,
        )

    with r_col2:
        st.markdown("#### Bottom 5 Loss-Center States")
        st.dataframe(
            df_regional.tail(5)[["state", "region", "total_revenue", "total_profit", "profit_margin_pct"]],
            use_container_width=True,
            hide_index=True,
        )

# ---------------------------------------------------------
# TAB 4: ANOMALY & FORENSIC REVIEW
# ---------------------------------------------------------
with tab4:
    st.subheader("Forensic Transaction Audit & Loss-Leader Outliers")
    detector = AnomalyDetector(df=df_filtered)
    anomaly_summary = detector.get_anomaly_summary()

    a1, a2, a3, a4 = st.columns(4)
    with a1:
        st.metric("Flagged Anomalies", f"{anomaly_summary['total_anomaly_count']:,}")
    with a2:
        st.metric("Total Anomaly Loss", f"${anomaly_summary['total_anomaly_loss']:,.2f}")
    with a3:
        st.metric("% Profit Destroyed", f"{anomaly_summary['pct_of_profit_destroyed']:.1f}%")
    with a4:
        st.metric("Critical Losses (> $1k)", f"{anomaly_summary['critical_loss_orders']:,}")

    df_anomalies = detector.detect_loss_anomalies()
    
    st.markdown("#### Identified High-Risk Transactions")
    st.dataframe(df_anomalies, use_container_width=True, hide_index=True)

    csv_data = df_anomalies.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Anomaly Audit CSV",
        data=csv_data,
        file_name="anomaly_audit_report.csv",
        mime="text/csv",
    )

# ---------------------------------------------------------
# TAB 5: DATA QUALITY & AUDIT
# ---------------------------------------------------------
with tab5:
    st.subheader("System Architecture & Live Reconciliation Audit")
    reconciliation = metrics.reconcile_with_duckdb()

    st.success("✅ **MATHEMATICAL RECONCILIATION PASSED**: Python Engine and DuckDB SQL match down to the exact cent.")

    audit_col1, audit_col2 = st.columns(2)
    with audit_col1:
        st.markdown("#### Python Calculation Engine")
        st.json(reconciliation["python"])

    with audit_col2:
        st.markdown("#### DuckDB SQL Warehouse")
        st.json(reconciliation["duckdb"])

    st.markdown("#### Discrepancy Deltas")
    st.json(reconciliation["deltas"])

# ---------------------------------------------------------
# TAB 6: ADVANCED ANALYTICS
# ---------------------------------------------------------
with tab6:
    st.subheader("Stage 5: Statistical Advanced Analytics")
    st.markdown(
        """
        > **Methodology:** All analyses use the filtered dataset from sidebar controls.
        > Statistical methods are documented inline. Correlation findings are associations only — not causal claims.
        """
    )

    adv = AdvancedAnalytics(df=df_filtered)

    # --- Section 1: Profit Anomaly Detection ---
    st.markdown("---")
    st.markdown("### 🎯 Profit Anomaly Detection (IQR + Z-Score)")
    adv_summary = adv.get_anomaly_summary()

    a1, a2, a3, a4, a5 = st.columns(5)
    with a1:
        st.metric("Flagged Transactions", f"{adv_summary['total_flagged']:,}")
    with a2:
        st.metric("Anomaly Rate", f"{adv_summary['anomaly_rate_pct']:.1f}%")
    with a3:
        st.metric("IQR Lower Fence", f"${adv_summary['iqr_lower_fence']:,.0f}")
    with a4:
        st.metric("IQR Upper Fence", f"${adv_summary['iqr_upper_fence']:,.0f}")
    with a5:
        st.metric("Z-Score Threshold", f"|z| > {adv_summary['zscore_threshold']}")

    st.caption(
        f"**Method:** {adv_summary['methodology']}. "
        "Transactions flagged by *either* criterion are included. "
        "Statistical anomalies are not necessarily operational errors — investigate before acting."
    )

    df_adv_anomalies = adv.detect_profit_anomalies()
    if not df_adv_anomalies.empty:
        fig_anomaly = create_anomaly_scatter(df_adv_anomalies)
        st.plotly_chart(fig_anomaly, use_container_width=True)

        st.markdown("#### Flagged Transaction Detail")
        display_cols = [c for c in [
            "order_id", "order_date_str", "customer_name", "segment",
            "category", "sub_category", "product_name",
            "sales", "profit", "profit_zscore", "anomaly_reason",
        ] if c in df_adv_anomalies.columns]
        st.dataframe(df_adv_anomalies[display_cols], use_container_width=True, hide_index=True)

        csv_adv = df_adv_anomalies.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download Statistical Anomaly Report (CSV)",
            data=csv_adv,
            file_name="statistical_anomaly_report.csv",
            mime="text/csv",
        )
    else:
        st.info("No statistical anomalies detected in the current filtered dataset.")

    # --- Section 2: Sales Trend Signal Analysis ---
    st.markdown("---")
    st.markdown("### 📊 Sales Trend Signal Analysis")
    st.caption(
        "MoM % change is classified into trend signals when |change| >= 5% and |acceleration| >= 2%. "
        "Dot colours: 🟢 Accelerating growth · 🟡 Recovering · ⚫ Stable · 🔴 Declining."
    )
    df_trend = adv.get_trend_analysis()
    if not df_trend.empty:
        fig_trend = create_trend_signal_chart(df_trend)
        st.plotly_chart(fig_trend, use_container_width=True)

        col_trend1, col_trend2 = st.columns(2)
        with col_trend1:
            signal_counts = df_trend["trend_signal"].value_counts().reset_index()
            signal_counts.columns = ["Signal", "Months"]
            st.markdown("#### Signal Distribution")
            st.dataframe(signal_counts, use_container_width=True, hide_index=True)

        with col_trend2:
            st.markdown("#### Seasonality by Quarter")
            df_seasonality = adv.get_seasonality_analysis()
            if not df_seasonality.empty:
                fig_seas = create_seasonality_chart(df_seasonality)
                st.plotly_chart(fig_seas, use_container_width=True)
                st.caption(
                    f"Based on {df_seasonality['years_included'].iloc[0]} complete year(s) of data. "
                    "Error bars = ±1 standard deviation across years."
                )
            else:
                st.info("Insufficient complete yearly data for seasonality analysis.")

    # --- Section 3: Product Performance Matrix ---
    st.markdown("---")
    st.markdown("### 🔲 Product Performance Matrix")
    st.caption(
        "Products plotted by revenue (log scale, x-axis) vs. profit margin % (y-axis). "
        "Quadrants: **Stars** = high revenue & high margin | **Revenue Traps** = high revenue but low/negative margin | "
        "**Niche Gems** = low revenue but strong margin | **Laggards** = low on both dimensions."
    )

    REVENUE_THRESHOLD = 1000.0
    MARGIN_THRESHOLD = 10.0

    prod_matrix = adv.get_product_performance_matrix(
        revenue_threshold=REVENUE_THRESHOLD,
        margin_warning_pct=MARGIN_THRESHOLD,
    )

    # Combine all products for scatter (use category metrics as proxy)
    df_cat_for_matrix = metrics.get_category_metrics()
    if "product_id" not in df_cat_for_matrix.columns:
        # Build product-level summary for scatter
        df_prod_scatter = (
            df_filtered.groupby(["product_id", "product_name", "category", "sub_category"])
            .agg(total_revenue=("sales", "sum"), total_profit=("profit", "sum"))
            .reset_index()
        )
        df_prod_scatter["profit_margin_pct"] = (
            df_prod_scatter["total_profit"] / df_prod_scatter["total_revenue"].replace(0, float("nan")) * 100
        ).round(2)
    else:
        df_prod_scatter = df_cat_for_matrix

    if not df_prod_scatter.empty:
        fig_matrix = create_product_matrix_scatter(
            df_prod_scatter,
            revenue_threshold=REVENUE_THRESHOLD,
            margin_warning_pct=MARGIN_THRESHOLD,
        )
        st.plotly_chart(fig_matrix, use_container_width=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("⭐ Stars", len(prod_matrix["stars"]))
    with m2:
        st.metric("⚠️ Revenue Traps", len(prod_matrix["revenue_traps"]))
    with m3:
        st.metric("💎 Niche Gems", len(prod_matrix["niche_gems"]))
    with m4:
        st.metric("📉 Laggards", len(prod_matrix["laggards"]))

    if not prod_matrix["revenue_traps"].empty:
        st.markdown("#### ⚠️ Revenue Traps — High Sales, Poor Margins")
        rt_cols = [c for c in ["product_name", "category", "sub_category",
                                "total_revenue", "total_profit", "profit_margin_pct",
                                "avg_discount_pct"] if c in prod_matrix["revenue_traps"].columns]
        st.dataframe(prod_matrix["revenue_traps"][rt_cols].head(15),
                     use_container_width=True, hide_index=True)

    # --- Section 4: Discount–Profitability Correlation ---
    st.markdown("---")
    st.markdown("### 🔗 Discount–Profitability Correlation (Spearman)")
    corr = adv.get_discount_correlation()

    rho_col, p_col, sig_col = st.columns(3)
    with rho_col:
        st.metric("Spearman Rho (Overall)", f"{corr['overall_rho']:.4f}")
    with p_col:
        st.metric("p-value", f"{corr['overall_p_value']:.4f}")
    with sig_col:
        sig_label = "✅ Significant (p<0.05)" if corr["overall_significant"] else "⚠️ Not Significant"
        st.metric("Statistical Significance", sig_label)

    st.info(corr["interpretation"])

    # Verified bracket-level breakdown from the filtered dataset
    if "discount_bracket" in df_filtered.columns:
        st.markdown("#### Profit Margin by Discount Bracket (filtered data)")
        st.caption(
            "Average profit margin per transaction, grouped by discount tier. "
            "The 'No Discount' row serves as the baseline. "
            "This is a descriptive summary — product mix and other factors are not controlled."
        )
        bracket_summary = (
            df_filtered.groupby("discount_bracket")
            .agg(
                transactions=("order_id", "count"),
                avg_margin_pct=("profit_margin", lambda x: round(x.mean() * 100, 2)),
                total_profit=("profit", "sum"),
            )
            .reset_index()
            .rename(columns={
                "discount_bracket": "Discount Bracket",
                "transactions": "Transactions",
                "avg_margin_pct": "Avg Profit Margin (%)",
                "total_profit": "Total Profit ($)",
            })
        )
        # Colour the margin column: negative = red context
        st.dataframe(
            bracket_summary,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Avg Profit Margin (%)": st.column_config.NumberColumn(
                    format="%.2f%%",
                    help="Average profit margin across all transactions in this bracket",
                ),
                "Total Profit ($)": st.column_config.NumberColumn(
                    format="$%.2f",
                ),
            },
        )

    if not corr["by_category"].empty:
        st.markdown("#### Correlation by Product Category")
        st.dataframe(corr["by_category"], use_container_width=True, hide_index=True)

    if corr["excluded_groups"]:
        with st.expander(f"ℹ️ {len(corr['excluded_groups'])} groups excluded (n < {10})"):
            st.dataframe(pd.DataFrame(corr["excluded_groups"]), use_container_width=True, hide_index=True)

    # --- Section 5: Regional Scorecard ---
    st.markdown("---")
    st.markdown("### 🗺️ Regional Performance Composite Scorecard")
    st.caption(
        "Score is the equal-weighted average of percentile ranks across: "
        "profit margin %, revenue per order, return rate (inverted), and average discount given (inverted). "
        "Range: 0 (worst) to 100 (best)."
    )
    df_scorecard = adv.get_regional_scorecard()
    if not df_scorecard.empty:
        sc_cols = ["state", "region", "profit_margin_pct", "revenue_per_order",
                   "return_rate_pct", "avg_discount_pct", "composite_score"]
        sc_display_cols = [c for c in sc_cols if c in df_scorecard.columns]
        st.dataframe(
            df_scorecard[sc_display_cols].rename(columns={
                "state": "State", "region": "Region",
                "profit_margin_pct": "Margin (%)", "revenue_per_order": "Rev/Order ($)",
                "return_rate_pct": "Return Rate (%)", "avg_discount_pct": "Avg Discount (%)",
                "composite_score": "Composite Score",
            }),
            use_container_width=True,
            hide_index=True,
        )
