"""
Migration: drop_legacy_sprint1_tables.py
Sprint: 4 (limpieza post-Sprint 2)
Fecha: Mayo 2026

Contexto:
    El modelo de datos original definía las tablas:
      - requests    (sustituida por sourcing_requests)
      - decisions   (sustituida por sourcing_decisions)
      - providers   (no usada operativamente)
      - documents   (sustituida por stg_supplier_documents)

    Todas tienen 0 filas. La tabla `quotes` ya fue eliminada mediante
    drop_legacy_quotes_table.py.

    Esta migración elimina las tablas legacy restantes para evitar ambigüedad
    entre el modelo antiguo y el modelo operativo actual.

Idempotente:
    Sí. Usa DROP TABLE IF EXISTS.

Seguridad:
    Antes de ejecutar los DROP, verifica que las tablas estén vacías.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"

TABLES_TO_DROP = [
    "decisions",
    "requests",
    "providers",
    "documents",
]


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return bool(row and row[0])


def get_count(conn: sqlite3.Connection, table_name: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def run(dry_run: bool = False) -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la DB: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")

        blocking_errors = []

        for table in TABLES_TO_DROP:
            if not table_exists(conn, table):
                print(f"WARN: tabla '{table}' no existe. Se omitirá.")
                continue

            count = get_count(conn, table)
            print(f"CHECK: tabla '{table}' tiene {count} filas")

            if count > 0:
                blocking_errors.append(
                    f"ABORT: tabla '{table}' tiene {count} filas. No se eliminará."
                )

        if blocking_errors:
            print()
            for error in blocking_errors:
                print(error)
            print()
            print("No se ha ejecutado ningún DROP.")
            return

        print()

        for table in TABLES_TO_DROP:
            sql = f"DROP TABLE IF EXISTS {table}"

            if dry_run:
                print(f"[DRY RUN] {sql}")
            else:
                conn.execute(sql)
                print(f"OK: tabla '{table}' eliminada o ya inexistente")

        if not dry_run:
            conn.commit()
            print()
            print("Migration drop_legacy_sprint1_tables: completada.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar SQL sin ejecutar cambios",
    )
    args = parser.parse_args()

    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()