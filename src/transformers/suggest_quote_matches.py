from __future__ import annotations

import argparse
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.services.matching_service import (
    assign_match,
    find_candidates,
    list_approved_unmatched,
    promote_to_core,
)
from src.services.staging_service import list_staging_quotes, set_review_status
from src.utils.db import connect


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Matching semiautomático entre stg_supplier_quotes y sourcing_requests."
    )
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--min-score", type=float, default=20.0)
    parser.add_argument("--quote-id", type=int, default=None)
    return parser.parse_args()


def line(width: int = 140) -> None:
    print("-" * width)


def print_quote(quote) -> None:
    print()
    line()
    print(f"QUOTE STAGING #{quote.id}")
    line()
    print(f"Proveedor   : {quote.supplier_code}")
    print(f"Documento   : {quote.document}")
    print(f"Grade extra : {quote.extracted_grade}")
    print(f"Coating raw : {quote.coating_raw}")
    print(f"Espesor     : {quote.thickness_mm}")
    print(f"Ancho       : {quote.width_mm}")
    print(f"Precio      : {quote.price_per_ton} EUR/t")
    print(f"Review      : {quote.review_status}")
    print(f"Needs review: {quote.needs_manual_review}")


def print_candidates(candidates) -> None:
    print()
    print("CANDIDATOS")
    line()

    for idx, candidate in enumerate(candidates, start=1):
        print(
            f"[{idx}] Score={candidate.score:.0f} | "
            f"Req#{candidate.request_id} | ref={candidate.our_ref} | "
            f"{candidate.client_name} | {candidate.product} | {candidate.grade} | "
            f"{candidate.thickness_mm} x {candidate.width_mm} | "
            f"tn={candidate.tons} | status={candidate.status}"
        )

        breakdown = candidate.breakdown
        print(f"     - grade={breakdown.get('grade_score')}: {breakdown.get('grade')}")
        print(f"     - thickness={breakdown.get('thickness_score')}: {breakdown.get('thickness')}")
        print(f"     - width={breakdown.get('width_score')}: {breakdown.get('width')}")


def get_quotes_to_review(conn, quote_id: int | None):
    if quote_id is not None:
        return list_staging_quotes(conn, limit=1_000_000)

    return list_approved_unmatched(conn)


def interactive_match_session(top_n: int, min_score: float, quote_id: int | None = None) -> None:
    with connect() as conn:
        if quote_id is not None:
            quotes = [
                quote
                for quote in list_staging_quotes(conn)
                if quote.id == quote_id
            ]
        else:
            quotes = list_approved_unmatched(conn)

        if not quotes:
            print("No hay quotes aprobadas sin match.")
            return

        print()
        print(f"Quotes a revisar: {len(quotes)}")

        for quote in quotes:
            print_quote(quote)

            if quote.review_status != "approved":
                print("Esta quote no está approved. Saltando.")
                continue

            candidates = find_candidates(
                conn,
                quote_id=quote.id,
                top_n=top_n,
                min_score=min_score,
            )

            if not candidates:
                print("Sin candidatos compatibles por encima del score mínimo.")
                choice = input("[s]altar / [r]echazar quote / [q]uit: ").strip().lower()

                if choice == "q":
                    print("Sesión terminada.")
                    return
                if choice == "r":
                    set_review_status(conn, [quote.id], "rejected")
                    print("Quote marcada como rejected.")
                continue

            print_candidates(candidates)

            choice = input(
                f"Seleccionar [1-{len(candidates)}] / "
                "[s]altar / [r]echazar quote / [q]uit: "
            ).strip().lower()

            if choice == "q":
                print("Sesión terminada.")
                return

            if choice in {"s", ""}:
                continue

            if choice == "r":
                set_review_status(conn, [quote.id], "rejected")
                print("Quote marcada como rejected.")
                continue

            if choice.isdigit() and 1 <= int(choice) <= len(candidates):
                selected = candidates[int(choice) - 1]

                print()
                print("[CONFIRMACIÓN]")
                print(f"Quote #{quote.id} -> Request #{selected.request_id} ref={selected.our_ref}")

                confirm = input("Confirmar asignación [s/N]: ").strip().lower()
                if confirm != "s":
                    print("Asignación cancelada.")
                    continue

                assign_match(conn, quote.id, selected.request_id)
                print(f"OK: quote #{quote.id} asignada a request #{selected.request_id}.")

                promote = input("¿Promover ahora a sourcing_quotes? [s/N]: ").strip().lower()
                if promote == "s":
                    new_core_id = promote_to_core(conn, quote.id)
                    print(f"OK: sourcing_quote creada/encontrada id={new_core_id}")

                continue

            print("Opción no válida. Saltando quote.")


def main() -> None:
    args = parse_args()
    interactive_match_session(
        top_n=args.top_n,
        min_score=args.min_score,
        quote_id=args.quote_id,
    )


if __name__ == "__main__":
    main()