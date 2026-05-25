from __future__ import annotations

from pathlib import Path
import os
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = Path(os.environ.get("STEEL_DB_PATH", BASE_DIR / "db" / "steel_mvp.db"))


VALID_ACTIONS = {
    "a": "approved",
    "approved": "approved",
    "aprobar": "approved",
    "r": "rejected",
    "rejected": "rejected",
    "rechazar": "rejected",
}


def print_line(width: int = 120) -> None:
    print("-" * width)


def fetch_status(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("""
        SELECT
            supplier_code,
            COALESCE(review_status, 'pending') AS review_status,
            COUNT(*) AS n
        FROM stg_supplier_quotes
        GROUP BY supplier_code, COALESCE(review_status, 'pending')
        ORDER BY supplier_code, review_status
    """).fetchall()


def fetch_pending_summary(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("""
        SELECT
            supplier_code,
            COUNT(*) AS n_pending,
            MIN(created_at) AS first_created_at,
            MAX(created_at) AS last_created_at
        FROM stg_supplier_quotes
        WHERE COALESCE(review_status, 'pending') = 'pending'
        GROUP BY supplier_code
        ORDER BY supplier_code
    """).fetchall()


def fetch_pending_documents(conn: sqlite3.Connection, supplier_code: str) -> list[sqlite3.Row]:
    return conn.execute("""
        SELECT
            COALESCE(d.file_name, '(sin documento)') AS file_name,
            COUNT(q.id) AS n_pending
        FROM stg_supplier_quotes q
        LEFT JOIN stg_supplier_documents d
            ON d.id = q.supplier_document_id
        WHERE q.supplier_code = ?
          AND COALESCE(q.review_status, 'pending') = 'pending'
        GROUP BY COALESCE(d.file_name, '(sin documento)')
        ORDER BY file_name
    """, (supplier_code,)).fetchall()


def count_pending(conn: sqlite3.Connection, supplier_code: str) -> int:
    return conn.execute("""
        SELECT COUNT(*)
        FROM stg_supplier_quotes
        WHERE supplier_code = ?
          AND COALESCE(review_status, 'pending') = 'pending'
    """, (supplier_code,)).fetchone()[0]


def print_current_status(conn: sqlite3.Connection) -> None:
    print()
    print("ESTADO ACTUAL DE STAGING")
    print_line()

    rows = fetch_status(conn)
    if not rows:
        print("No hay quotes en stg_supplier_quotes.")
        return

    for row in rows:
        print(f"{row['supplier_code']:12s} | {row['review_status']:10s} | {row['n']:5d}")


def print_pending_summary(conn: sqlite3.Connection) -> None:
    print()
    print("QUOTES PENDING POR PROVEEDOR")
    print_line()

    rows = fetch_pending_summary(conn)
    if not rows:
        print("No hay quotes pendientes en staging.")
        return

    for row in rows:
        print(
            f"{row['supplier_code']:12s} | "
            f"pending={row['n_pending']:5d} | "
            f"desde={row['first_created_at']} | "
            f"hasta={row['last_created_at']}"
        )


def ask_supplier(conn: sqlite3.Connection) -> str | None:
    supplier = input("\nCódigo de proveedor a procesar (ENTER para cancelar): ").strip().upper()

    if not supplier:
        print("Cancelado.")
        return None

    n = count_pending(conn, supplier)
    if n == 0:
        print(f"No hay quotes pending para {supplier}.")
        return None

    print()
    print(f"DOCUMENTOS PENDING PARA {supplier}")
    print_line()

    docs = fetch_pending_documents(conn, supplier)
    for row in docs:
        print(f"{row['file_name']} | pending={row['n_pending']}")

    return supplier


def ask_action(supplier_code: str, n_pending: int) -> str | None:
    raw = input(
        f"\n¿Qué hacer con las {n_pending} quotes pending de {supplier_code}? "
        "[a]probar / [r]echazar / [c]ancelar: "
    ).strip().lower()

    if raw in {"c", "cancelar", ""}:
        print("Cancelado.")
        return None

    new_status = VALID_ACTIONS.get(raw)
    if new_status is None:
        print("Acción no válida. Usa 'a' para aprobar o 'r' para rechazar.")
        return None

    return new_status


def confirm_action(supplier_code: str, n_pending: int, new_status: str) -> bool:
    verb = "APROBAR" if new_status == "approved" else "RECHAZAR"

    print()
    print("[AVISO] Esta acción actualizará muchas filas de staging.")
    print(f"Proveedor : {supplier_code}")
    print(f"Acción    : {verb}")
    print(f"Filas     : {n_pending}")
    print()

    confirm = input(f"Escribe {supplier_code} para confirmar: ").strip().upper()

    if confirm != supplier_code:
        print("Cancelado. No coincide el código de proveedor.")
        return False

    return True


def update_batch(conn: sqlite3.Connection, supplier_code: str, new_status: str) -> int:
    cur = conn.execute("""
        UPDATE stg_supplier_quotes
        SET review_status = ?
        WHERE supplier_code = ?
          AND COALESCE(review_status, 'pending') = 'pending'
    """, (new_status, supplier_code))

    conn.commit()
    return cur.rowcount


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la DB: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        print_current_status(conn)
        print_pending_summary(conn)

        pending_rows = fetch_pending_summary(conn)
        if not pending_rows:
            return

        supplier_code = ask_supplier(conn)
        if supplier_code is None:
            return

        n_pending = count_pending(conn, supplier_code)

        new_status = ask_action(supplier_code, n_pending)
        if new_status is None:
            return

        if not confirm_action(supplier_code, n_pending, new_status):
            return

        updated = update_batch(conn, supplier_code, new_status)

    print()
    print("Actualización por lote completada.")
    print(f"Proveedor: {supplier_code}")
    print(f"Nuevo review_status: {new_status}")
    print(f"Quotes actualizadas: {updated}")


if __name__ == "__main__":
    main()
