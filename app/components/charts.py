"""High-performance Plotly Visualization Components for Streamlit Dashboard.

Applies modern dark-mode aesthetic, harmonious color palettes, custom hover
templates, and responsive layouts.
"""

from typing import Optional
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Visual Design Palette
THEME = {
    "bg_color": "#0F172A",          # Deep slate background
    "paper_color": "#1E293B",       # Card background
    "text_color": "#F8FAFC",        # Crisp white
    "muted_text": "#94A3B8",        # Slate grey
    "grid_color": "#334155",        # Subtle gridlines
    "primary": "#38BDF8",           # Cyan blue
    "secondary": "#818CF8",         # Indigo
    "profit_green": "#10B981",      # Emerald
    "loss_red": "#F43F5E",          # Rose red
    "accent_gold": "#FBBF24",       # Amber gold
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
        template="plotly_dark",
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
        template="plotly_dark",
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
        template="plotly_dark",
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
        template="plotly_dark",
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
