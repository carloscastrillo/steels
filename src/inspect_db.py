from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def inspect_database() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")

        cursor = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
        """)

        tables = [row[0] for row in cursor.fetchall()]

    print("Tablas encontradas:")
    for table in tables:
        print(f"- {table}")


if __name__ == "__main__":
    inspect_database()