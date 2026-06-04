from pathlib import Path
import sqlite3


DBS = {
    "PROD": Path("db/steel_mvp.db"),
    "E2E": Path("db/steel_mvp_e2e_sprint7.db"),
}


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
    """, (table,)).fetchone()
    return row is not None


def print_rows(title: str, rows: list[tuple]) -> None:
    print()
    print(title)
    print("-" * 120)
    if not rows:
        print("(sin filas)")
        return

    for row in rows:
        print(row)


for label, db_path in DBS.items():
    if not db_path.exists():
        print()
        print("=" * 120)
        print(label, db_path)
        print("=" * 120)
        print("DB no existe.")
        continue

    conn = sqlite3.connect(db_path)

    print()
    print("=" * 120)
    print(label, db_path)
    print("=" * 120)

    print_rows(
        "sourcing_requests sospechosas",
        conn.execute("""
            SELECT
                id,
                our_ref,
                status
            FROM sourcing_requests
            WHERE id = 67
               OR LOWER(COALESCE(status, '')) LIKE '%test%'
            ORDER BY id
        """).fetchall()
    )

    print_rows(
        "sourcing_decisions sospechosas",
        conn.execute("""
            SELECT *
            FROM sourcing_decisions
            WHERE sourcing_request_id = 67
               OR LOWER(COALESCE(decision_reason, '')) LIKE '%test%'
               OR LOWER(COALESCE(decision_reason, '')) LIKE '%e2e%'
               OR LOWER(COALESCE(decided_by, '')) LIKE '%test%'
            ORDER BY id
        """).fetchall()
    )

    print_rows(
        "sourcing_quotes sospechosas request 67",
        conn.execute("""
            SELECT
                id,
                sourcing_request_id,
                supplier_code,
                supplier_name,
                total_price_per_ton,
                total_estimated_cost,
                quoted_tons,
                needs_manual_review,
                source_type,
                created_at
            FROM sourcing_quotes
            WHERE sourcing_request_id = 67
            ORDER BY id
        """).fetchall()
    )

    print_rows(
        "stg_supplier_quotes modificadas/sospechosas",
        conn.execute("""
            SELECT
                id,
                supplier_code,
                extracted_grade,
                review_status,
                matched_sourcing_request_id,
                needs_manual_review
            FROM stg_supplier_quotes
            WHERE id IN (1063, 1129)
               OR matched_sourcing_request_id = 67
            ORDER BY id
        """).fetchall()
    )

    print()
    print("Resumen")
    print("-" * 120)

    for table in [
        "stg_supplier_quotes",
        "sourcing_quotes",
        "sourcing_decisions",
        "sourcing_request_shortlist",
    ]:
        if table_exists(conn, table):
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table}: {n}")

    conn.close()


print()
print("=" * 120)
print("DRY RUN ONLY: no se ha modificado ninguna DB.")
print("=" * 120)
