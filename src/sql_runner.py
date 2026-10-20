"""SQL Analytics Runner.

Executes all analytical SQL scripts against the DuckDB warehouse,
validating syntax, execution speed, and printing tabular summaries.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import SQL_DIR
from src.duckdb_manager import DuckDBWarehouse


def run_all_queries() -> None:
    """Execute each SQL query file and display results."""
    warehouse = DuckDBWarehouse()
    warehouse.initialize_warehouse()

    sql_files = sorted(SQL_DIR.glob("*.sql"))
    print(f"\nDiscovered {len(sql_files)} SQL query files to execute:")

    for sql_file in sql_files:
        print("\n" + "=" * 80)
        print(f"EXECUTING: {sql_file.name}")
        print("=" * 80)
        df_result = warehouse.execute_script(sql_file)
        print(f"Row count: {len(df_result)}")
        print(df_result.head(10).to_string(index=False))


if __name__ == "__main__":
    run_all_queries()
