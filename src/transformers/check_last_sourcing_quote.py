from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"

def main() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT
                q.id,
                q.sourcing_request_id,
                sr.our_ref,
                c.name AS client_name,
                rs.product,
                rs.grade,
                rs.thickness_mm,
                rs.width_mm,
                q.supplier_code,
                q.supplier_name,
                q.quoted_price_per_ton,
                q.transport_cost_per_ton,
                q.surcharges_per_ton,
                q.total_price_per_ton,
                q.total_estimated_cost,
                q.currency,
                q.quoted_tons,
                q.lead_time_days,
                q.transport_type,
                q.quality_confirmed,
                q.source_type,
                q.needs_manual_review,
                q.notes,
                q.created_at
            FROM sourcing_quotes q
            JOIN sourcing_requests sr ON sr.id = q.sourcing_request_id
            JOIN clients c            ON c.id = sr.client_id
            JOIN request_specs rs     ON rs.id = sr.request_spec_id
            ORDER BY q.id DESC
            LIMIT 1
        """).fetchone()



        if row is None:
            print("No hay sourcing_quotes.")
            return
        print("ULTIMA SOURCING_QUOTE")
        print("-" * 120)
        print(dict(row))
        
if __name__ == "__main__":
    main()