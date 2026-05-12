from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def column_exists(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    cursor = connection.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        if not column_exists(conn, "materials", "product_form_code"):
            conn.execute("ALTER TABLE materials ADD COLUMN product_form_code TEXT")
            print("Añadida columna: product_form_code")
        else:
            print("La columna product_form_code ya existe")

        if not column_exists(conn, "materials", "product_form_text"):
            conn.execute("ALTER TABLE materials ADD COLUMN product_form_text TEXT")
            print("Añadida columna: product_form_text")
        else:
            print("La columna product_form_text ya existe")

        conn.commit()

    print("Patch aplicado correctamente.")


if __name__ == "__main__":
    main()