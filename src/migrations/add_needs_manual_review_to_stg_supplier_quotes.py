"""
Migration: add_needs_manual_review_to_stg_supplier_quotes.py
Sprint: P2-2
Fecha: Mayo 2026

Contexto:
    stg_supplier_quotes ya usa review_status para controlar la revisión
    manual, pero para alinear staging con sourcing_quotes y con los criterios
    de aceptación de parsers de proveedor se añade needs_manual_review.

    Por defecto vale 1 porque toda quote autoextraída desde PDF debe revisarse.
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
        if column_exists(conn, "stg_supplier_quotes", "needs_manual_review"):
            print("stg_supplier_quotes.needs_manual_review ya existe.")
            return

        conn.execute("""
            ALTER TABLE stg_supplier_quotes
            ADD COLUMN needs_manual_review INTEGER DEFAULT 1
        """)
        conn.execute("""
            UPDATE stg_supplier_quotes
            SET needs_manual_review = 1
            WHERE needs_manual_review IS NULL
        """)
        conn.commit()

    print("Columna needs_manual_review añadida a stg_supplier_quotes.")


if __name__ == "__main__":
    run()