-- ==============================================================================
-- Query 03: Category and Sub-Category Profitability Analysis
-- Purpose: Evaluate category contribution, identify loss-making lines
-- Features: Margin calculation, loss-order count, average discount rate
-- ==============================================================================

SELECT
    category,
    sub_category,
    COUNT(DISTINCT order_id) AS total_orders,
    SUM(quantity) AS units_sold,
    ROUND(SUM(sales), 2) AS total_revenue_usd,
    ROUND(SUM(sales) * 100.0 / SUM(SUM(sales)) OVER (), 2) AS revenue_share_pct,
    ROUND(SUM(profit), 2) AS total_profit_usd,
    -- Safe Profit Margin
    CASE 
        WHEN SUM(sales) > 0 THEN ROUND((SUM(profit) / SUM(sales)) * 100, 2)
        ELSE 0.00 
    END AS profit_margin_pct,
    ROUND(AVG(discount) * 100, 2) AS avg_discount_pct,
    -- Loss Transaction Analysis
    COUNT(CASE WHEN profit < 0 THEN 1 END) AS unprofitable_line_items,
    ROUND(COUNT(CASE WHEN profit < 0 THEN 1 END) * 100.0 / COUNT(*), 2) AS unprofitable_item_pct,
    ROUND(SUM(CASE WHEN profit < 0 THEN profit ELSE 0 END), 2) AS total_loss_incurred_usd
FROM fact_sales
GROUP BY category, sub_category
ORDER BY total_profit_usd DESC;
