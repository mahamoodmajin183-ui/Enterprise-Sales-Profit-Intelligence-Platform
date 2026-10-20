-- ==============================================================================
-- Query 01: Executive KPI Summary
-- Purpose: Calculate enterprise-wide sales, profit, orders, and margins
-- Features: Explicit zero-denominator guard, distinct counts, average basket size
-- ==============================================================================

SELECT
    COUNT(DISTINCT order_id) AS total_orders,
    COUNT(DISTINCT customer_id) AS total_customers,
    COUNT(*) AS total_line_items,
    SUM(quantity) AS total_units_sold,
    ROUND(SUM(sales), 2) AS total_revenue_usd,
    ROUND(SUM(profit), 2) AS total_profit_usd,
    ROUND(SUM(estimated_cost), 2) AS total_cost_usd,
    -- Explicit zero-denominator safe margin calculation
    CASE 
        WHEN SUM(sales) > 0 THEN ROUND((SUM(profit) / SUM(sales)) * 100, 2)
        ELSE 0.00 
    END AS overall_profit_margin_pct,
    -- Average Order Value (AOV)
    CASE 
        WHEN COUNT(DISTINCT order_id) > 0 THEN ROUND(SUM(sales) / COUNT(DISTINCT order_id), 2)
        ELSE 0.00 
    END AS avg_order_value_usd,
    -- Average Profit Per Order
    CASE 
        WHEN COUNT(DISTINCT order_id) > 0 THEN ROUND(SUM(profit) / COUNT(DISTINCT order_id), 2)
        ELSE 0.00 
    END AS avg_profit_per_order_usd,
    -- Average Discount Granted
    ROUND(AVG(discount) * 100, 2) AS avg_discount_pct,
    -- Return Rate (% of orders returned)
    ROUND(COUNT(DISTINCT CASE WHEN is_returned THEN order_id END) * 100.0 / COUNT(DISTINCT order_id), 2) AS order_return_rate_pct
FROM fact_sales;
