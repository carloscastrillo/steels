from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        if not column_exists(conn, "supplier_options", "capability_allowed"):
            conn.execute("ALTER TABLE supplier_options ADD COLUMN capability_allowed INTEGER")
            print("Añadida columna: capability_allowed")
        else:
            print("La columna capability_allowed ya existe")

        if not column_exists(conn, "supplier_options", "capability_rule_id"):
            conn.execute("ALTER TABLE supplier_options ADD COLUMN capability_rule_id INTEGER")
            print("Añadida columna: capability_rule_id")
        else:
            print("La columna capability_rule_id ya existe")

        if not column_exists(conn, "supplier_options", "capability_note"):
            conn.execute("ALTER TABLE supplier_options ADD COLUMN capability_note TEXT")
            print("Añadida columna: capability_note")
        else:
            print("La columna capability_note ya existe")

        conn.commit()

    print("Patch aplicado correctamente.")


if __name__ == "__main__":
    main()