# Data & BI Analyst Interview Readiness Guide

This comprehensive guide is designed for preparing to present this project during technical and business interviews for **Data Analyst**, **Analytics Engineer**, and **BI Analyst** positions.

---

## 1. Project Pitch (30-Second Elevator Pitch)

> "In this project, I built an end-to-end Enterprise Sales & Profit Intelligence Platform using Python, DuckDB, SQL, and Streamlit. The objective was to diagnose the root causes of margin erosion in a multi-million-dollar retail business. By implementing a local-first medallion-style data pipeline, I discovered that while top-line revenue expanded to $2.3M, 18.7% of order lines were operating at a net loss—destroying over $156,000 in operating profit. Specifically, I uncovered a critical discount tipping point at 20%, beyond which 100% of transactions with discounts over 40% resulted in losses. I backed this up with a 13-test automated pytest suite, mathematical reconciliation down to the exact cent, and an interactive executive dashboard."

---

## 2. Technical Architecture & Design Decisions

### Q: Why did you choose DuckDB instead of SQLite, PostgreSQL, or Snowflake?
**Answer:**
- **Columnar Execution Engine:** DuckDB is purpose-built for analytical (OLAP) workloads. Because analytical queries involve aggregations over millions of rows (`SUM(sales)`, `AVG(discount)`, `GROUP BY region`) rather than individual row lookups (OLTP), DuckDB processes these vectorially with SIMD instructions, executing our complex analytical queries in under 15 milliseconds.
- **Native Parquet Integration:** DuckDB can directly query Parquet files on disk without preliminary loading, eliminating unnecessary memory duplication.
- **Zero-Cloud & Zero-Cost:** It runs embedded in-process within Python, requiring no external servers, database credentials, or paid cloud APIs, making the entire platform local-first and 100% reproducible for reviewers.

### Q: Why did you separate raw data from processed data?
**Answer:**
- Following modern data engineering best practices (Medallion architecture), raw data is treated as an immutable append-only layer.
- If a downstream transformation rule changes (e.g., updating discount bracket definitions or fiscal calendar rules), we can rerun the pipeline from the untouched raw CSV without corrupting or losing original transactional ground truth.

---

## 3. Data Cleaning & Engineering Decisions

### Q: How did you handle edge cases such as division by zero in profit margins?
**Answer:**
- In standard SQL or Python, `profit / sales` crashes or returns `NULL`/`Infinity` if revenue is zero or negative.
- In SQL, I used explicit defensive guards:
  ```sql
  CASE 
      WHEN SUM(sales) > 0 THEN ROUND((SUM(profit) / SUM(sales)) * 100, 2)
      ELSE 0.00 
  END AS profit_margin_pct
  ```
- In Python, I implemented a reusable `safe_divide(numerator, denominator, default=0.0)` utility that explicitly checks for `None`, `NaN`, `0`, and `np.isinf()`.

### Q: What data quality anomalies did you encounter, and how did you resolve them?
**Answer:**
- **Postal Code formatting:** In US datasets, zip codes in New England (like Boston or Vermont) begin with leading zeros, which spreadsheets or pandas often coerce into integers (e.g., `5401` instead of `05401`). I standardized these with `.str.zfill(5)` to preserve 5-digit geographic integrity.
- **Ship Date Validation:** I verified temporal consistency by asserting that `ship_date >= order_date`. 
- **Idempotency:** The pipeline utilizes idempotent Parquet overwrites and DuckDB `CREATE OR REPLACE` DDL, allowing anyone to re-run the pipeline multiple times without generating duplicate rows.

---

## 4. SQL Analytics & Metric Definitions

### Q: Walk me through your SQL logic for calculating Year-over-Year (YoY) revenue growth.
**Answer:**
- "I used window functions with `LAG()` partitioned across the temporal dimension:
  ```sql
  WITH monthly_sales AS (
      SELECT 
          order_year, order_month,
          SUM(sales) AS monthly_revenue
      FROM fact_sales
      GROUP BY order_year, order_month
  )
  SELECT 
      order_year, order_month, monthly_revenue,
      LAG(monthly_revenue, 12) OVER (ORDER BY order_year, order_month) AS py_same_month_revenue,
      ROUND(((monthly_revenue - LAG(monthly_revenue, 12) OVER (ORDER BY order_year, order_month)) 
             / LAG(monthly_revenue, 12) OVER (ORDER BY order_year, order_month)) * 100, 2) AS yoy_growth_pct
  FROM monthly_sales;
  ```
  By using a 12-period lag on sorted year-month aggregates, we accurately compare identical seasonal periods (e.g., Nov 2014 vs Nov 2013) while guarding against divide-by-zero on missing base periods."

### Q: How do you verify that your SQL queries and Python dashboard metrics match?
**Answer:**
- "I wrote a dedicated reconciliation script and automated pytest suite (`test_reconciliation.py`). It computes total revenue, total profit, and order counts in Python's `MetricsEngine` and executes an aggregate query against DuckDB's `fact_sales` and analytical marts. The test asserts that the delta between Python and DuckDB is less than $0.01. In our pipeline, it reconciled to $0.0000 across all $2,297,200.65 in revenue."

---

## 5. Core Business Findings & Strategic Intuition

### Q: What was your most surprising or actionable business discovery?
**Answer:**
- "The **Discount Tipping Point**. Many companies assume that offering higher discounts is a safe lever to drive sales volume. However, the data showed:
  - Transactions with 0% discount produced a healthy **29.5% profit margin** and generated $320,987 in profit.
  - Transactions between 21% and 40% discount operated at a **-15.3% margin**, with 90.2% of items losing money.
  - Transactions with discounts greater than 40% were **100% loss-making**, destroying $99,558.74 in cash.
- Furthermore, this was highly regional: states like Texas (average discount 37.2%) and Illinois (39.0%) generated cumulative losses exceeding -$38,000. Recommending a hard discount cap at 20% is an immediate, evidence-backed strategy to protect hundreds of thousands in operating profit."

### Q: Can you claim that high discounts caused customers to be unprofitable?
**Answer:**
- "As an analyst, I maintain rigor regarding correlation versus causation. The data demonstrates a strong empirical correlation between discounts > 20% and negative contribution margins. However, without marketing acquisition data, customer acquisition costs, or customer lifetime value (LTV) cohorts, we cannot prove whether discounts were uncoordinated margin destruction or deliberate loss-leader promotions to acquire high-value enterprise accounts. My recommendation is to audit whether deep-discount buyers ever make repeat purchases at full price before eliminating promotions entirely."

---

## 6. Interview Checklist & Demonstration Plan

1. **Architecture Walkthrough:** Show `README.md` Mermaid diagram explaining the local-first flow (Raw CSV -> Cleaning -> Parquet -> DuckDB -> SQL Marts -> Streamlit / Power BI).
2. **Quality Demonstration:** Run `python -m pytest tests -v` in real time to show all 13 automated tests passing.
3. **Interactive Demo:** Launch the Streamlit dashboard (`python -m streamlit run app/dashboard.py`) and demonstrate the dynamic filtering, discount tipping curve, and anomaly drilldown.
4. **Code Inspection:** Walk the interviewer through `src/metrics_engine.py` (safe division, zero guards) and `sql/02_trends_monthly_yoy.sql` (window functions).
