from __future__ import annotations

from datetime import datetime
import importlib
import sqlite3
from typing import Any

from src.services.models import CoreQuote, ShortlistRow


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def list_shortlist(
    conn: sqlite3.Connection,
    only_with_alternatives: bool = False,
) -> list[ShortlistRow]:
    where_parts = ["1 = 1"]

    if only_with_alternatives:
        where_parts.append("srs.second_option_code IS NOT NULL")

    rows = conn.execute(f"""
        SELECT
            srs.sourcing_request_id,
            sr.our_ref,
            c.name AS client_name,
            rs.product,
            rs.grade,
            rs.thickness_mm,
            rs.width_mm,
            sr.requested_tons,
            sr.status,
            srs.best_option_code,
            srs.best_supplier_name,
            srs.best_unit_cost,
            srs.best_source,
            srs.second_option_code,
            srs.second_unit_cost,
            srs.third_option_code,
            srs.am_spot_unit_cost,
            srs.delta_best_vs_am_spot,
            srs.savings_total_vs_am_spot
        FROM sourcing_request_shortlist srs
        JOIN sourcing_requests sr
            ON sr.id = srs.sourcing_request_id
        JOIN request_specs rs
            ON rs.id = sr.request_spec_id
        JOIN clients c
            ON c.id = sr.client_id
        WHERE {" AND ".join(where_parts)}
        ORDER BY
            CASE
                WHEN srs.savings_total_vs_am_spot IS NULL THEN 1
                ELSE 0
            END,
            srs.savings_total_vs_am_spot DESC,
            srs.sourcing_request_id DESC
    """).fetchall()

    return [ShortlistRow.from_row(row) for row in rows]


def get_request_quotes(
    conn: sqlite3.Connection,
    request_id: int,
) -> list[CoreQuote]:
    rows = conn.execute("""
        SELECT
            id,
            supplier_code,
            supplier_name,
            total_price_per_ton,
            total_estimated_cost,
            quoted_tons,
            COALESCE(needs_manual_review, 0) AS needs_manual_review,
            source_type
        FROM sourcing_quotes
        WHERE sourcing_request_id = ?
        ORDER BY
            CASE
                WHEN total_price_per_ton IS NULL THEN 1
                ELSE 0
            END,
            total_price_per_ton ASC,
            id ASC
    """, (int(request_id),)).fetchall()

    return [CoreQuote.from_row(row) for row in rows]


def _fetch_core_quote(conn: sqlite3.Connection, selected_quote_id: int) -> dict[str, Any]:
    row = conn.execute("""
        SELECT
            id,
            sourcing_request_id,
            supplier_code,
            supplier_name,
            total_price_per_ton,
            total_estimated_cost,
            quoted_tons,
            needs_manual_review,
            source_type
        FROM sourcing_quotes
        WHERE id = ?
    """, (int(selected_quote_id),)).fetchone()

    item = _row_to_dict(row)

    if item is None:
        raise ValueError(f"No existe sourcing_quote id={selected_quote_id}")

    return item


def _fetch_request(conn: sqlite3.Connection, request_id: int) -> dict[str, Any]:
    row = conn.execute("""
        SELECT
            id,
            status,
            requested_tons
        FROM sourcing_requests
        WHERE id = ?
    """, (int(request_id),)).fetchone()

    item = _row_to_dict(row)

    if item is None:
        raise ValueError(f"No existe sourcing_request id={request_id}")

    return item


def _build_decision_payload(
    conn: sqlite3.Connection,
    request_id: int,
    selected_quote: dict[str, Any],
    reason: str,
    decided_by: str,
) -> dict[str, Any]:
    columns = _table_columns(conn, "sourcing_decisions")
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    candidates = {
        "sourcing_request_id": int(request_id),
        "request_id": int(request_id),
        "selected_quote_id": int(selected_quote["id"]),
        "quote_id": int(selected_quote["id"]),
        "supplier_code": selected_quote.get("supplier_code"),
        "selected_supplier_code": selected_quote.get("supplier_code"),
        "supplier_name": selected_quote.get("supplier_name"),
        "selected_supplier_name": selected_quote.get("supplier_name"),
        "decision_reason": reason,
        "reason": reason,
        "decided_by": decided_by,
        "decided_at": now,
        "created_at": now,
        "selected_total_price_per_ton": selected_quote.get("total_price_per_ton"),
        "selected_total_estimated_cost": selected_quote.get("total_estimated_cost"),
        "selected_quoted_tons": selected_quote.get("quoted_tons"),
        "notes": "registered_from_shortlist_service",
    }

    return {
        key: value
        for key, value in candidates.items()
        if key in columns
    }


def register_decision(
    conn: sqlite3.Connection,
    request_id: int,
    selected_quote_id: int,
    reason: str,
    decided_by: str,
) -> int:
    selected_quote = _fetch_core_quote(conn, selected_quote_id)
    request = _fetch_request(conn, request_id)

    if int(selected_quote["sourcing_request_id"]) != int(request_id):
        raise ValueError(
            "La quote seleccionada no pertenece a la sourcing_request indicada. "
            f"quote.sourcing_request_id={selected_quote['sourcing_request_id']} "
            f"request_id={request_id}"
        )

    decision_payload = _build_decision_payload(
        conn=conn,
        request_id=int(request_id),
        selected_quote=selected_quote,
        reason=reason,
        decided_by=decided_by,
    )

    if not decision_payload:
        raise RuntimeError("No hay columnas compatibles para insertar en sourcing_decisions.")

    column_names = list(decision_payload.keys())
    placeholders = ", ".join("?" for _ in column_names)

    sql = f"""
        INSERT INTO sourcing_decisions (
            {", ".join(column_names)}
        )
        VALUES ({placeholders})
    """

    try:
        cursor = conn.execute(
            sql,
            [decision_payload[column] for column in column_names],
        )

        conn.execute("""
            UPDATE sourcing_requests
            SET status = 'awarded'
            WHERE id = ?
        """, (int(request["id"]),))

        conn.commit()
        return int(cursor.lastrowid)

    except Exception:
        conn.rollback()
        raise


def rebuild_shortlist(conn: sqlite3.Connection) -> int:
    """
    Regenera sourcing_request_shortlist usando el transformer existente.

    El transformer ya combina supplier_options (BOSS) + sourcing_quotes (QUOTE)
    y rellena best_source.
    """
    module = importlib.import_module("src.transformers.build_sourcing_request_shortlist")
    module.main()

    row = conn.execute("""
        SELECT COUNT(*) AS n
        FROM sourcing_request_shortlist
    """).fetchone()

    return int(row["n"] if row else 0)