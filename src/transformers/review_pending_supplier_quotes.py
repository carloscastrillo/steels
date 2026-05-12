from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def ask_text(label: str, default: str | None = None) -> str | None:
    suffix = f" [{default}]" if default not in (None, "") else ""
    raw = input(f"{label}{suffix}: ").strip()
    if raw == "":
        return default
    return raw


def ask_int(label: str, default: int | None = None) -> int | None:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"{label}{suffix}: ").strip()
        if raw == "":
            return default
        try:
            return int(raw)
        except ValueError:
            print("Valor entero no válido. Inténtalo otra vez.")


def ask_float(label: str, default: float | None = None) -> float | None:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"{label}{suffix}: ").strip().replace(",", ".")
        if raw == "":
            return default
        try:
            return float(raw)
        except ValueError:
            print("Valor numérico no válido. Inténtalo otra vez.")


def ask_action() -> str:
    while True:
        raw = input("Acción [a=aprobar, r=rechazar, s=skip, q=salir]: ").strip().lower()
        if raw in ("a", "r", "s", "q"):
            return raw
        print("Acción no válida.")

def ask_yes_no(label: str, default_no: bool = True) -> bool:
    suffix = " [s/N]" if default_no else " [S/n]"
    while True:
        raw = input(f"{label}{suffix}: ").strip().upper()
        if raw == "":
            return not default_no
        if raw in ("S", "SI", "Y", "YES", "1"):
            return True
        if raw in ("N", "NO", "0"):
            return False
        print("Respuesta no válida. Usa s/n, y/n o 1/0.")


def _tokenize_grade(value: str | None) -> set[str]:
    if not value:
        return set()
    return set(re.findall(r"[A-Z0-9]+", value.upper()))


def grade_overlap_score(extracted_grade: str | None, request_grade: str | None) -> float:
    a = _tokenize_grade(extracted_grade)
    b = _tokenize_grade(request_grade)

    if not a or not b:
        return 0.0

    overlap = len(a & b)
    base = max(len(a), len(b))
    return overlap / base if base > 0 else 0.0

def show_pending_quotes(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""
        SELECT
            q.id,
            q.supplier_code,
            q.supplier_name,
            q.extracted_grade,
            q.extracted_thickness_mm,
            q.extracted_width_mm,
            q.extracted_price_per_ton,
            q.currency,
            q.review_status,
            d.file_name
        FROM stg_supplier_quotes q
        JOIN stg_supplier_documents d ON d.id = q.supplier_document_id
        WHERE q.review_status = 'pending'
        ORDER BY q.id ASC
        LIMIT 20
    """).fetchall()

    print("-" * 160)
    print("STG_SUPPLIER_QUOTES PENDIENTES")
    if not rows:
        print("(sin pendientes)")
    for row in rows:
        print(dict(row))
    print("-" * 160)


def show_candidate_requests(conn: sqlite3.Connection, limit: int = 15) -> None:
    rows = conn.execute("""
        SELECT
            sr.id,
            sr.our_ref,
            sr.status,
            sr.requested_tons,
            c.name AS client_name,
            rs.product,
            rs.grade,
            rs.thickness_mm,
            rs.width_mm
        FROM sourcing_requests sr
        JOIN clients c        ON c.id = sr.client_id
        JOIN request_specs rs ON rs.id = sr.request_spec_id
        ORDER BY sr.id DESC
        LIMIT ?
    """, (limit,)).fetchall()

    print("SOURCING_REQUESTS RECIENTES")
    print("-" * 160)
    for row in rows:
        print(
            f"id={row['id']} | ref={row['our_ref']} | client={row['client_name']} | "
            f"{row['product']} | {row['grade']} | {row['thickness_mm']} x {row['width_mm']} | "
            f"tn={row['requested_tons']} | status={row['status']}"
        )
    print("-" * 160)


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        show_pending_quotes(conn)

        stg_quote_id = ask_int("ID de stg_supplier_quote a revisar")
        if stg_quote_id is None:
            raise ValueError("Debes indicar un ID.")

        row = conn.execute("""
            SELECT
                q.*,
                d.file_name,
                d.file_path
            FROM stg_supplier_quotes q
            JOIN stg_supplier_documents d ON d.id = q.supplier_document_id
            WHERE q.id = ?
        """, (stg_quote_id,)).fetchone()

        if row is None:
            raise ValueError(f"No existe stg_supplier_quote id={stg_quote_id}")

        print("QUOTE STAGING SELECCIONADA")
        print("-" * 160)
        print(dict(row))
        print("-" * 160)

        if row["review_status"] != "pending":
            print(f"Esta quote ya no está pendiente. review_status={row['review_status']}")
            return

        action = ask_action()
        if action == "q":
            print("Saliendo.")
            return

        if action == "s":
            print("Quote saltada.")
            return

        if action == "r":
            rejection_note = ask_text("Motivo rechazo", "manual_rejected")
            notes = row["notes"] or ""
            merged_notes = f"{notes} | REJECT_REASON:{rejection_note}" if notes else f"REJECT_REASON:{rejection_note}"

            conn.execute("""
                UPDATE stg_supplier_quotes
                SET
                    review_status = 'rejected',
                    notes = ?
                WHERE id = ?
            """, (merged_notes, stg_quote_id))
            conn.commit()

            print("Quote rechazada correctamente.")
            return

        # action == "a"
        show_candidate_requests(conn)

        auto_manual_review = 0
        auto_notes: list[str] = []

        matched_request_id = ask_int("Asignar a sourcing_request_id (ENTER para dejar NULL)")

        if matched_request_id is not None:
            request_row = conn.execute("""
                SELECT
                    sr.id,
                    sr.our_ref,
                    sr.status,
                    sr.requested_tons,
                    c.name AS client_name,
                    rs.product,
                    rs.grade,
                    rs.thickness_mm,
                    rs.width_mm
                FROM sourcing_requests sr
                JOIN clients c        ON c.id = sr.client_id
                JOIN request_specs rs ON rs.id = sr.request_spec_id
                WHERE sr.id = ?
            """, (matched_request_id,)).fetchone()

            if request_row is None:
                raise ValueError(f"No existe sourcing_request_id={matched_request_id}")

            print("REQUEST ASIGNADA")
            print("-" * 160)
            print(dict(request_row))
            print("-" * 160)

            if request_row["status"] == "awarded":
                print("[AVISO] La sourcing_request asignada ya está adjudicada (status = awarded).")
                auto_manual_review = 1
                auto_notes.append("ASSIGNED_TO_AWARDED_REQUEST")
                if not ask_yes_no("¿Continuar igualmente con esta asignación?", default_no=True):
                    print("Aprobación cancelada por el usuario.")
                    return

            score = grade_overlap_score(row["extracted_grade"], request_row["grade"])
            if score < 0.25:
                print("[AVISO] Baja similitud entre grade extraída y grade de la request.")
                print(f"Extracted grade: {row['extracted_grade']}")
                print(f"Request grade:   {request_row['grade']}")
                print(f"grade_overlap_score: {score:.2f}")
                auto_manual_review = 1
                auto_notes.append("LOW_GRADE_MATCH_CONFIDENCE")
                if not ask_yes_no("¿Continuar igualmente con esta asignación?", default_no=True):
                    print("Aprobación cancelada por el usuario.")
                    return
        else:
            request_row = None

        quoted_price_per_ton = ask_float(
            "Quoted price per ton",
            row["extracted_price_per_ton"]
        )
        if quoted_price_per_ton is None:
            raise ValueError("Quoted price per ton es obligatorio")
        if quoted_price_per_ton <= 0:
            raise ValueError("Quoted price per ton debe ser > 0")

        currency = ask_text("Currency", row["currency"] or "EUR") or "EUR"
        supplier_code = ask_text("Supplier code", row["supplier_code"]) or row["supplier_code"]
        supplier_name = ask_text("Supplier name", row["supplier_name"]) or row["supplier_name"]

        if row["supplier_code"] and supplier_code.upper() != str(row["supplier_code"]).upper():
            print("[AVISO] Estás cambiando el supplier_code extraído.")
            print(f"Extraído:   {row['supplier_code']}")
            print(f"Introducido:{supplier_code}")
            auto_manual_review = 1
            auto_notes.append("SUPPLIER_CODE_CHANGED_AT_REVIEW")

        if row["supplier_name"] and supplier_name.casefold() != str(row["supplier_name"]).casefold():
            print("[AVISO] Estás cambiando el supplier_name extraído.")
            print(f"Extraído:   {row['supplier_name']}")
            print(f"Introducido:{supplier_name}")
            auto_manual_review = 1
            auto_notes.append("SUPPLIER_NAME_CHANGED_AT_REVIEW")

        quoted_tons_default = float(request_row["requested_tons"]) if request_row is not None else None
        quoted_tons = ask_float("Quoted tons", quoted_tons_default)
        if quoted_tons is not None and quoted_tons <= 0:
            raise ValueError("Quoted tons debe ser > 0")

        transport_cost_per_ton = ask_float("Transport cost per ton", 0.0) or 0.0
        surcharges_per_ton = ask_float("Surcharges per ton", 0.0) or 0.0

        if transport_cost_per_ton < 0:
            raise ValueError("Transport cost per ton no puede ser < 0")
        if surcharges_per_ton < 0:
            raise ValueError("Surcharges per ton no puede ser < 0")

        total_price_per_ton = quoted_price_per_ton + transport_cost_per_ton + surcharges_per_ton
        total_estimated_cost = (
            total_price_per_ton * quoted_tons if quoted_tons is not None else total_price_per_ton
        )

        if row["extracted_price_per_ton"] is not None:
            extracted_price = float(row["extracted_price_per_ton"])
            if extracted_price > 0:
                delta_pct = abs(total_price_per_ton - extracted_price) / extracted_price
                if delta_pct > 0.25:
                    print("[AVISO] El precio final revisado se desvía más de un 25% del precio extraído.")
                    print(f"Extraído: {extracted_price:.2f} | Revisado: {total_price_per_ton:.2f}")
                    auto_manual_review = 1
                    auto_notes.append("STRONG_DEVIATION_VS_EXTRACTED_PRICE")

        lead_time_days = ask_int("Lead time days")
        transport_type = ask_text("Transport type")
        quality_confirmed = ask_text("Quality confirmed", "YES") or "YES"
        source_type = row["source_type"] or "pdf"

        approval_note = ask_text("Notes aprobación", "approved_from_staging")
        notes = row["notes"] or ""
        merged_notes_parts = []

        if notes:
            merged_notes_parts.append(notes)
        if auto_notes:
            merged_notes_parts.extend(auto_notes)
        if approval_note:
            merged_notes_parts.append(f"APPROVAL_NOTE:{approval_note}")

        merged_notes = " | ".join(merged_notes_parts)
        needs_manual_review = 1 if auto_manual_review == 1 else 0

        created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        if matched_request_id is not None:
            conn.execute("""
                INSERT INTO sourcing_quotes (
                    sourcing_request_id,
                    supplier_code,
                    supplier_name,
                    quoted_price_per_ton,
                    transport_cost_per_ton,
                    surcharges_per_ton,
                    total_price_per_ton,
                    total_estimated_cost,
                    currency,
                    quoted_tons,
                    lead_time_days,
                    transport_type,
                    quality_confirmed,
                    source_type,
                    needs_manual_review,
                    notes,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                matched_request_id,
                supplier_code,
                supplier_name,
                quoted_price_per_ton,
                transport_cost_per_ton,
                surcharges_per_ton,
                total_price_per_ton,
                total_estimated_cost,
                currency,
                quoted_tons,
                lead_time_days,
                transport_type,
                quality_confirmed,
                source_type,
                needs_manual_review,
                merged_notes,
                created_at,
            ))
            new_sourcing_quote_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        else:
            new_sourcing_quote_id = None

        conn.execute("""
            UPDATE stg_supplier_quotes
            SET
                matched_sourcing_request_id = ?,
                review_status = 'approved',
                notes = ?
            WHERE id = ?
        """, (
            matched_request_id,
            merged_notes,
            stg_quote_id,
        ))

        conn.commit()

        print("Quote aprobada correctamente.")
        print("-" * 160)
        print(f"stg_supplier_quote_id: {stg_quote_id}")
        print(f"matched_sourcing_request_id: {matched_request_id}")
        print(f"new_sourcing_quote_id: {new_sourcing_quote_id}")
        print(f"review_status: approved")
        print(f"needs_manual_review: {needs_manual_review}")
        print(f"notes: {merged_notes}")

if __name__ == "__main__":
    main()