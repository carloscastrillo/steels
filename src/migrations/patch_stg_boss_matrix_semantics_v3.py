from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


NEW_COLUMNS = [
    ("am_tons", "REAL"),
    ("luso_tons", "REAL"),
    ("import_tons", "REAL"),
    ("offer_14_total", "REAL"),
    ("offer_15_total", "REAL"),
    ("offer_16_total", "REAL"),
    ("offer_17_total", "REAL"),
]


def column_exists(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    cursor = connection.execute(f"PRAGMA table_info({table_name})")
    return column_name in [row[1] for row in cursor.fetchall()]


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        for column_name, column_type in NEW_COLUMNS:
            if column_exists(conn, "stg_boss_matrix", column_name):
                print(f"La columna {column_name} ya existe")
                continue

            conn.execute(
                f"ALTER TABLE stg_boss_matrix ADD COLUMN {column_name} {column_type}"
            )
            print(f"Añadida columna: {column_name} ({column_type})")

        conn.commit()

    print("Patch aplicado correctamente.")


if __name__ == "__main__":
    main()