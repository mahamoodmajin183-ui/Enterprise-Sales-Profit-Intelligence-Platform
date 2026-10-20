-- ==============================================================================
-- Query 09: Customer Concentration & Contribution Analysis
-- Purpose: Analyze customer buying behavior, customer lifetime value, and profitability tiers
-- Features: NTILE deciles, cumulative revenue contribution, order frequency
-- ==============================================================================

WITH customer_summary AS (
    SELECT
        customer_id,
        customer_name,
        segment,
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(quantity) AS total_units_bought,
        ROUND(SUM(sales), 2) AS lifetime_revenue_usd,
        ROUND(SUM(profit), 2) AS lifetime_profit_usd,
        CASE 
            WHEN SUM(sales) > 0 THEN ROUND((SUM(profit) / SUM(sales)) * 100, 2)
            ELSE 0.00 
        END AS lifetime_margin_pct,
        ROUND(AVG(discount) * 100, 2) AS avg_discount_received_pct,
        COUNT(CASE WHEN profit < 0 THEN 1 END) AS unprofitable_line_count,
        MIN(order_date) AS first_order_date,
        MAX(order_date) AS last_order_date
    FROM fact_sales
    GROUP BY customer_id, customer_name, segment
),
customer_ranked AS (
    SELECT
        *,
        NTILE(10) OVER (ORDER BY lifetime_revenue_usd DESC) AS revenue_decile,
        ROW_NUMBER() OVER (ORDER BY lifetime_profit_usd DESC) AS profit_rank,
        ROW_NUMBER() OVER (ORDER BY lifetime_profit_usd ASC) AS loss_rank
    FROM customer_summary
)
SELECT
    customer_id,
    customer_name,
    segment,
    total_orders,
    total_units_bought,
    lifetime_revenue_usd,
    lifetime_profit_usd,
    lifetime_margin_pct,
    avg_discount_received_pct,
    unprofitable_line_count,
    revenue_decile,
    CASE 
        WHEN lifetime_profit_usd >= 2000 THEN 'Platinum Contributor (> $2,000 Profit)'
        WHEN lifetime_profit_usd >= 1000 THEN 'Gold Contributor ($1,000 - $2,000)'
        WHEN lifetime_profit_usd >= 0 THEN 'Standard Profitable'
        ELSE 'Deficit Customer (Net Loss)'
    END AS customer_value_segment
FROM customer_ranked
ORDER BY lifetime_profit_usd DESC;
