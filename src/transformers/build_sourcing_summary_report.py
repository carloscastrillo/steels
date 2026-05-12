from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        global_summary = conn.execute("""
            SELECT
                COUNT(*) AS total_requests,
                SUM(sr.requested_tons) AS total_tons,
                SUM(CASE WHEN srs.best_option_code IS NOT NULL THEN 1 ELSE 0 END) AS requests_with_best_option,
                SUM(CASE WHEN srs.savings_total_vs_am_spot IS NOT NULL THEN srs.savings_total_vs_am_spot ELSE 0 END) AS total_savings_vs_am_spot,
                AVG(CASE WHEN srs.savings_total_vs_am_spot IS NOT NULL THEN srs.savings_total_vs_am_spot END) AS avg_savings_per_request,
                AVG(CASE WHEN srs.delta_best_vs_am_spot IS NOT NULL THEN srs.delta_best_vs_am_spot END) AS avg_delta_eur_per_ton
            FROM sourcing_request_shortlist srs
            JOIN sourcing_requests sr ON sr.id = srs.sourcing_request_id
        """).fetchone()

        winners = conn.execute("""
            SELECT
                best_option_code,
                best_supplier_name,
                COUNT(*) AS wins,
                SUM(savings_total_vs_am_spot) AS total_savings,
                AVG(savings_total_vs_am_spot) AS avg_savings,
                AVG(delta_best_vs_am_spot) AS avg_delta_eur_per_ton
            FROM sourcing_request_shortlist
            WHERE best_option_code IS NOT NULL
            GROUP BY best_option_code, best_supplier_name
            ORDER BY wins DESC, total_savings DESC
        """).fetchall()

        top_requests = conn.execute("""
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
                srs.am_spot_unit_cost,
                srs.delta_best_vs_am_spot,
                srs.savings_total_vs_am_spot
            FROM sourcing_request_shortlist srs
            JOIN sourcing_requests sr ON sr.id = srs.sourcing_request_id
            JOIN clients c ON c.id = sr.client_id
            JOIN request_specs rs ON rs.id = sr.request_spec_id
            WHERE srs.savings_total_vs_am_spot IS NOT NULL
            ORDER BY srs.savings_total_vs_am_spot DESC
            LIMIT 15
        """).fetchall()

        print("RESUMEN GLOBAL")
        print("-" * 120)
        print(f"Total requests: {global_summary['total_requests']}")
        print(f"Total tons: {global_summary['total_tons']}")
        print(f"Requests con mejor opción calculada: {global_summary['requests_with_best_option']}")
        print(f"Ahorro total potencial vs AM_SPOT: {global_summary['total_savings_vs_am_spot']}")
        print(f"Ahorro medio por request: {global_summary['avg_savings_per_request']}")
        print(f"Delta medio EUR/t vs AM_SPOT: {global_summary['avg_delta_eur_per_ton']}")

        print("\nGANADORES POR PROVEEDOR / OPCIÓN")
        print("-" * 120)
        for row in winners:
            print(
                f"- {row['best_option_code']} | {row['best_supplier_name']} | "
                f"wins={row['wins']} | "
                f"total_savings={row['total_savings']} | "
                f"avg_savings={row['avg_savings']} | "
                f"avg_delta_eur_per_ton={row['avg_delta_eur_per_ton']}"
            )

        print("\nTOP 15 REQUESTS POR AHORRO")
        print("-" * 120)
        for row in top_requests:
            print(dict(row))


if __name__ == "__main__":
    main()