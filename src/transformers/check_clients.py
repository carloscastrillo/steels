from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        total = conn.execute("""
            SELECT COUNT(*) AS total
            FROM clients
        """).fetchone()["total"]

        print(f"Total clients: {total}")
        print("-" * 100)

        rows = conn.execute("""
            SELECT id, name, sap_code, notes, created_at
            FROM clients
            ORDER BY name
            LIMIT 20
        """).fetchall()

        for row in rows:
            print(dict(row))


if __name__ == "__main__":
    main()