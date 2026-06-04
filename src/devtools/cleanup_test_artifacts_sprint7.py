from pathlib import Path
import argparse
import sqlite3
import shutil
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def fetch_rows(conn: sqlite3.Connection) -> dict[str, list[tuple]]:
    return {
        "request_67": conn.execute("""
            SELECT id, our_ref, status
            FROM sourcing_requests
            WHERE id = 67
        """).fetchall(),

        "sourcing_quote_9": conn.execute("""
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
            WHERE id = 9
              AND sourcing_request_id = 67
              AND supplier_code = 'GALMED'
        """).fetchall(),

        "staging_quote_1063": conn.execute("""
            SELECT
                id,
                supplier_code,
                extracted_grade,
                review_status,
                matched_sourcing_request_id,
                needs_manual_review
            FROM stg_supplier_quotes
            WHERE id = 1063
        """).fetchall(),

        "decisions_67": conn.execute("""
            SELECT *
            FROM sourcing_decisions
            WHERE sourcing_request_id = 67
        """).fetchall(),
    }


def print_rows(title: str, rows: list[tuple]) -> None:
    print()
    print(title)
    print("-" * 120)
    if not rows:
        print("(sin filas)")
        return

    for row in rows:
        print(row)


def create_backup(db_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(f"{db_path.stem}_backup_before_test_cleanup_{timestamp}.db")
    shutil.copy2(db_path, backup_path)
    return backup_path


def run(db_path: Path, apply: bool) -> None:
    if not db_path.exists():
        raise FileNotFoundError(f"No existe la DB: {db_path}")

    conn = sqlite3.connect(db_path)

    print("SPRINT 7 — CLEANUP TEST ARTIFACTS")
    print("=" * 120)
    print("DB:", db_path)
    print("MODE:", "APPLY" if apply else "DRY RUN")

    before = fetch_rows(conn)

    print_rows("request_67", before["request_67"])
    print_rows("sourcing_quote_9", before["sourcing_quote_9"])
    print_rows("staging_quote_1063", before["staging_quote_1063"])
    print_rows("decisions_67", before["decisions_67"])

    print()
    print("Acciones previstas")
    print("-" * 120)
    print("1. DELETE sourcing_quotes id=9 si coincide con request_id=67, GALMED, pdf.")
    print("2. RESET stg_supplier_quotes id=1063 a pending, matched_sourcing_request_id=NULL, needs_manual_review=1.")
    print("3. No tocar sourcing_requests id=67 porque en PROD sigue pending_review.")
    print("4. No tocar sourcing_decisions porque no hay decisión sospechosa para request 67 en PROD.")

    if not apply:
        print()
        print("DRY RUN ONLY: no se ha modificado ninguna DB.")
        conn.close()
        return

    backup_path = create_backup(db_path)
    print()
    print("Backup creado:", backup_path)

    try:
        deleted = conn.execute("""
            DELETE FROM sourcing_quotes
            WHERE id = 9
              AND sourcing_request_id = 67
              AND supplier_code = 'GALMED'
              AND source_type = 'pdf'
        """).rowcount

        updated = conn.execute("""
            UPDATE stg_supplier_quotes
            SET
                review_status = 'pending',
                matched_sourcing_request_id = NULL,
                needs_manual_review = 1
            WHERE id = 1063
              AND supplier_code = 'GALMED'
        """).rowcount

        conn.commit()

        print()
        print("Aplicado")
        print("-" * 120)
        print("sourcing_quotes deleted:", deleted)
        print("stg_supplier_quotes reset:", updated)

    except Exception:
        conn.rollback()
        raise

    after = fetch_rows(conn)

    print_rows("POST cleanup — request_67", after["request_67"])
    print_rows("POST cleanup — sourcing_quote_9", after["sourcing_quote_9"])
    print_rows("POST cleanup — staging_quote_1063", after["staging_quote_1063"])
    print_rows("POST cleanup — decisions_67", after["decisions_67"])

    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="Ruta a la DB a limpiar. Por defecto: db/steel_mvp.db",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplicar cambios. Sin esta flag solo hace dry-run.",
    )
    args = parser.parse_args()

    run(Path(args.db), apply=args.apply)


if __name__ == "__main__":
    main()
