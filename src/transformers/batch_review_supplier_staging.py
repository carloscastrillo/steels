from __future__ import annotations

from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.services.staging_service import (
    count_pending_by_supplier,
    list_staging_quotes,
    pending_documents_by_supplier,
    set_review_status,
    staging_summary,
)
from src.utils.db import connect


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


def print_current_status(summary: list[dict]) -> None:
    print()
    print("ESTADO ACTUAL DE STAGING")
    print_line()

    if not summary:
        print("No hay quotes en stg_supplier_quotes.")
        return

    for item in summary:
        print(
            f"{item['supplier_code']:12s} | "
            f"{item['review_status']:10s} | "
            f"{item['n_quotes']:5d}"
        )


def print_pending_summary(summary: list[dict]) -> None:
    print()
    print("QUOTES PENDING POR PROVEEDOR")
    print_line()

    pending_items = [
        item
        for item in summary
        if item["review_status"] == "pending"
    ]

    if not pending_items:
        print("No hay quotes pendientes en staging.")
        return

    for item in pending_items:
        print(
            f"{item['supplier_code']:12s} | "
            f"pending={item['n_quotes']:5d} | "
            f"docs={item['n_documents']:3d} | "
            f"manual_review={item['n_manual_review']:5d} | "
            f"matched={item['n_matched']:5d}"
        )


def ask_supplier(conn) -> str | None:
    supplier = input("\nCódigo de proveedor a procesar (ENTER para cancelar): ").strip().upper()

    if not supplier:
        print("Cancelado.")
        return None

    n_pending = count_pending_by_supplier(conn, supplier)
    if n_pending == 0:
        print(f"No hay quotes pending para {supplier}.")
        return None

    print()
    print(f"DOCUMENTOS PENDING PARA {supplier}")
    print_line()

    docs = pending_documents_by_supplier(conn, supplier)
    for item in docs:
        print(f"{item['file_name']} | pending={item['n_pending']}")

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


def main() -> None:
    with connect() as conn:
        summary = staging_summary(conn)

        print_current_status(summary)
        print_pending_summary(summary)

        pending_items = [
            item
            for item in summary
            if item["review_status"] == "pending"
        ]

        if not pending_items:
            return

        supplier_code = ask_supplier(conn)
        if supplier_code is None:
            return

        n_pending = count_pending_by_supplier(conn, supplier_code)

        new_status = ask_action(supplier_code, n_pending)
        if new_status is None:
            return

        if not confirm_action(supplier_code, n_pending, new_status):
            return

        pending_quotes = [
            quote.id
            for quote in list_staging_quotes(
                conn,
                supplier_code=supplier_code,
                review_status="pending",
            )
        ]

        updated = set_review_status(conn, pending_quotes, new_status)

    print()
    print("Actualización por lote completada.")
    print(f"Proveedor: {supplier_code}")
    print(f"Nuevo review_status: {new_status}")
    print(f"Quotes actualizadas: {updated}")


if __name__ == "__main__":
    main()
