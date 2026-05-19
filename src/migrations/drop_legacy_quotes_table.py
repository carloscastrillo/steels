"""
Migration: drop_legacy_quotes_table.py
Sprint: 2 -> 3 (limpieza post-migración)
Fecha: Mayo 2026

Contexto:
    En el modelo pre-Sprint 2, el sistema operaba con la tabla legacy `quotes`.
    A partir de Sprint 2, el modelo migró a `sourcing_quotes` y
    `sourcing_decisions`, que son las tablas operativas actuales.

    Esta migración elimina la tabla legacy `quotes` si aún existe, para evitar
    confusión en el schema.

Estado:
    YA EJECUTADO sobre `db/steel_mvp.db`.
    Este script es de referencia histórica.
    Ejecutarlo de nuevo es idempotente por usar IF EXISTS.
"""

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def run() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DROP TABLE IF EXISTS quotes")
        conn.commit()

    print("Migration drop_legacy_quotes_table: OK (tabla 'quotes' eliminada o ya inexistente)")


if __name__ == "__main__":
    run()
