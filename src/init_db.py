from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"


def init_database() -> None:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"No existe el archivo de esquema: {SCHEMA_PATH}")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.executescript(schema_sql)
        connection.commit()

    print(f"Base de datos inicializada correctamente en: {DB_PATH}")


if __name__ == "__main__":
    init_database()