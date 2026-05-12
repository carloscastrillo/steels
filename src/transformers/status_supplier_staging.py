from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        docs_total = conn.execute("SELECT COUNT(*) FROM stg_supplier_documents").fetchone()[0]
        quotes_total = conn.execute("SELECT COUNT(*) FROM stg_supplier_quotes").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM stg_supplier_quotes WHERE review_status = 'pending'").fetchone()[0]
        approved = conn.execute("SELECT COUNT(*) FROM stg_supplier_quotes WHERE review_status = 'approved'").fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM stg_supplier_quotes WHERE review_status = 'rejected'").fetchone()[0]

        print("=" * 100)
        print("SUPPLIER STAGING STATUS")
        print("=" * 100)
        print(f"stg_supplier_documents: {docs_total}")
        print(f"stg_supplier_quotes   : {quotes_total}")
        print(f"  - pending           : {pending}")
        print(f"  - approved          : {approved}")
        print(f"  - rejected          : {rejected}")
        print("-" * 100)

        print("ÚLTIMOS DOCUMENTOS")
        rows = conn.execute("""
            SELECT
                id,
                file_name,
                file_type,
                supplier_code,
                n_quotes_extracted,
                imported_at
            FROM stg_supplier_documents
            ORDER BY id DESC
            LIMIT 10
        """).fetchall()

        if not rows:
            print("(sin documentos)")
        else:
            for row in rows:
                print(dict(row))

        print("-" * 100)
        print("ÚLTIMAS STG_SUPPLIER_QUOTES")
        rows = conn.execute("""
            SELECT
                id,
                supplier_code,
                supplier_name,
                extracted_grade,
                extracted_price_per_ton,
                matched_sourcing_request_id,
                review_status,
                created_at
            FROM stg_supplier_quotes
            ORDER BY id DESC
            LIMIT 10
        """).fetchall()

        if not rows:
            print("(sin quotes staging)")
        else:
            for row in rows:
                print(dict(row))


if __name__ == "__main__":
    main()