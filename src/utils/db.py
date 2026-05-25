from __future__ import annotations

import os
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent


def resolve_db_path() -> Path:
    raw_path = Path(os.environ.get("STEEL_DB_PATH", BASE_DIR / "db" / "steel_mvp.db"))

    if raw_path.is_absolute():
        return raw_path

    return BASE_DIR / raw_path


DB_PATH = resolve_db_path()


def get_db_path() -> Path:
    return DB_PATH


def connect(row_factory: bool = True) -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    if row_factory:
        conn.row_factory = sqlite3.Row

    return conn
