-- ==============================================================================
-- Query 04: Regional and State Sales Performance
-- Purpose: Benchmark regional markets and pinpoint geographic loss centers
-- Features: Regional contribution, state-level margin ranking, return rates
-- ==============================================================================

SELECT
    region,
    state,
    COUNT(DISTINCT order_id) AS total_orders,
    COUNT(DISTINCT customer_id) AS total_customers,
    SUM(quantity) AS units_sold,
    ROUND(SUM(sales), 2) AS total_revenue_usd,
    ROUND(SUM(profit), 2) AS total_profit_usd,
    CASE 
        WHEN SUM(sales) > 0 THEN ROUND((SUM(profit) / SUM(sales)) * 100, 2)
        ELSE 0.00 
    END AS profit_margin_pct,
    ROUND(AVG(discount) * 100, 2) AS avg_discount_pct,
    ROUND(COUNT(DISTINCT CASE WHEN is_returned THEN order_id END) * 100.0 / COUNT(DISTINCT order_id), 2) AS return_rate_pct,
    CASE 
        WHEN SUM(profit) < 0 THEN 'Loss Maker'
        WHEN (SUM(profit) / SUM(sales)) < 0.10 THEN 'Low Margin (<10%)'
        ELSE 'Healthy Margin (>=10%)'
    END AS performance_tier
FROM fact_sales
GROUP BY region, state
ORDER BY total_profit_usd ASC;
