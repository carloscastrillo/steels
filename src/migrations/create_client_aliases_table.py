from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    sql = """
    CREATE TABLE IF NOT EXISTS client_aliases (
        id INTEGER PRIMARY KEY,
        alias_name TEXT NOT NULL UNIQUE,
        client_id INTEGER NOT NULL,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    );
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(sql)
        conn.commit()

    print("Tabla client_aliases creada correctamente.")


if __name__ == "__main__":
    main()
    