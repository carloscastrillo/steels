from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT
                client_name,
                COUNT(*) AS total_rows
            FROM stg_boss_request_candidates
            WHERE match_status = 'no_client_match'
            GROUP BY client_name
            ORDER BY total_rows DESC, client_name
        """).fetchall()

        print("Clientes de Excel sin match en core:")
        for row in rows:
            print(f"- {row['client_name']}: {row['total_rows']}")


if __name__ == "__main__":
    main()