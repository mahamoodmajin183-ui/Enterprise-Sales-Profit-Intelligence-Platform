"""DuckDB Analytical Warehouse Manager.

Manages the local DuckDB instance, sets up dimensional and fact tables/views,
executes analytical SQL queries, and verifies data reconciliation.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import duckdb
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import DATABASE_DIR, DUCKDB_DATABASE_FILE, PROCESSED_PARQUET_FILE, SQL_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class DuckDBWarehouse:
    """Manages local DuckDB analytical data warehouse."""

    def __init__(self, db_path: Optional[Path] = None, parquet_path: Optional[Path] = None):
        self.db_path = str(db_path or DUCKDB_DATABASE_FILE)
        self.parquet_path = str(parquet_path or PROCESSED_PARQUET_FILE).replace("\\", "/")
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Establish a connection to DuckDB."""
        return duckdb.connect(self.db_path)

    def initialize_warehouse(self, force_refresh: bool = True) -> None:
        """Create or refresh tables, dimensional views, and analytical marts."""
        logger.info(f"Initializing DuckDB warehouse at: {self.db_path}")
        con = self.get_connection()
        try:
            # 1. Base Fact Table (Ingested directly from cleaned Parquet for high performance)
            con.execute(f"""
                CREATE OR REPLACE TABLE fact_sales AS 
                SELECT * FROM read_parquet('{self.parquet_path}');
            """)

            # 2. Dimensional Views
            con.execute("""
                CREATE OR REPLACE VIEW dim_customers AS
                SELECT DISTINCT
                    customer_id,
                    customer_name,
                    segment
                FROM fact_sales;
            """)

            con.execute("""
                CREATE OR REPLACE VIEW dim_products AS
                SELECT DISTINCT
                    product_id,
                    category,
                    sub_category,
                    product_name
                FROM fact_sales;
            """)

            con.execute("""
                CREATE OR REPLACE VIEW dim_geography AS
                SELECT DISTINCT
                    postal_code,
                    city,
                    state,
                    region,
                    country
                FROM fact_sales;
            """)

            # 3. Analytical Marts
            # Monthly Performance Mart with YoY Lag
            con.execute("""
                CREATE OR REPLACE VIEW mart_monthly_performance AS
                WITH monthly_agg AS (
                    SELECT 
                        order_year,
                        order_month,
                        order_year_month,
                        COUNT(DISTINCT order_id) AS total_orders,
                        COUNT(DISTINCT customer_id) AS active_customers,
                        SUM(quantity) AS total_quantity,
                        ROUND(SUM(sales), 2) AS total_revenue,
                        ROUND(SUM(profit), 2) AS total_profit,
                        ROUND(AVG(discount) * 100, 2) AS avg_discount_pct,
                        CASE 
                            WHEN SUM(sales) > 0 THEN ROUND((SUM(profit) / SUM(sales)) * 100, 2) 
                            ELSE 0.0 
                        END AS profit_margin_pct
                    FROM fact_sales
                    GROUP BY order_year, order_month, order_year_month
                )
                SELECT 
                    m.*,
                    LAG(total_revenue, 12) OVER (ORDER BY order_year, order_month) AS py_same_month_revenue,
                    CASE 
                        WHEN LAG(total_revenue, 12) OVER (ORDER BY order_year, order_month) > 0 
                        THEN ROUND(((total_revenue - LAG(total_revenue, 12) OVER (ORDER BY order_year, order_month)) 
                             / LAG(total_revenue, 12) OVER (ORDER BY order_year, order_month)) * 100, 2)
                        ELSE NULL 
                    END AS yoy_revenue_growth_pct
                FROM monthly_agg m;
            """)

            # Category & Sub-Category Mart
            con.execute("""
                CREATE OR REPLACE VIEW mart_category_performance AS
                SELECT 
                    category,
                    sub_category,
                    COUNT(DISTINCT order_id) AS total_orders,
                    SUM(quantity) AS total_quantity,
                    ROUND(SUM(sales), 2) AS total_revenue,
                    ROUND(SUM(profit), 2) AS total_profit,
                    CASE 
                        WHEN SUM(sales) > 0 THEN ROUND((SUM(profit) / SUM(sales)) * 100, 2) 
                        ELSE 0.0 
                    END AS profit_margin_pct,
                    ROUND(AVG(discount) * 100, 2) AS avg_discount_pct,
                    COUNT(CASE WHEN profit < 0 THEN 1 END) AS loss_order_count,
                    ROUND(COUNT(CASE WHEN profit < 0 THEN 1 END) * 100.0 / COUNT(*), 2) AS loss_order_pct,
                    ROUND(SUM(CASE WHEN profit < 0 THEN profit ELSE 0 END), 2) AS total_loss_dollars
                FROM fact_sales
                GROUP BY category, sub_category;
            """)

            # Regional Mart
            con.execute("""
                CREATE OR REPLACE VIEW mart_regional_performance AS
                SELECT 
                    region,
                    state,
                    COUNT(DISTINCT order_id) AS total_orders,
                    COUNT(DISTINCT customer_id) AS unique_customers,
                    ROUND(SUM(sales), 2) AS total_revenue,
                    ROUND(SUM(profit), 2) AS total_profit,
                    CASE 
                        WHEN SUM(sales) > 0 THEN ROUND((SUM(profit) / SUM(sales)) * 100, 2) 
                        ELSE 0.0 
                    END AS profit_margin_pct,
                    ROUND(AVG(discount) * 100, 2) AS avg_discount_pct,
                    ROUND(COUNT(CASE WHEN is_returned THEN 1 END) * 100.0 / COUNT(DISTINCT order_id), 2) AS return_rate_pct
                FROM fact_sales
                GROUP BY region, state;
            """)

            # Discount Impact Mart
            con.execute("""
                CREATE OR REPLACE VIEW mart_discount_performance AS
                SELECT 
                    discount_bracket,
                    COUNT(*) AS line_item_count,
                    COUNT(DISTINCT order_id) AS total_orders,
                    ROUND(AVG(discount) * 100, 2) AS avg_discount_pct,
                    ROUND(SUM(sales), 2) AS total_revenue,
                    ROUND(SUM(profit), 2) AS total_profit,
                    CASE 
                        WHEN SUM(sales) > 0 THEN ROUND((SUM(profit) / SUM(sales)) * 100, 2) 
                        ELSE 0.0 
                    END AS profit_margin_pct,
                    COUNT(CASE WHEN profit < 0 THEN 1 END) AS loss_transaction_count,
                    ROUND(COUNT(CASE WHEN profit < 0 THEN 1 END) * 100.0 / COUNT(*), 2) AS loss_rate_pct,
                    ROUND(SUM(CASE WHEN profit < 0 THEN profit ELSE 0 END), 2) AS total_loss_dollars
                FROM fact_sales
                GROUP BY discount_bracket;
            """)

            # Customer Contribution Mart
            con.execute("""
                CREATE OR REPLACE VIEW mart_customer_performance AS
                SELECT 
                    customer_id,
                    customer_name,
                    segment,
                    COUNT(DISTINCT order_id) AS total_orders,
                    SUM(quantity) AS total_units_bought,
                    ROUND(SUM(sales), 2) AS total_revenue,
                    ROUND(SUM(profit), 2) AS total_profit,
                    CASE 
                        WHEN SUM(sales) > 0 THEN ROUND((SUM(profit) / SUM(sales)) * 100, 2) 
                        ELSE 0.0 
                    END AS profit_margin_pct,
                    ROUND(AVG(discount) * 100, 2) AS avg_discount_pct
                FROM fact_sales
                GROUP BY customer_id, customer_name, segment;
            """)

            logger.info("Successfully created all tables, dimensional views, and analytical marts in DuckDB.")
        finally:
            con.close()

    def export_marts(self, output_dir: Optional[Path] = None) -> Dict[str, str]:
        """Export analytical marts to CSV and Parquet files for BI dashboard consumption."""
        out_path = output_dir or (Path(self.db_path).parent.parent / "data" / "processed" / "marts")
        out_path.mkdir(parents=True, exist_ok=True)
        marts = [
            "mart_monthly_performance",
            "mart_category_performance",
            "mart_regional_performance",
            "mart_discount_performance",
            "mart_customer_performance",
        ]
        exported = {}
        con = self.get_connection()
        try:
            for mart in marts:
                df = con.execute(f"SELECT * FROM {mart}").df()
                csv_file = out_path / f"{mart}.csv"
                parquet_file = out_path / f"{mart}.parquet"
                df.to_csv(csv_file, index=False)
                df.to_parquet(parquet_file, index=False)
                exported[mart] = str(parquet_file)
                logger.info(f"Exported mart {mart} ({len(df)} rows) to {parquet_file}")
            return exported
        finally:
            con.close()

    def query(self, sql_query: str) -> pd.DataFrame:
        """Execute a SQL query and return results as a pandas DataFrame."""
        con = self.get_connection()
        try:
            return con.execute(sql_query).df()
        finally:
            con.close()

    def execute_script(self, script_path: Path) -> pd.DataFrame:
        """Read and execute an external .sql file."""
        if not script_path.exists():
            raise FileNotFoundError(f"SQL script not found: {script_path}")
        with open(script_path, "r", encoding="utf-8") as f:
            sql_content = f.read()
        return self.query(sql_content)


if __name__ == "__main__":
    warehouse = DuckDBWarehouse()
    warehouse.initialize_warehouse()
    summary = warehouse.query("SELECT COUNT(*) AS row_cnt, SUM(sales) AS total_rev, SUM(profit) AS total_prof FROM fact_sales")
    print("DuckDB Warehouse Verification:")
    print(summary)
