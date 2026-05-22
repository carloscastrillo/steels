"""
Migration: add_coating_raw_to_stg_supplier_quotes.py
Sprint: 5 — Tarea 1.1

Añade coating_raw a stg_supplier_quotes para conservar la cabecera original
extraída desde PDFs de proveedor, especialmente en casos de cabeceras compuestas
como Galmed: Z120\\nZ70/50.
"""

from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in cols)


def run() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        if column_exists(conn, "stg_supplier_quotes", "coating_raw"):
            print("stg_supplier_quotes.coating_raw ya existe.")
            return

        conn.execute("""
            ALTER TABLE stg_supplier_quotes
            ADD COLUMN coating_raw TEXT
        """)
        conn.commit()

    print("OK: columna coating_raw añadida a stg_supplier_quotes.")


if __name__ == "__main__":
    run()