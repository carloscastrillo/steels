from __future__ import annotations

from pathlib import Path
from datetime import datetime
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


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


def ask_text(label: str, default: str | None = None) -> str | None:
    suffix = f" [{default}]" if default not in (None, "") else ""
    raw = input(f"{label}{suffix}: ").strip()
    if raw == "":
        return default
    return raw


def show_recent_requests(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""
        SELECT
            sr.id,
            sr.our_ref,
            c.name AS client_name,
            rs.product,
            rs.grade,
            rs.thickness_mm,
            rs.width_mm,
            sr.requested_tons,
            sr.status
        FROM sourcing_requests sr
        JOIN clients c        ON c.id = sr.client_id
        JOIN request_specs rs ON rs.id = sr.request_spec_id
        ORDER BY sr.id DESC
        LIMIT 20
    """).fetchall()

    print("-" * 160)
    print("ULTIMAS SOURCING_REQUESTS")
    for row in rows:
        print(
            f"id={row['id']} | ref={row['our_ref']} | client={row['client_name']} | "
            f"{row['product']} | {row['grade']} | {row['thickness_mm']} x {row['width_mm']} | "
            f"tn={row['requested_tons']} | status={row['status']}"
        )
    print("-" * 160)


def show_request_context(conn: sqlite3.Connection, sourcing_request_id: int) -> sqlite3.Row | None:
    row = conn.execute("""
        SELECT
            sr.id,
            sr.our_ref,
            sr.requested_tons,
            sr.missing_tons,
            sr.status,
            sr.sheet_date,
            c.name AS client_name,
            rs.product,
            rs.grade,
            rs.thickness_mm,
            rs.width_mm,
            rs.cw_min,
            rs.cw_max
        FROM sourcing_requests sr
        JOIN clients c        ON c.id = sr.client_id
        JOIN request_specs rs ON rs.id = sr.request_spec_id
        WHERE sr.id = ?
    """, (sourcing_request_id,)).fetchone()

    if row:
        print("REQUEST SELECCIONADA")
        print("-" * 160)
        print(dict(row))
        print("-" * 160)

    return row


def fetch_quotes_for_request(conn: sqlite3.Connection, sourcing_request_id: int) -> list[sqlite3.Row]:
    return conn.execute("""
        SELECT
            q.id,
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
            q.notes
        FROM sourcing_quotes q
        WHERE q.sourcing_request_id = ?
        ORDER BY q.total_price_per_ton ASC, q.id ASC
    """, (sourcing_request_id,)).fetchall()


def print_quotes_table(rows: list[sqlite3.Row]) -> None:
    if not rows:
        print("No hay sourcing_quotes para esta request.")
        return

    print("QUOTES DISPONIBLES")
    print("-" * 190)
    header = (
        f"{'ID':>4}  {'CODE':<12}  {'SUPPLIER':<18}  "
        f"{'BASE':>10}  {'TPTE':>10}  {'REC':>10}  {'TOTAL/T':>10}  "
        f"{'TONS':>10}  {'TOTAL':>14}  {'LT':>4}  {'REV':>3}  {'QUALITY':<10}  {'SOURCE':<10}"
    )
    print(header)
    print("-" * 190)

    for row in rows:
        review = "Y" if row["needs_manual_review"] == 1 else "N"
        lead = row["lead_time_days"] if row["lead_time_days"] is not None else "-"
        quality = row["quality_confirmed"] if row["quality_confirmed"] is not None else "-"
        source = row["source_type"] if row["source_type"] is not None else "-"

        print(
            f"{row['id']:>4}  "
            f"{str(row['supplier_code']):<12}  "
            f"{str(row['supplier_name'])[:18]:<18}  "
            f"{row['quoted_price_per_ton']:>10.2f}  "
            f"{row['transport_cost_per_ton']:>10.2f}  "
            f"{row['surcharges_per_ton']:>10.2f}  "
            f"{row['total_price_per_ton']:>10.2f}  "
            f"{(row['quoted_tons'] if row['quoted_tons'] is not None else 0):>10.2f}  "
            f"{row['total_estimated_cost']:>14.2f}  "
            f"{str(lead):>4}  "
            f"{review:>3}  "
            f"{str(quality)[:10]:<10}  "
            f"{str(source)[:10]:<10}"
        )
    print("-" * 190)


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        show_recent_requests(conn)

        sourcing_request_id = ask_int("Sourcing request ID")
        if sourcing_request_id is None:
            raise ValueError("Debes indicar un sourcing_request_id")

        request_row = show_request_context(conn, sourcing_request_id)
        if request_row is None:
            raise ValueError(f"No existe sourcing_request_id={sourcing_request_id}")

        existing_decision = conn.execute("""
            SELECT
                d.id,
                d.selected_quote_id,
                d.decision_reason,
                d.decided_by,
                d.decided_at
            FROM sourcing_decisions d
            WHERE d.sourcing_request_id = ?
            LIMIT 1
        """, (sourcing_request_id,)).fetchone()

        if existing_decision is not None:
            print("YA EXISTE UNA DECISION PARA ESTA REQUEST")
            print("-" * 160)
            print(dict(existing_decision))
            print("-" * 160)
            raise ValueError("Esta request ya tiene una decisión registrada.")

        quotes = fetch_quotes_for_request(conn, sourcing_request_id)
        print_quotes_table(quotes)

        if not quotes:
            raise ValueError("No se puede registrar una decisión sin quotes.")

        selected_quote_id = ask_int("Quote ID ganadora")
        if selected_quote_id is None:
            raise ValueError("Debes indicar una quote ganadora")

        selected_quote = conn.execute("""
            SELECT
                id,
                supplier_code,
                supplier_name,
                total_price_per_ton,
                total_estimated_cost,
                quoted_tons,
                lead_time_days,
                needs_manual_review
            FROM sourcing_quotes
            WHERE id = ?
              AND sourcing_request_id = ?
        """, (selected_quote_id, sourcing_request_id)).fetchone()

        if selected_quote is None:
            raise ValueError("La quote elegida no pertenece a esta sourcing_request.")

        print("QUOTE GANADORA SELECCIONADA")
        print("-" * 160)
        print(dict(selected_quote))
        print("-" * 160)

        decision_reason = ask_text("Decision reason", "best_price")
        decided_by = ask_text("Decided by", "manual_user")

        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        conn.execute("""
            INSERT INTO sourcing_decisions (
                sourcing_request_id,
                selected_quote_id,
                decision_reason,
                decided_by,
                decided_at,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            sourcing_request_id,
            selected_quote_id,
            decision_reason,
            decided_by,
            now,
            now,
        ))

        conn.execute("""
            UPDATE sourcing_requests
            SET status = ?
            WHERE id = ?
        """, ("awarded", sourcing_request_id))

        conn.commit()

        print("DECISION REGISTRADA CORRECTAMENTE")
        print("-" * 160)
        print(f"sourcing_request_id: {sourcing_request_id}")
        print(f"selected_quote_id: {selected_quote_id}")
        print(f"supplier_code: {selected_quote['supplier_code']}")
        print(f"supplier_name: {selected_quote['supplier_name']}")
        print(f"decision_reason: {decision_reason}")
        print(f"decided_by: {decided_by}")
        print(f"new_request_status: awarded")


if __name__ == "__main__":
    main()