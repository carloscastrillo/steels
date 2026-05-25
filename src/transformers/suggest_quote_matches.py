from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = Path(os.environ.get("STEEL_DB_PATH", BASE_DIR / "db" / "steel_mvp.db"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Matching semiautomático entre stg_supplier_quotes y sourcing_requests."
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Número máximo de candidatos a mostrar por quote",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=25.0,
        help="Score mínimo para mostrar un candidato",
    )
    parser.add_argument(
        "--quote-id",
        type=int,
        default=None,
        help="Revisar solo una quote concreta",
    )
    return parser.parse_args()


def line(width: int = 140) -> None:
    print("-" * width)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).upper().replace("\n", " ").strip().split())


def load_raw_json(value: Any) -> dict:
    if not value:
        return {}

    try:
        payload = json.loads(value)
        if isinstance(payload, dict):
            return payload
    except Exception:
        return {}

    return {}


def extract_tokens_from_quote(quote: dict) -> set[str]:
    """
    Extrae tokens técnicos útiles desde coating_raw y extracted_grade.

    Ejemplos:
        Z140
        Z275
        Z70-50
        DC01
        DC04
        DX51D
        S235JR
        S355MC
    """
    text_parts = [
        quote.get("coating_raw"),
        quote.get("extracted_grade"),
        quote.get("raw_text_snippet"),
    ]
    text = normalize_text(" ".join(str(x) for x in text_parts if x))

    tokens: set[str] = set()

    patterns = [
        r"\bZM\s*\d{2,3}\b",
        r"\bZ\s*\d{2,3}(?:[-/]\d{1,3})?\b",
        r"\bDX\d{2}D\b",
        r"\bDC\d{2}\b",
        r"\bS\d{3}(?:JR|MC|GD)?\b",
        r"\bHC\d{3}[A-Z]*\b",
        r"\bHCT\d{3}[A-Z]*\b",
        r"\bDP\d{3,4}\b",
    ]

    for pattern in patterns:
        for match in re.findall(pattern, text):
            token = match.replace(" ", "").replace("/", "-")
            tokens.add(token)

    return tokens


def token_matches_request(token: str, request_grade: str) -> bool:
    req = normalize_text(request_grade).replace("/", "-")

    if token in req:
        return True

    if "-" in token:
        first_part = token.split("-")[0]
        if first_part and first_part in req:
            return True

    return False


def get_quote_thickness_range(quote: dict) -> tuple[float | None, float | None, float | None]:
    payload = load_raw_json(quote.get("raw_row_json"))

    possible_min_keys = [
        "thickness_min_mm",
        "thickness_min",
        "espessura_min_mm",
    ]
    possible_max_keys = [
        "thickness_max_mm",
        "thickness_max",
        "espessura_max_mm",
    ]

    min_val = None
    max_val = None

    for key in possible_min_keys:
        if payload.get(key) is not None:
            min_val = float(payload[key])
            break

    for key in possible_max_keys:
        if payload.get(key) is not None:
            max_val = float(payload[key])
            break

    mid = quote.get("extracted_thickness_mm")

    if mid is not None:
        try:
            mid = float(mid)
        except Exception:
            mid = None

    if min_val is not None and max_val is not None:
        return min_val, max_val, mid

    if mid is not None:
        return mid, mid, mid

    return None, None, None


def score_grade_tokens(quote: dict, request: dict) -> tuple[float, str]:
    tokens = extract_tokens_from_quote(quote)
    request_grade = request.get("grade") or ""

    if not tokens:
        return 0.0, "sin tokens técnicos"

    matched = [token for token in sorted(tokens) if token_matches_request(token, request_grade)]

    if matched:
        if len(matched) >= 2:
            return 40.0, f"tokens match: {', '.join(matched)}"
        return 32.0, f"token match: {matched[0]}"

    return 0.0, f"sin match grade; tokens={', '.join(sorted(tokens))}"


def score_thickness(quote: dict, request: dict) -> tuple[float, str]:
    q_min, q_max, q_mid = get_quote_thickness_range(quote)
    r_thick = request.get("thickness_mm")

    if r_thick is None:
        return 0.0, "request sin espesor"

    r_thick = float(r_thick)

    if q_min is not None and q_max is not None and q_min != q_max:
        if q_min <= r_thick <= q_max:
            return 40.0, f"espesor dentro de rango {q_min}-{q_max}"

        diff = min(abs(r_thick - q_min), abs(r_thick - q_max))
        if diff <= 0.05:
            return 30.0, f"espesor cerca de rango {q_min}-{q_max}"
        if diff <= 0.15:
            return 20.0, f"espesor algo cerca de rango {q_min}-{q_max}"
        if diff <= 0.30:
            return 10.0, f"espesor lejano pero posible {q_min}-{q_max}"

        return 0.0, f"espesor fuera de rango {q_min}-{q_max}"

    if q_mid is None:
        return 8.0, "quote sin espesor; no penalización fuerte"

    diff = abs(float(q_mid) - r_thick)

    if diff <= 0.03:
        return 40.0, f"espesor casi exacto diff={diff:.3f}"
    if diff <= 0.08:
        return 32.0, f"espesor muy cercano diff={diff:.3f}"
    if diff <= 0.15:
        return 24.0, f"espesor cercano diff={diff:.3f}"
    if diff <= 0.30:
        return 10.0, f"espesor posible diff={diff:.3f}"

    return 0.0, f"espesor incompatible diff={diff:.3f}"


def score_width(quote: dict, request: dict) -> tuple[float, str]:
    q_width = quote.get("extracted_width_mm")
    r_width = request.get("width_mm")

    if r_width is None:
        return 0.0, "request sin ancho"

    if q_width is None:
        return 10.0, "quote sin ancho; no penalización"

    diff = abs(float(q_width) - float(r_width))

    if diff <= 25:
        return 20.0, f"ancho casi exacto diff={diff:.0f}"
    if diff <= 75:
        return 15.0, f"ancho cercano diff={diff:.0f}"
    if diff <= 150:
        return 10.0, f"ancho posible diff={diff:.0f}"

    return 0.0, f"ancho incompatible diff={diff:.0f}"


def score_match(quote: dict, request: dict) -> tuple[float, list[str]]:
    grade_score, grade_reason = score_grade_tokens(quote, request)
    thickness_score, thickness_reason = score_thickness(quote, request)
    width_score, width_reason = score_width(quote, request)

    score = grade_score + thickness_score + width_score

    reasons = [
        f"grade={grade_score:.0f}: {grade_reason}",
        f"thickness={thickness_score:.0f}: {thickness_reason}",
        f"width={width_score:.0f}: {width_reason}",
    ]

    return score, reasons


def fetch_quote(conn: sqlite3.Connection, quote_id: int) -> sqlite3.Row | None:
    return conn.execute("""
        SELECT
            q.*,
            d.file_name AS file_name
        FROM stg_supplier_quotes q
        LEFT JOIN stg_supplier_documents d
            ON d.id = q.supplier_document_id
        WHERE q.id = ?
    """, (quote_id,)).fetchone()


def fetch_unmatched_quotes(conn: sqlite3.Connection, quote_id: int | None = None) -> list[sqlite3.Row]:
    if quote_id is not None:
        quote = fetch_quote(conn, quote_id)
        return [quote] if quote is not None else []

    return conn.execute("""
        SELECT
            q.*,
            d.file_name AS file_name
        FROM stg_supplier_quotes q
        LEFT JOIN stg_supplier_documents d
            ON d.id = q.supplier_document_id
        WHERE q.review_status = 'approved'
          AND q.matched_sourcing_request_id IS NULL
        ORDER BY q.supplier_code, q.extracted_grade, q.extracted_thickness_mm, q.id
    """).fetchall()


def fetch_open_requests(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("""
        SELECT
            sr.id,
            sr.our_ref,
            sr.requested_tons,
            sr.status,
            sr.sheet_date,
            rs.product,
            rs.grade,
            rs.thickness_mm,
            rs.width_mm,
            rs.cw_min,
            rs.cw_max,
            c.name AS client_name
        FROM sourcing_requests sr
        JOIN request_specs rs
            ON rs.id = sr.request_spec_id
        JOIN clients c
            ON c.id = sr.client_id
        WHERE COALESCE(sr.status, '') NOT IN ('awarded', 'cancelled')
        ORDER BY sr.id DESC
    """).fetchall()


def find_candidates(
    quote: sqlite3.Row,
    requests: list[sqlite3.Row],
    top_n: int,
    min_score: float,
) -> list[dict]:
    quote_dict = dict(quote)

    candidates: list[dict] = []

    for request in requests:
        req_dict = dict(request)
        score, reasons = score_match(quote_dict, req_dict)

        if score < min_score:
            continue

        candidates.append({
            "score": score,
            "reasons": reasons,
            "request_id": req_dict["id"],
            "our_ref": req_dict["our_ref"],
            "client_name": req_dict["client_name"],
            "product": req_dict["product"],
            "grade": req_dict["grade"],
            "thickness_mm": req_dict["thickness_mm"],
            "width_mm": req_dict["width_mm"],
            "tons": req_dict["requested_tons"],
            "status": req_dict["status"],
            "sheet_date": req_dict["sheet_date"],
        })

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:top_n]


def print_quote(quote: sqlite3.Row) -> None:
    print()
    line()
    print(f"QUOTE STAGING #{quote['id']}")
    line()
    print(f"Proveedor   : {quote['supplier_code']} | {quote['supplier_name']}")
    print(f"Documento   : {quote['file_name']}")
    print(f"Grade extra : {quote['extracted_grade']}")
    print(f"Coating raw : {quote['coating_raw'] if 'coating_raw' in quote.keys() else ''}")
    print(f"Espesor     : {quote['extracted_thickness_mm']}")
    print(f"Ancho       : {quote['extracted_width_mm']}")
    print(f"Precio      : {quote['extracted_price_per_ton']} {quote['currency']}/t")
    print(f"Review      : {quote['review_status']}")
    print(f"Notes       : {quote['notes']}")


def print_candidates(candidates: list[dict]) -> None:
    print()
    print("CANDIDATOS")
    line()

    for idx, cand in enumerate(candidates, start=1):
        print(
            f"[{idx}] Score={cand['score']:.0f} | "
            f"Req#{cand['request_id']} | ref={cand['our_ref']} | "
            f"{cand['client_name']} | {cand['product']} | {cand['grade']} | "
            f"{cand['thickness_mm']} x {cand['width_mm']} | "
            f"tn={cand['tons']} | status={cand['status']}"
        )
        for reason in cand["reasons"]:
            print(f"     - {reason}")


def assign_match(conn: sqlite3.Connection, quote_id: int, request_id: int) -> None:
    conn.execute("""
        UPDATE stg_supplier_quotes
        SET matched_sourcing_request_id = ?
        WHERE id = ?
    """, (request_id, quote_id))
    conn.commit()


def reject_quote(conn: sqlite3.Connection, quote_id: int) -> None:
    conn.execute("""
        UPDATE stg_supplier_quotes
        SET review_status = 'rejected'
        WHERE id = ?
    """, (quote_id,))
    conn.commit()


def interactive_match_session(top_n: int, min_score: float, quote_id: int | None = None) -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la DB: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        requests = fetch_open_requests(conn)
        quotes = fetch_unmatched_quotes(conn, quote_id=quote_id)

        if not quotes:
            print("No hay quotes aprobadas sin match.")
            return

        print()
        print(f"Quotes aprobadas sin match: {len(quotes)}")
        print(f"Requests abiertas candidatas: {len(requests)}")

        for quote in quotes:
            print_quote(quote)

            if quote["review_status"] != "approved":
                print("Esta quote no está approved. Saltando.")
                continue

            candidates = find_candidates(
                quote=quote,
                requests=requests,
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
                    reject_quote(conn, quote["id"])
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

            if choice == "s" or choice == "":
                continue

            if choice == "r":
                reject_quote(conn, quote["id"])
                print("Quote marcada como rejected.")
                continue

            if choice.isdigit() and 1 <= int(choice) <= len(candidates):
                selected = candidates[int(choice) - 1]

                print()
                print("[CONFIRMACIÓN]")
                print(f"Quote #{quote['id']} -> Request #{selected['request_id']} ref={selected['our_ref']}")
                confirm = input("Confirmar asignación [s/N]: ").strip().lower()

                if confirm != "s":
                    print("Asignación cancelada.")
                    continue

                assign_match(conn, quote["id"], selected["request_id"])
                print(f"OK: quote #{quote['id']} asignada a request #{selected['request_id']}.")
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
