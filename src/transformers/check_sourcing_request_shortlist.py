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
            FROM sourcing_request_shortlist
        """).fetchone()["total"]

        print(f"Total shortlists: {total}")
        print("-" * 160)

        rows = conn.execute("""
            SELECT
                srs.sourcing_request_id,
                sr.our_ref,
                c.name AS client_name,
                rs.product,
                rs.grade,
                rs.thickness_mm,
                rs.width_mm,
                sr.requested_tons,
                srs.best_option_code,
                srs.best_supplier_name,
                srs.best_unit_cost,
                srs.best_total_cost,
                srs.second_option_code,
                srs.second_unit_cost,
                srs.third_option_code,
                srs.third_unit_cost,
                srs.am_spot_unit_cost,
                srs.delta_best_vs_am_spot,
                srs.savings_total_vs_am_spot
            FROM sourcing_request_shortlist srs
            JOIN sourcing_requests sr ON sr.id = srs.sourcing_request_id
            JOIN clients c ON c.id = sr.client_id
            JOIN request_specs rs ON rs.id = sr.request_spec_id
            ORDER BY srs.sourcing_request_id
            LIMIT 15
        """).fetchall()

        for row in rows:
            print(dict(row))
            print("-" * 160)


if __name__ == "__main__":
    main()