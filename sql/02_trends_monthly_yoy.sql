-- ==============================================================================
-- Query 02: Monthly and Year-Over-Year (YoY) Growth Trends
-- Purpose: Track monthly sales trajectory, profit margins, and YoY delta
-- Features: Window functions (LAG), seasonal analysis, margin tracking
-- ==============================================================================

WITH monthly_sales AS (
    SELECT
        order_year,
        order_month,
        order_year_month,
        COUNT(DISTINCT order_id) AS orders_count,
        SUM(quantity) AS units_sold,
        ROUND(SUM(sales), 2) AS monthly_revenue,
        ROUND(SUM(profit), 2) AS monthly_profit,
        CASE 
            WHEN SUM(sales) > 0 THEN ROUND((SUM(profit) / SUM(sales)) * 100, 2)
            ELSE 0.00 
        END AS profit_margin_pct
    FROM fact_sales
    GROUP BY order_year, order_month, order_year_month
),
monthly_with_lags AS (
    SELECT
        order_year,
        order_month,
        order_year_month,
        orders_count,
        units_sold,
        monthly_revenue,
        monthly_profit,
        profit_margin_pct,
        -- Prior Month Revenue
        LAG(monthly_revenue, 1) OVER (ORDER BY order_year, order_month) AS prev_month_revenue,
        -- Same Month Last Year (12 months lag for YoY)
        LAG(monthly_revenue, 12) OVER (ORDER BY order_year, order_month) AS py_same_month_revenue,
        LAG(monthly_profit, 12) OVER (ORDER BY order_year, order_month) AS py_same_month_profit
    FROM monthly_sales
)
SELECT
    order_year,
    order_month,
    order_year_month,
    orders_count,
    units_sold,
    monthly_revenue,
    monthly_profit,
    profit_margin_pct,
    -- Month-over-Month (MoM) Growth %
    CASE 
        WHEN prev_month_revenue > 0 THEN ROUND(((monthly_revenue - prev_month_revenue) / prev_month_revenue) * 100, 2)
        ELSE NULL 
    END AS mom_revenue_growth_pct,
    -- Year-over-Year (YoY) Growth %
    CASE 
        WHEN py_same_month_revenue > 0 THEN ROUND(((monthly_revenue - py_same_month_revenue) / py_same_month_revenue) * 100, 2)
        ELSE NULL 
    END AS yoy_revenue_growth_pct,
    -- YoY Profit Delta in USD
    ROUND(monthly_profit - COALESCE(py_same_month_profit, monthly_profit), 2) AS yoy_profit_delta_usd
FROM monthly_with_lags
ORDER BY order_year, order_month;
