from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import psycopg


ROOT = Path(__file__).parent
SQLITE_PATH = ROOT / "budget.db"


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("Set DATABASE_URL before running this migration.")
    if not SQLITE_PATH.exists():
        raise SystemExit(f"Local database not found: {SQLITE_PATH}")

    with psycopg.connect(database_url) as target, sqlite3.connect(SQLITE_PATH) as source:
        target.execute((ROOT / "schema.sql").read_text(encoding="utf-8"))
        for table in ("categories", "transactions", "budgets"):
            rows = source.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                continue
            if table == "categories":
                target.executemany(
                    "INSERT INTO categories(id, kind, name) VALUES (%s, %s, %s) ON CONFLICT(kind, name) DO NOTHING",
                    rows,
                )
            elif table == "transactions":
                target.executemany(
                    """INSERT INTO transactions(id, transaction_date, kind, category, subcategory, amount, note)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT(id) DO NOTHING""",
                    rows,
                )
            else:
                target.executemany(
                    """INSERT INTO budgets(id, scope, category, amount)
                    VALUES (%s, %s, %s, %s) ON CONFLICT(scope, category) DO UPDATE SET amount = EXCLUDED.amount""",
                    rows,
                )
        target.execute("SELECT setval(pg_get_serial_sequence('categories', 'id'), COALESCE(MAX(id), 1)) FROM categories")
        target.execute("SELECT setval(pg_get_serial_sequence('transactions', 'id'), COALESCE(MAX(id), 1)) FROM transactions")
        target.execute("SELECT setval(pg_get_serial_sequence('budgets', 'id'), COALESCE(MAX(id), 1)) FROM budgets")
    print("Migration complete.")


if __name__ == "__main__":
    main()
