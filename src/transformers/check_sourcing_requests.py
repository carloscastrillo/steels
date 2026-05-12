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
            FROM sourcing_requests
        """).fetchone()["total"]

        print(f"Total sourcing_requests: {total}")
        print("-" * 140)

        rows = conn.execute("""
            SELECT
                sr.id,
                sr.our_ref,
                c.name AS client_name,
                rs.product,
                rs.grade,
                rs.thickness_mm,
                rs.width_mm,
                rs.cw_min,
                rs.cw_max,
                sr.requested_tons,
                sr.missing_tons,
                sr.sheet_date,
                sr.status
            FROM sourcing_requests sr
            JOIN clients c ON c.id = sr.client_id
            JOIN request_specs rs ON rs.id = sr.request_spec_id
            ORDER BY sr.id
            LIMIT 20
        """).fetchall()

        for row in rows:
            print(dict(row))
            print("-" * 140)


if __name__ == "__main__":
    main()