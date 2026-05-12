"""
utils/db.py
-----------
Utilidades compartidas de base de datos.

Elimina el patrón copy-paste de BASE_DIR / DB_PATH que existe en los 30+
scripts del proyecto. Importar desde aquí garantiza que todos apuntan al
mismo archivo y con los mismos PRAGMA.

Uso:
    from utils.db import get_db_path, connect, get_count

    with connect() as conn:
        count = get_count(conn, "sourcing_requests")
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Ruta raíz del proyecto (dos niveles arriba de src/utils/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH  = BASE_DIR / "db" / "steel_mvp.db"


def get_db_path() -> Path:
    """Devuelve la ruta absoluta a la base de datos."""
    return DB_PATH


def connect(check_exists: bool = True) -> sqlite3.Connection:
    """
    Abre y devuelve una conexión SQLite con:
      - row_factory = sqlite3.Row  (acceso por nombre de columna)
      - PRAGMA foreign_keys = ON
      - PRAGMA journal_mode = WAL  (mejor rendimiento en lecturas concurrentes)

    Uso recomendado con context manager:
        with connect() as conn:
            conn.execute(...)
    """
    if check_exists and not DB_PATH.exists():
        raise FileNotFoundError(
            f"No existe la base de datos: {DB_PATH}\n"
            "Ejecuta primero: python src/init_db.py"
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def get_count(conn: sqlite3.Connection, table: str) -> int:
    """
    Devuelve el número de filas de una tabla.
    Devuelve -1 si la tabla no existe.
    """
    try:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return -1


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Comprueba si una tabla existe en la base de datos."""
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    ).fetchone()
    return bool(row and row[0])


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Comprueba si una columna existe en una tabla."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def cascade_delete_boss_core(conn: sqlite3.Connection) -> None:
    """
    Borra en orden FK-safe todas las tablas core que dependen de stg_boss_matrix.
    Usar antes de re-importar el BOSS para garantizar idempotencia.

    Orden de borrado (inverso al de FK):
      sourcing_request_shortlist → supplier_options → sourcing_requests
      → request_specs → stg_boss_matrix
    """
    steps = [
        "sourcing_request_shortlist",
        "supplier_options",
        "sourcing_requests",
        "request_specs",
        "stg_boss_matrix",
    ]
    for table in steps:
        try:
            conn.execute(f"DELETE FROM {table}")
        except sqlite3.OperationalError:
            pass   # tabla aún no creada, ignorar
