-- ==============================================================================
-- Query 07: Anomaly and Outlier Investigation
-- Purpose: Identify severe operational margin drains requiring forensic review
-- Conditions: Loss exceeding $500, or deep discount (>40%) combined with loss
-- ==============================================================================

SELECT
    order_id,
    order_date_str,
    customer_name,
    segment,
    state,
    region,
    category,
    sub_category,
    product_name,
    quantity,
    ROUND(sales, 2) AS sales_usd,
    ROUND(discount * 100, 1) AS discount_pct,
    ROUND(profit, 2) AS profit_usd,
    ROUND(profit_margin * 100, 1) AS profit_margin_pct,
    CASE 
        WHEN profit <= -1000 THEN 'Critical Loss (> $1,000)'
        WHEN profit <= -500 THEN 'Severe Loss ($500 - $1,000)'
        WHEN discount >= 0.50 THEN 'Excessive Discount (>= 50%)'
        ELSE 'Negative Margin Outlier'
    END AS anomaly_classification
FROM fact_sales
WHERE profit <= -500 OR (discount >= 0.50 AND profit < -100)
ORDER BY profit ASC;
