from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        row = conn.execute("""
            SELECT
                d.id,
                d.sourcing_request_id,
                sr.our_ref,
                sr.status AS request_status,
                c.name AS client_name,
                rs.product,
                rs.grade,
                rs.thickness_mm,
                rs.width_mm,
                q.id AS selected_quote_id,
                q.supplier_code,
                q.supplier_name,
                q.total_price_per_ton,
                q.total_estimated_cost,
                d.decision_reason,
                d.decided_by,
                d.decided_at,
                d.created_at
            FROM sourcing_decisions d
            JOIN sourcing_requests sr ON sr.id = d.sourcing_request_id
            JOIN clients c            ON c.id = sr.client_id
            JOIN request_specs rs     ON rs.id = sr.request_spec_id
            JOIN sourcing_quotes q    ON q.id = d.selected_quote_id
            ORDER BY d.id DESC
            LIMIT 1
        """).fetchone()

        if row is None:
            print("No hay sourcing_decisions.")
            return

        print("ULTIMA SOURCING_DECISION")
        print("-" * 160)
        print(dict(row))


if __name__ == "__main__":
    main()