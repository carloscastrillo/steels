from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        summary = conn.execute("""
            SELECT match_status, COUNT(*) AS total
            FROM stg_boss_request_candidates
            GROUP BY match_status
            ORDER BY total DESC
        """).fetchall()

        print("Resumen por match_status:")
        for row in summary:
            print(f"- {row['match_status']}: {row['total']}")

        print("-" * 120)

        rows = conn.execute("""
            SELECT
                id,
                our_ref,
                client_name,
                product,
                grade,
                thickness_mm,
                width_mm,
                tn,
                matched_material_count,
                matched_material_id,
                match_status
            FROM stg_boss_request_candidates
            ORDER BY id
            LIMIT 20
        """).fetchall()

        for row in rows:
            print(dict(row))
            print("-" * 120)


if __name__ == "__main__":
    main()