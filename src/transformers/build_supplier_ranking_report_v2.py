from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        requests = conn.execute("""
            SELECT
                sr.id AS sourcing_request_id,
                sr.our_ref,
                c.name AS client_name,
                rs.product,
                rs.grade,
                rs.thickness_mm,
                rs.width_mm,
                sr.requested_tons
            FROM sourcing_requests sr
            JOIN clients c ON c.id = sr.client_id
            JOIN request_specs rs ON rs.id = sr.request_spec_id
            ORDER BY sr.id
        """).fetchall()

        print(f"Total sourcing_requests analizadas: {len(requests)}")
        print("=" * 160)

        for req in requests:
            options = conn.execute("""
                SELECT
                    option_code,
                    supplier_name,
                    unit_cost
                FROM supplier_options
                WHERE sourcing_request_id = ?
                  AND is_comparable = 1
                ORDER BY unit_cost ASC, option_code ASC
            """, (req["sourcing_request_id"],)).fetchall()

            am_spot = conn.execute("""
                SELECT unit_cost
                FROM supplier_options
                WHERE sourcing_request_id = ?
                  AND option_code = 'AM_SPOT'
                  AND is_comparable = 1
                LIMIT 1
            """, (req["sourcing_request_id"],)).fetchone()

            am_spot_cost = am_spot["unit_cost"] if am_spot else None

            print(
                f"REQUEST {req['sourcing_request_id']} | "
                f"our_ref={req['our_ref']} | "
                f"client={req['client_name']} | "
                f"{req['product']} | {req['grade']} | "
                f"{req['thickness_mm']} x {req['width_mm']} | "
                f"tn={req['requested_tons']}"
            )

            if not options:
                print("  No hay opciones comparables")
                print("-" * 160)
                continue

            best = options[0]
            print(
                f"  BEST_COMPARABLE: {best['option_code']} | {best['supplier_name']} | {best['unit_cost']:.2f} EUR/t"
            )

            if am_spot_cost is not None:
                delta_vs_am = best["unit_cost"] - am_spot_cost
                print(
                    f"  DELTA vs AM_SPOT: {delta_vs_am:+.2f} EUR/t "
                    f"(AM_SPOT={am_spot_cost:.2f})"
                )
            else:
                print("  DELTA vs AM_SPOT: no disponible")

            print("  TOP 3 COMPARABLES:")
            for idx, option in enumerate(options[:3], start=1):
                if am_spot_cost is not None:
                    delta = option["unit_cost"] - am_spot_cost
                    delta_text = f"{delta:+.2f} vs AM_SPOT"
                else:
                    delta_text = "sin benchmark AM_SPOT"

                print(
                    f"    {idx}. {option['option_code']} | "
                    f"{option['supplier_name']} | "
                    f"{option['unit_cost']:.2f} EUR/t | {delta_text}"
                )

            print("-" * 160)


if __name__ == "__main__":
    main()