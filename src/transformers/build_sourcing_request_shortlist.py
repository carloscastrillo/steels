from pathlib import Path
from datetime import datetime
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        conn.execute("DELETE FROM sourcing_request_shortlist")

        requests = conn.execute("""
            SELECT id
            FROM sourcing_requests
            ORDER BY id
        """).fetchall()

        inserted = 0

        for req in requests:
            request_id = req["id"]

            options = conn.execute("""
                SELECT
                    option_code,
                    supplier_name,
                    unit_cost,
                    total_cost
                FROM supplier_options
                WHERE sourcing_request_id = ?
                    AND is_comparable = 1
                    AND is_rankable = 1
                    AND capability_allowed = 1
                ORDER BY unit_cost ASC, option_code ASC
            """, (request_id,)).fetchall()

            am_spot = conn.execute("""
                SELECT unit_cost, total_cost
                FROM supplier_options
                WHERE sourcing_request_id = ?
                    AND option_code = 'AM_SPOT'
                    AND is_comparable = 1
                    AND is_rankable = 1
                    AND capability_allowed = 1
                LIMIT 1
            """, (request_id,)).fetchone()

            best = options[0] if len(options) > 0 else None
            second = options[1] if len(options) > 1 else None
            third = options[2] if len(options) > 2 else None

            am_spot_unit_cost = am_spot["unit_cost"] if am_spot else None
            am_spot_total_cost = am_spot["total_cost"] if am_spot else None

            delta_best_vs_am_spot = None
            savings_total_vs_am_spot = None

            if best and am_spot_unit_cost is not None:
                delta_best_vs_am_spot = float(best["unit_cost"]) - float(am_spot_unit_cost)

            if best and am_spot_total_cost is not None and best["total_cost"] is not None:
                savings_total_vs_am_spot = float(am_spot_total_cost) - float(best["total_cost"])
           
            conn.execute("""
                INSERT INTO sourcing_request_shortlist (
                    sourcing_request_id,
                    best_option_code,
                    best_supplier_name,
                    best_unit_cost,
                    best_total_cost,
                    second_option_code,
                    second_supplier_name,
                    second_unit_cost,
                    second_total_cost,
                    third_option_code,
                    third_supplier_name,
                    third_unit_cost,
                    third_total_cost,
                    am_spot_unit_cost,
                    am_spot_total_cost,
                    delta_best_vs_am_spot,
                    savings_total_vs_am_spot,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request_id,
                best["option_code"] if best else None,
                best["supplier_name"] if best else None,
                best["unit_cost"] if best else None,
                best["total_cost"] if best else None,
                second["option_code"] if second else None,
                second["supplier_name"] if second else None,
                second["unit_cost"] if second else None,
                second["total_cost"] if second else None,
                third["option_code"] if third else None,
                third["supplier_name"] if third else None,
                third["unit_cost"] if third else None,
                third["total_cost"] if third else None,
                am_spot_unit_cost,
                am_spot_total_cost,
                delta_best_vs_am_spot,
                savings_total_vs_am_spot,
                created_at,
            ))
            inserted += 1

        conn.commit()

    print(f"Shortlists generadas: {inserted}")


if __name__ == "__main__":
    main()