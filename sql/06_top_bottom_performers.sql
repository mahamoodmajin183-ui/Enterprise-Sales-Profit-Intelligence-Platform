-- ==============================================================================
-- Query 06: Top & Bottom Performers (Products, Revenue, and Margin Traps)
-- Purpose: Isolate highest value drivers, top revenue earners, chronic loss leaders, and revenue traps
-- Features: Ranking window functions (ROW_NUMBER, DENSE_RANK), union of cohorts
-- ==============================================================================

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
        ROW_NUMBER() OVER (ORDER BY total_profit ASC) AS worst_loss_rank,
        ROW_NUMBER() OVER (ORDER BY total_revenue DESC) AS top_revenue_rank
    FROM product_stats
)
-- 1. Top 10 by Net Profit
SELECT 
    '1. Top 10 Profitable Product' AS cohort_type,
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

-- 2. Bottom 10 by Net Profit (Chronic Loss Leaders)
SELECT 
    '2. Bottom 10 Loss Leader' AS cohort_type,
    worst_loss_rank AS rank_position,
    product_name,
    category,
    sub_category,
    total_revenue,
    total_profit,
    profit_margin_pct
FROM ranked_products
WHERE worst_loss_rank <= 10

UNION ALL

-- 3. Top 10 by Gross Revenue
SELECT 
    '3. Top 10 Revenue Generator' AS cohort_type,
    top_revenue_rank AS rank_position,
    product_name,
    category,
    sub_category,
    total_revenue,
    total_profit,
    profit_margin_pct
FROM ranked_products
WHERE top_revenue_rank <= 10

UNION ALL

-- 4. High Revenue with Weak Profit Margin (Revenue >= $5,000 and Margin < 5%)
SELECT 
    '4. High Revenue Weak Margin (<5%)' AS cohort_type,
    ROW_NUMBER() OVER (ORDER BY total_revenue DESC) AS rank_position,
    product_name,
    category,
    sub_category,
    total_revenue,
    total_profit,
    profit_margin_pct
FROM ranked_products
WHERE total_revenue >= 5000.0 AND profit_margin_pct < 5.0

ORDER BY cohort_type ASC, rank_position ASC;
