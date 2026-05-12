from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def fetch_decisions(conn):
    return conn.execute("""
        SELECT
            d.id AS decision_id,
            d.sourcing_request_id,
            d.selected_quote_id,
            d.decision_reason,
            d.decided_by,
            d.decided_at,
            sr.our_ref,
            sr.requested_tons,
            sr.status AS request_status,
            c.name AS client_name,
            rs.product,
            rs.grade,
            rs.thickness_mm,
            rs.width_mm,
            q.supplier_code AS selected_supplier_code,
            q.supplier_name AS selected_supplier_name,
            q.total_price_per_ton AS selected_total_price_per_ton,
            q.total_estimated_cost AS selected_total_estimated_cost,
            q.needs_manual_review AS selected_needs_manual_review
        FROM sourcing_decisions d
        JOIN sourcing_requests sr ON sr.id = d.sourcing_request_id
        JOIN clients c            ON c.id = sr.client_id
        JOIN request_specs rs     ON rs.id = sr.request_spec_id
        JOIN sourcing_quotes q    ON q.id = d.selected_quote_id
        ORDER BY d.decided_at DESC, d.id DESC
    """).fetchall()


def fetch_next_best_real_quote(conn, sourcing_request_id: int, selected_quote_id: int):
    return conn.execute("""
        SELECT
            supplier_code,
            supplier_name,
            total_price_per_ton
        FROM sourcing_quotes
        WHERE sourcing_request_id = ?
          AND id <> ?
          AND COALESCE(needs_manual_review, 0) = 0
        ORDER BY total_price_per_ton ASC, id ASC
        LIMIT 1
    """, (sourcing_request_id, selected_quote_id)).fetchone()


def count_excluded_manual_review_quotes(conn, sourcing_request_id: int, selected_quote_id: int) -> int:
    return conn.execute("""
        SELECT COUNT(*)
        FROM sourcing_quotes
        WHERE sourcing_request_id = ?
          AND id <> ?
          AND COALESCE(needs_manual_review, 0) = 1
    """, (sourcing_request_id, selected_quote_id)).fetchone()[0]


def fetch_am_spot_benchmark(conn, sourcing_request_id: int):
    return conn.execute("""
        SELECT unit_cost
        FROM supplier_options
        WHERE sourcing_request_id = ?
          AND option_code = 'AM_SPOT'
          AND is_comparable = 1
          AND is_rankable = 1
          AND capability_allowed = 1
        LIMIT 1
    """, (sourcing_request_id,)).fetchone()


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        decisions = fetch_decisions(conn)

        print("SAVINGS REPORT")
        print("-" * 180)

        total_selected_spend = 0.0
        total_savings_vs_next_best_real = 0.0
        total_savings_vs_am_spot = 0.0
        decisions_with_real_alternative = 0

        for row in decisions:
            selected_price = float(row["selected_total_price_per_ton"] or 0)
            requested_tons = float(row["requested_tons"] or 0)
            total_selected_spend += float(row["selected_total_estimated_cost"] or 0)

            next_best = fetch_next_best_real_quote(
                conn,
                row["sourcing_request_id"],
                row["selected_quote_id"]
            )
            excluded_manual_review_count = count_excluded_manual_review_quotes(
                conn,
                row["sourcing_request_id"],
                row["selected_quote_id"]
            )

            if next_best is not None and next_best["total_price_per_ton"] is not None:
                next_best_price = float(next_best["total_price_per_ton"])
                savings_vs_next_best_real = (next_best_price - selected_price) * requested_tons
                total_savings_vs_next_best_real += savings_vs_next_best_real
                decisions_with_real_alternative += 1
                next_best_text = (
                    f"{next_best['supplier_code']} | {next_best['supplier_name']} | "
                    f"{next_best_price:.2f} EUR/t | savings={next_best_price - selected_price:.2f} EUR/t | "
                    f"total={savings_vs_next_best_real:.2f}"
                )
            else:
                savings_vs_next_best_real = 0.0
                if excluded_manual_review_count > 0:
                    next_best_text = (
                        f"sin alternativa real en sourcing_quotes "
                        f"(se excluyeron {excluded_manual_review_count} quote(s) con needs_manual_review=1)"
                    )
                else:
                    next_best_text = "sin alternativa real en sourcing_quotes"

            am_spot = fetch_am_spot_benchmark(conn, row["sourcing_request_id"])
            if am_spot is not None and am_spot["unit_cost"] is not None:
                am_spot_price = float(am_spot["unit_cost"])
                savings_vs_am_spot = (am_spot_price - selected_price) * requested_tons
                total_savings_vs_am_spot += savings_vs_am_spot
                am_spot_text = (
                    f"{am_spot_price:.2f} EUR/t | "
                    f"savings={am_spot_price - selected_price:.2f} EUR/t | total={savings_vs_am_spot:.2f}"
                )
            else:
                savings_vs_am_spot = 0.0
                am_spot_text = "sin benchmark comparable"

            print(
                f"decision_id={row['decision_id']} | request_id={row['sourcing_request_id']} | "
                f"ref={row['our_ref']} | client={row['client_name']} | "
                f"{row['product']} | {row['grade']} | {row['thickness_mm']} x {row['width_mm']} | "
                f"tn={requested_tons:.1f}"
            )
            print(
                f"  SELECTED: {row['selected_supplier_code']} | {row['selected_supplier_name']} | "
                f"{selected_price:.2f} EUR/t | total={float(row['selected_total_estimated_cost'] or 0):.2f} | "
                f"needs_manual_review={row['selected_needs_manual_review']}"
            )
            print(f"  NEXT BEST REAL QUOTE: {next_best_text}")
            print(f"  AM_SPOT BENCHMARK: {am_spot_text}")
            print(
                f"  DECISION: reason={row['decision_reason']} | by={row['decided_by']} | "
                f"at={row['decided_at']} | request_status={row['request_status']}"
            )
            print("-" * 180)

        avg_savings_vs_next_best_real = (
            total_savings_vs_next_best_real / decisions_with_real_alternative
            if decisions_with_real_alternative > 0 else 0.0
        )
        avg_savings_vs_am_spot = (
            total_savings_vs_am_spot / len(decisions)
            if decisions else 0.0
        )

        print("RESUMEN GLOBAL")
        print("-" * 180)
        print(f"Total decisions: {len(decisions)}")
        print(f"Decisions with real alternative quote: {decisions_with_real_alternative}")
        print(f"Total selected spend: {total_selected_spend:.2f}")
        print(f"Total savings vs next best REAL quote: {total_savings_vs_next_best_real:.2f}")
        print(f"Total savings vs AM_SPOT benchmark: {total_savings_vs_am_spot:.2f}")
        print(f"Avg savings vs next best REAL quote: {avg_savings_vs_next_best_real:.2f}")
        print(f"Avg savings vs AM_SPOT benchmark: {avg_savings_vs_am_spot:.2f}")


if __name__ == "__main__":
    main()