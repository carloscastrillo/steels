from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


NEW_COLUMNS = [
    ("is_available", "INTEGER"),
    ("is_zero_placeholder", "INTEGER"),
    ("is_suspicious", "INTEGER"),
    ("is_rankable", "INTEGER"),
    ("validation_note", "TEXT"),
]


def column_exists(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    cursor = connection.execute(f"PRAGMA table_info({table_name})")
    return column_name in [row[1] for row in cursor.fetchall()]


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        for column_name, column_type in NEW_COLUMNS:
            if column_exists(conn, "supplier_options", column_name):
                print(f"La columna {column_name} ya existe")
                continue

            conn.execute(
                f"ALTER TABLE supplier_options ADD COLUMN {column_name} {column_type}"
            )
            print(f"Añadida columna: {column_name} ({column_type})")

        conn.commit()

    print("Patch aplicado correctamente.")


if __name__ == "__main__":
    main()