from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        req = conn.execute("""
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
                sr.status,
                sr.notes
            FROM sourcing_requests sr
            JOIN clients c ON c.id = sr.client_id
            JOIN request_specs rs ON rs.id = sr.request_spec_id
            ORDER BY sr.id DESC
            LIMIT 1
        """).fetchone()

        if not req:
            print("No hay sourcing_requests.")
            return

        print("ULTIMA SOURCING_REQUEST")
        print("-" * 120)
        print(dict(req))
        print("-" * 120)

        options = conn.execute("""
            SELECT
                option_code,
                supplier_name,
                unit_cost,
                total_cost,
                is_comparable,
                notes
            FROM supplier_options
            WHERE sourcing_request_id = ?
            ORDER BY unit_cost ASC, option_code ASC
        """, (req["id"],)).fetchall()

        print("SUPPLIER_OPTIONS")
        for row in options:
            print(dict(row))

        print("-" * 120)

        shortlist = conn.execute("""
            SELECT
                sourcing_request_id,
                best_option_code,
                best_supplier_name,
                best_unit_cost,
                best_total_cost,
                second_option_code,
                second_unit_cost,
                third_option_code,
                third_unit_cost,
                am_spot_unit_cost,
                delta_best_vs_am_spot,
                savings_total_vs_am_spot
            FROM sourcing_request_shortlist
            WHERE sourcing_request_id = ?
        """, (req["id"],)).fetchone()

        print("SHORTLIST")
        print(dict(shortlist) if shortlist else "Sin shortlist")


if __name__ == "__main__":
    main()