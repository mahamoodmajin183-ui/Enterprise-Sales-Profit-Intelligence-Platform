-- ==============================================================================
-- Query 06: Top & Bottom Performers (Products & Customers)
-- Purpose: Isolate highest value drivers vs chronic loss leaders
-- Features: Ranking window functions (DENSE_RANK), union of top/bottom
-- ==============================================================================

-- 1. Top 10 Most Profitable Products
WITH product_stats AS (
    SELECT
        product_id,
        product_name,
        category,
        sub_category,
        COUNT(DISTINCT order_id) AS orders_count,
        SUM(quantity) AS units_sold,
        ROUND(SUM(sales), 2) AS total_revenue,
        ROUND(SUM(profit), 2) AS total_profit,
        CASE 
            WHEN SUM(sales) > 0 THEN ROUND((SUM(profit) / SUM(sales)) * 100, 2)
            ELSE 0.00 
        END AS profit_margin_pct
    FROM fact_sales
    GROUP BY product_id, product_name, category, sub_category
),
ranked_products AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (ORDER BY total_profit DESC) AS top_profit_rank,
        ROW_NUMBER() OVER (ORDER BY total_profit ASC) AS worst_loss_rank
    FROM product_stats
)
SELECT 
    'Top 10 Profitable Product' AS cohort_type,
    top_profit_rank AS rank_position,
    product_name,
    category,
    sub_category,
    total_revenue,
    total_profit,
    profit_margin_pct
FROM ranked_products
WHERE top_profit_rank <= 10

UNION ALL

SELECT 
    'Bottom 10 Loss Leader' AS cohort_type,
    worst_loss_rank AS rank_position,
    product_name,
    category,
    sub_category,
    total_revenue,
    total_profit,
    profit_margin_pct
FROM ranked_products
WHERE worst_loss_rank <= 10
ORDER BY cohort_type DESC, rank_position ASC;
