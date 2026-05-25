from __future__ import annotations

from pathlib import Path
import os
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = Path(os.environ.get("STEEL_DB_PATH", BASE_DIR / "db" / "steel_mvp.db"))


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def run() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la DB: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        if column_exists(conn, "sourcing_request_shortlist", "best_source"):
            print("sourcing_request_shortlist.best_source ya existe.")
            return

        conn.execute("""
            ALTER TABLE sourcing_request_shortlist
            ADD COLUMN best_source TEXT DEFAULT 'BOSS'
        """)

        conn.commit()

    print("OK: columna best_source añadida a sourcing_request_shortlist.")


if __name__ == "__main__":
    run()
