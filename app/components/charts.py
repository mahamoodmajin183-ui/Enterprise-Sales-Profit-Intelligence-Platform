"""High-performance Plotly Visualization Components for Streamlit Dashboard.

Applies modern dark-mode aesthetic, harmonious color palettes, custom hover
templates, and responsive layouts.
"""

from typing import Optional
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Visual Design Palette - Modern Clean SaaS Theme (Nova Analytics Style)
THEME = {
    "bg_color": "#F8FAFC",          # Ultra light canvas
    "paper_color": "#FFFFFF",       # Pure white card surface
    "text_color": "#0F172A",        # Deep navy/slate text
    "muted_text": "#64748B",        # Slate grey labels
    "grid_color": "#F1F5F9",        # Soft light divider lines
    "primary": "#4F46E5",           # Vibrant Indigo/Purple brand
    "secondary": "#818CF8",         # Soft Indigo
    "profit_green": "#10B981",      # Crisp Emerald
    "loss_red": "#EF4444",          # Crimson Rose
    "accent_gold": "#F59E0B",       # Vivid Amber
}


def create_monthly_trend_chart(df_monthly: pd.DataFrame) -> go.Figure:
    """Create dual-axis interactive time series for Revenue and Profit."""
    if df_monthly.empty:
        return go.Figure()

    fig = go.Figure()

    # Revenue Bar Chart
    fig.add_trace(
        go.Bar(
            x=df_monthly["order_year_month"],
            y=df_monthly["monthly_revenue"],
            name="Revenue ($)",
            marker=dict(
                color="rgba(56, 189, 248, 0.7)",
                line=dict(color="#38BDF8", width=1.5),
            ),
            hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.2f}<extra></extra>",
            yaxis="y1",
        )
    )

    # Profit Line Chart
    fig.add_trace(
        go.Scatter(
            x=df_monthly["order_year_month"],
            y=df_monthly["monthly_profit"],
            name="Operating Profit ($)",
            mode="lines+markers",
            line=dict(color="#10B981", width=3, shape="spline"),
            marker=dict(size=6, color="#10B981", symbol="circle"),
            hovertemplate="<b>%{x}</b><br>Profit: $%{y:,.2f}<extra></extra>",
            yaxis="y1",
        )
    )

    # Margin Percentage secondary trace
    fig.add_trace(
        go.Scatter(
            x=df_monthly["order_year_month"],
            y=df_monthly["profit_margin_pct"],
            name="Profit Margin (%)",
            mode="lines",
            line=dict(color="#FBBF24", width=2, dash="dot"),
            hovertemplate="<b>%{x}</b><br>Margin: %{y:.1f}%<extra></extra>",
            yaxis="y2",
        )
    )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=THEME["text_color"]),
        margin=dict(l=40, r=40, t=30, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            title="",
            showgrid=False,
            color=THEME["muted_text"],
            tickangle=-45,
        ),
        yaxis=dict(
            title="Amount (USD)",
            showgrid=True,
            gridcolor=THEME["grid_color"],
            color=THEME["muted_text"],
        ),
        yaxis2=dict(
            title="Margin (%)",
            overlaying="y",
            side="right",
            showgrid=False,
            color="#FBBF24",
            ticksuffix="%",
        ),
        hovermode="x unified",
    )
    return fig


def create_category_profitability_chart(df_category: pd.DataFrame) -> go.Figure:
    """Create a horizontal breakdown of Sub-Category Profitability and Revenue."""
    if df_category.empty:
        return go.Figure()

    df_sorted = df_category.sort_values("total_profit", ascending=True)

    colors = [THEME["profit_green"] if p >= 0 else THEME["loss_red"] for p in df_sorted["total_profit"]]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df_sorted["sub_category"],
            x=df_sorted["total_profit"],
            orientation="h",
            marker=dict(color=colors, line=dict(width=1, color="rgba(255,255,255,0.2)")),
            hovertemplate="<b>%{y}</b><br>Profit: $%{x:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=THEME["text_color"]),
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis=dict(
            title="Total Profit / Loss (USD)",
            showgrid=True,
            gridcolor=THEME["grid_color"],
            zeroline=True,
            zerolinecolor="#FFFFFF",
            zerolinewidth=1.5,
        ),
        yaxis=dict(title="", showgrid=False),
    )
    return fig


def create_discount_elasticity_chart(df_discount: pd.DataFrame) -> go.Figure:
    """Create discount bracket vs profit margin destruction visual."""
    if df_discount.empty:
        return go.Figure()

    fig = go.Figure()

    # Sales Volume Bar
    fig.add_trace(
        go.Bar(
            x=df_discount["discount_bracket"],
            y=df_discount["total_sales"],
            name="Revenue ($)",
            marker=dict(color="rgba(129, 140, 248, 0.6)"),
            hovertemplate="Sales: $%{y:,.2f}<extra></extra>",
            yaxis="y1",
        )
    )

    # Margin Line
    fig.add_trace(
        go.Scatter(
            x=df_discount["discount_bracket"],
            y=df_discount["profit_margin_pct"],
            name="Profit Margin (%)",
            mode="lines+markers",
            line=dict(color="#F43F5E", width=3),
            marker=dict(size=8, color="#F43F5E"),
            hovertemplate="Margin: %{y:.1f}%<extra></extra>",
            yaxis="y2",
        )
    )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=THEME["text_color"]),
        margin=dict(l=30, r=30, t=20, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="Discount Tier", showgrid=False),
        yaxis=dict(title="Revenue (USD)", showgrid=True, gridcolor=THEME["grid_color"]),
        yaxis2=dict(
            title="Margin (%)",
            overlaying="y",
            side="right",
            showgrid=False,
            color="#F43F5E",
            ticksuffix="%",
            zeroline=True,
            zerolinecolor="#F43F5E",
        ),
    )
    return fig


def create_anomaly_scatter(df_anomalies: pd.DataFrame) -> go.Figure:
    """Profit Z-score scatter: X=profit value, Y=Z-score, colour by anomaly reason."""
    if df_anomalies.empty:
        return go.Figure()

    colors = [
        THEME["loss_red"] if p < 0 else THEME["profit_green"]
        for p in df_anomalies["profit"]
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_anomalies["profit"],
            y=df_anomalies["profit_zscore"],
            mode="markers",
            marker=dict(
                color=colors,
                size=9,
                opacity=0.85,
                line=dict(color="rgba(255,255,255,0.2)", width=1),
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Profit: $%{x:,.2f}<br>"
                "Z-score: %{y:.2f}<br>"
                "Product: %{customdata[1]}<br>"
                "Reason: %{customdata[2]}"
                "<extra></extra>"
            ),
            customdata=df_anomalies[["order_id", "product_name", "anomaly_reason"]].values,
        )
    )

    # IQR fence reference lines
    if "iqr_lower_fence" in df_anomalies.columns:
        lower = df_anomalies["iqr_lower_fence"].iloc[0]
        upper = df_anomalies["iqr_upper_fence"].iloc[0]
        for fence, label in [(lower, "IQR Lower"), (upper, "IQR Upper")]:
            fig.add_vline(
                x=fence,
                line_dash="dash",
                line_color=THEME["accent_gold"],
                annotation_text=label,
                annotation_font_color=THEME["accent_gold"],
            )

    fig.add_hline(y=3.0, line_dash="dot", line_color="#F43F5E",
                  annotation_text="Z=+3", annotation_font_color="#F43F5E")
    fig.add_hline(y=-3.0, line_dash="dot", line_color="#F43F5E",
                  annotation_text="Z=-3", annotation_font_color="#F43F5E")

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=THEME["text_color"]),
        margin=dict(l=40, r=40, t=30, b=40),
        xaxis=dict(title="Transaction Profit (USD)", showgrid=True, gridcolor=THEME["grid_color"]),
        yaxis=dict(title="Z-Score", showgrid=True, gridcolor=THEME["grid_color"]),
        hovermode="closest",
    )
    return fig


def create_trend_signal_chart(df_trend: pd.DataFrame) -> go.Figure:
    """MoM change % timeline with trend signal annotation dots."""
    if df_trend.empty:
        return go.Figure()

    signal_colors = {
        "Accelerating growth": "#10B981",
        "Growth but decelerating": "#6EE7B7",
        "Stable": "#94A3B8",
        "Decline but recovering": "#FBBF24",
        "Accelerating decline": "#F43F5E",
        "Insufficient data": "#334155",
    }
    dot_colors = [signal_colors.get(s, "#94A3B8") for s in df_trend["trend_signal"]]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df_trend["order_year_month"],
            y=df_trend["monthly_revenue"],
            name="Revenue ($)",
            marker=dict(color="rgba(56,189,248,0.35)", line=dict(color="#38BDF8", width=1)),
            hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>",
            yaxis="y1",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_trend["order_year_month"],
            y=df_trend["rolling_3m_avg"],
            name="3m Rolling Avg",
            mode="lines",
            line=dict(color=THEME["accent_gold"], width=2.5, dash="dot"),
            hovertemplate="3m Avg: $%{y:,.0f}<extra></extra>",
            yaxis="y1",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_trend["order_year_month"],
            y=df_trend["mom_change_pct"],
            name="MoM Change (%)",
            mode="lines+markers",
            line=dict(color=THEME["secondary"], width=2),
            marker=dict(color=dot_colors, size=10),
            hovertemplate="<b>%{x}</b><br>MoM: %{y:.1f}%<br>Signal: %{customdata}<extra></extra>",
            customdata=df_trend["trend_signal"],
            yaxis="y2",
        )
    )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=THEME["text_color"]),
        margin=dict(l=40, r=40, t=30, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="", showgrid=False, tickangle=-45, color=THEME["muted_text"]),
        yaxis=dict(title="Revenue (USD)", showgrid=True, gridcolor=THEME["grid_color"]),
        yaxis2=dict(
            title="MoM Change (%)",
            overlaying="y",
            side="right",
            showgrid=False,
            color=THEME["secondary"],
            ticksuffix="%",
            zeroline=True,
            zerolinecolor="rgba(255,255,255,0.2)",
        ),
        hovermode="x unified",
    )
    return fig


def create_product_matrix_scatter(df_all_products: pd.DataFrame,
                                  revenue_threshold: float = 1000.0,
                                  margin_warning_pct: float = 10.0) -> go.Figure:
    """Scatter: Revenue vs Profit Margin, coloured by quadrant."""
    if df_all_products.empty:
        return go.Figure()

    df = df_all_products.copy()
    df = df[df["total_revenue"] > 0].dropna(subset=["profit_margin_pct"])

    def _quad(row):
        hr = row["total_revenue"] >= revenue_threshold
        hm = row["profit_margin_pct"] >= margin_warning_pct
        if hr and hm:
            return "Stars"
        if hr and not hm:
            return "Revenue Traps"
        if not hr and hm:
            return "Niche Gems"
        return "Laggards"

    df["quadrant"] = df.apply(_quad, axis=1)

    quad_colors = {
        "Stars": THEME["profit_green"],
        "Revenue Traps": "#F43F5E",
        "Niche Gems": THEME["primary"],
        "Laggards": THEME["muted_text"],
    }

    fig = go.Figure()
    for quad, color in quad_colors.items():
        sub = df[df["quadrant"] == quad]
        if sub.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=sub["total_revenue"],
                y=sub["profit_margin_pct"],
                mode="markers",
                name=quad,
                marker=dict(
                    color=color, size=9, opacity=0.8,
                    line=dict(color="rgba(255,255,255,0.15)", width=1)
                ),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Revenue: $%{x:,.0f}<br>"
                    "Margin: %{y:.1f}%<br>"
                    "Category: %{customdata[1]}"
                    "<extra>" + quad + "</extra>"
                ),
                customdata=sub[["product_name", "category"]].values,
            )
        )

    # Quadrant dividers
    fig.add_vline(x=revenue_threshold, line_dash="dash",
                  line_color="rgba(255,255,255,0.25)")
    fig.add_hline(y=margin_warning_pct, line_dash="dash",
                  line_color="rgba(255,255,255,0.25)")

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=THEME["text_color"]),
        margin=dict(l=40, r=40, t=30, b=40),
        xaxis=dict(title="Total Revenue (USD)", showgrid=True, gridcolor=THEME["grid_color"], type="log"),
        yaxis=dict(title="Profit Margin (%)", showgrid=True, gridcolor=THEME["grid_color"],
                   zeroline=True, zerolinecolor="#F43F5E"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="closest",
    )
    return fig


def create_seasonality_chart(df_seasonality: pd.DataFrame) -> go.Figure:
    """Bar chart of seasonal index by quarter with confidence bands."""
    if df_seasonality.empty:
        return go.Figure()

    colors = [
        THEME["profit_green"] if v >= 0 else THEME["loss_red"]
        for v in df_seasonality["mean_seasonal_index"]
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_seasonality["quarter_label"],
            y=df_seasonality["mean_seasonal_index"],
            error_y=dict(
                type="data",
                array=df_seasonality["std_seasonal_index"].fillna(0).tolist(),
                visible=True,
                color="rgba(255,255,255,0.4)",
            ),
            marker=dict(color=colors, line=dict(color="rgba(255,255,255,0.2)", width=1)),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Seasonal Index: %{y:+.1f}%<br>"
                "Std Dev: ±%{error_y.array:.1f}%"
                "<extra></extra>"
            ),
        )
    )

    fig.add_hline(y=0, line_color="rgba(255,255,255,0.3)", line_dash="dot")

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=THEME["text_color"]),
        margin=dict(l=40, r=40, t=30, b=40),
        xaxis=dict(title="Quarter", showgrid=False),
        yaxis=dict(
            title="Revenue Deviation from Annual Mean (%)",
            showgrid=True,
            gridcolor=THEME["grid_color"],
            ticksuffix="%",
        ),
        showlegend=False,
    )
    return fig


def create_regional_map(df_state: pd.DataFrame) -> go.Figure:
    """Create US State choropleth or horizontal bar breakdown for regional profit."""
    if df_state.empty:
        return go.Figure()

    df_top_bottom = pd.concat([
        df_state.head(8),  # Top 8
        df_state.tail(8)   # Bottom 8
    ]).drop_duplicates().sort_values("total_profit", ascending=True)

    colors = [THEME["profit_green"] if p >= 0 else THEME["loss_red"] for p in df_top_bottom["total_profit"]]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df_top_bottom["state"],
            x=df_top_bottom["total_profit"],
            orientation="h",
            marker=dict(color=colors),
            hovertemplate="<b>%{y}</b> (%{customdata})<br>Profit: $%{x:,.2f}<extra></extra>",
            customdata=df_top_bottom["region"],
        )
    )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=THEME["text_color"]),
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis=dict(
            title="Total Profit / Loss (USD)",
            showgrid=True,
            gridcolor=THEME["grid_color"],
            zeroline=True,
            zerolinecolor="#FFFFFF",
        ),
        yaxis=dict(title="", showgrid=False),
    )
    return fig
