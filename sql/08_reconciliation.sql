-- ==============================================================================
-- Query 08: End-to-End Data Reconciliation Audit
-- Purpose: Verify mathematical consistency between fact table and analytical marts
-- ==============================================================================

WITH base_totals AS (
    SELECT
        'Base Fact Table (fact_sales)' AS layer_name,
        COUNT(*) AS total_rows,
        COUNT(DISTINCT order_id) AS distinct_orders,
        COUNT(DISTINCT customer_id) AS distinct_customers,
        ROUND(SUM(sales), 2) AS total_revenue,
        ROUND(SUM(profit), 2) AS total_profit
    FROM fact_sales
),
monthly_mart_totals AS (
    SELECT
        'Mart: Monthly Performance' AS layer_name,
        NULL AS total_rows,
        SUM(total_orders) AS distinct_orders, -- note: orders summed across months
        NULL AS distinct_customers,
        ROUND(SUM(total_revenue), 2) AS total_revenue,
        ROUND(SUM(total_profit), 2) AS total_profit
    FROM mart_monthly_performance
),
category_mart_totals AS (
    SELECT
        'Mart: Category Performance' AS layer_name,
        NULL AS total_rows,
        NULL AS distinct_orders,
        NULL AS distinct_customers,
        ROUND(SUM(total_revenue), 2) AS total_revenue,
        ROUND(SUM(total_profit), 2) AS total_profit
    FROM mart_category_performance
),
discount_mart_totals AS (
    SELECT
        'Mart: Discount Performance' AS layer_name,
        SUM(line_item_count) AS total_rows,
        NULL AS distinct_orders,
        NULL AS distinct_customers,
        ROUND(SUM(total_revenue), 2) AS total_revenue,
        ROUND(SUM(total_profit), 2) AS total_profit
    FROM mart_discount_performance
)
SELECT * FROM base_totals
UNION ALL
SELECT * FROM monthly_mart_totals
UNION ALL
SELECT * FROM category_mart_totals
UNION ALL
SELECT * FROM discount_mart_totals;
