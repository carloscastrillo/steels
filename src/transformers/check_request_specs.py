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
            FROM request_specs
        """).fetchone()["total"]

        print(f"Total request_specs: {total}")
        print("-" * 120)

        rows = conn.execute("""
            SELECT
                id,
                product,
                grade,
                thickness_mm,
                width_mm,
                thickness_tolerance_text,
                width_tolerance_text,
                cw_min,
                cw_max,
                spec_key
            FROM request_specs
            ORDER BY product, grade, thickness_mm, width_mm
            LIMIT 20
        """).fetchall()

        for row in rows:
            print(dict(row))
            print("-" * 120)


if __name__ == "__main__":
    main()