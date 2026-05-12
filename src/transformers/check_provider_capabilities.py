from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        total = conn.execute("""
            SELECT COUNT(*) AS total
            FROM provider_capabilities
        """).fetchone()["total"]

        print(f"Total provider_capabilities: {total}")
        print("-" * 120)

        rows = conn.execute("""
            SELECT
                id,
                provider_code,
                provider_name,
                product,
                grade_pattern,
                min_thickness_mm,
                max_thickness_mm,
                min_width_mm,
                max_width_mm,
                is_active,
                notes
            FROM provider_capabilities
            ORDER BY provider_code, product
        """).fetchall()

        for row in rows:
            print(dict(row))


if __name__ == "__main__":
    main()