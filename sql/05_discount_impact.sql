-- ==============================================================================
-- Query 05: Discount Elasticity & Profit Destruction Analysis
-- Purpose: Quantify how increasing discount tiers impact operating profit margins
-- Features: Bracketed discount tiers, loss probability, net contribution
-- ==============================================================================

SELECT
    discount_bracket,
    COUNT(*) AS total_transactions,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(AVG(discount) * 100, 2) AS avg_discount_given_pct,
    ROUND(SUM(sales), 2) AS total_sales_usd,
    ROUND(SUM(profit), 2) AS total_profit_usd,
    -- Safe Profit Margin
    CASE 
        WHEN SUM(sales) > 0 THEN ROUND((SUM(profit) / SUM(sales)) * 100, 2)
        ELSE 0.00 
    END AS profit_margin_pct,
    -- Unprofitable Transactions
    COUNT(CASE WHEN profit < 0 THEN 1 END) AS unprofitable_line_items,
    ROUND(COUNT(CASE WHEN profit < 0 THEN 1 END) * 100.0 / COUNT(*), 2) AS unprofitable_item_pct,
    ROUND(SUM(CASE WHEN profit < 0 THEN profit ELSE 0 END), 2) AS total_loss_dollars
FROM fact_sales
GROUP BY discount_bracket
ORDER BY avg_discount_given_pct ASC;
