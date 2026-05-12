from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKUP_DIR = BASE_DIR / "exports" / "backups"


def backup_sourcing_state(db_path: Path) -> Path | None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        quote_count = conn.execute("SELECT COUNT(*) FROM sourcing_quotes").fetchone()[0]
        decision_count = conn.execute("SELECT COUNT(*) FROM sourcing_decisions").fetchone()[0]

        if quote_count == 0 and decision_count == 0:
            print("[backup] No hay sourcing_quotes ni sourcing_decisions para preservar.")
            return None

        quotes = conn.execute("""
            SELECT
                q.id AS old_quote_id,
                sr.our_ref,
                c.name AS client_name,
                rs.spec_key,
                sr.sheet_date,
                sr.requested_tons,

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
                q.notes,
                q.created_at
            FROM sourcing_quotes q
            JOIN sourcing_requests sr ON sr.id = q.sourcing_request_id
            JOIN clients c            ON c.id = sr.client_id
            JOIN request_specs rs     ON rs.id = sr.request_spec_id
            ORDER BY q.id
        """).fetchall()

        decisions = conn.execute("""
            SELECT
                d.id AS old_decision_id,
                d.selected_quote_id AS old_selected_quote_id,
                sr.our_ref,
                c.name AS client_name,
                rs.spec_key,
                sr.sheet_date,
                sr.requested_tons,
                d.decision_reason,
                d.decided_by,
                d.decided_at,
                d.created_at
            FROM sourcing_decisions d
            JOIN sourcing_requests sr ON sr.id = d.sourcing_request_id
            JOIN clients c            ON c.id = sr.client_id
            JOIN request_specs rs     ON rs.id = sr.request_spec_id
            ORDER BY d.id
        """).fetchall()

    payload = {
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "quotes": [dict(r) for r in quotes],
        "decisions": [dict(r) for r in decisions],
    }

    backup_path = BACKUP_DIR / f"sourcing_state_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    backup_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[backup] Backup creado: {backup_path}")
    print(f"[backup] Quotes: {len(payload['quotes'])} | Decisions: {len(payload['decisions'])}")
    return backup_path


def _resolve_request_id(conn: sqlite3.Connection, rec: dict) -> int | None:
    row = conn.execute("""
        SELECT sr.id
        FROM sourcing_requests sr
        JOIN clients c        ON c.id = sr.client_id
        JOIN request_specs rs ON rs.id = sr.request_spec_id
        WHERE sr.our_ref = ?
          AND c.name = ?
          AND rs.spec_key = ?
          AND ((sr.sheet_date = ?) OR (sr.sheet_date IS NULL AND ? IS NULL))
          AND ABS(COALESCE(sr.requested_tons, 0) - COALESCE(?, 0)) < 0.000001
        LIMIT 1
    """, (
        rec["our_ref"],
        rec["client_name"],
        rec["spec_key"],
        rec["sheet_date"],
        rec["sheet_date"],
        rec["requested_tons"],
    )).fetchone()

    return None if row is None else row["id"]


def _find_equivalent_quote(conn: sqlite3.Connection, request_id: int, rec: dict) -> int | None:
    row = conn.execute("""
        SELECT id
        FROM sourcing_quotes
        WHERE sourcing_request_id = ?
          AND supplier_code = ?
          AND supplier_name = ?
          AND ABS(COALESCE(total_price_per_ton, 0) - COALESCE(?, 0)) < 0.000001
          AND ABS(COALESCE(quoted_tons, 0) - COALESCE(?, 0)) < 0.000001
          AND COALESCE(source_type, '') = COALESCE(?, '')
          AND COALESCE(notes, '') = COALESCE(?, '')
        LIMIT 1
    """, (
        request_id,
        rec["supplier_code"],
        rec["supplier_name"],
        rec["total_price_per_ton"],
        rec["quoted_tons"],
        rec["source_type"],
        rec["notes"],
    )).fetchone()

    return None if row is None else row["id"]


def restore_sourcing_state(db_path: Path, backup_path: Path | None) -> dict:
    if backup_path is None or not backup_path.exists():
        print("[restore] No hay backup para restaurar.")
        return {
            "quotes_restored": 0,
            "quotes_skipped": 0,
            "decisions_restored": 0,
            "decisions_skipped": 0,
        }

    payload = json.loads(backup_path.read_text(encoding="utf-8"))
    quotes = payload.get("quotes", [])
    decisions = payload.get("decisions", [])

    old_to_new_quote_id: dict[int, int] = {}
    quotes_restored = 0
    quotes_skipped = 0
    decisions_restored = 0
    decisions_skipped = 0

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        for rec in quotes:
            request_id = _resolve_request_id(conn, rec)
            if request_id is None:
                quotes_skipped += 1
                continue

            existing_quote_id = _find_equivalent_quote(conn, request_id, rec)
            if existing_quote_id is not None:
                old_to_new_quote_id[rec["old_quote_id"]] = existing_quote_id
                continue

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
                request_id,
                rec["supplier_code"],
                rec["supplier_name"],
                rec["quoted_price_per_ton"],
                rec["transport_cost_per_ton"],
                rec["surcharges_per_ton"],
                rec["total_price_per_ton"],
                rec["total_estimated_cost"],
                rec["currency"],
                rec["quoted_tons"],
                rec["lead_time_days"],
                rec["transport_type"],
                rec["quality_confirmed"],
                rec["source_type"],
                rec["needs_manual_review"],
                rec["notes"],
                rec["created_at"],
            ))

            new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            old_to_new_quote_id[rec["old_quote_id"]] = new_id
            quotes_restored += 1

        for rec in decisions:
            request_id = _resolve_request_id(conn, rec)
            if request_id is None:
                decisions_skipped += 1
                continue

            selected_quote_id = old_to_new_quote_id.get(rec["old_selected_quote_id"])
            if selected_quote_id is None:
                decisions_skipped += 1
                continue

            existing_decision = conn.execute("""
                SELECT id
                FROM sourcing_decisions
                WHERE sourcing_request_id = ?
                LIMIT 1
            """, (request_id,)).fetchone()

            if existing_decision is not None:
                continue

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
                request_id,
                selected_quote_id,
                rec["decision_reason"],
                rec["decided_by"],
                rec["decided_at"],
                rec["created_at"],
            ))

            conn.execute("""
                UPDATE sourcing_requests
                SET status = 'awarded'
                WHERE id = ?
            """, (request_id,))

            decisions_restored += 1

        conn.commit()

    summary = {
        "quotes_restored": quotes_restored,
        "quotes_skipped": quotes_skipped,
        "decisions_restored": decisions_restored,
        "decisions_skipped": decisions_skipped,
    }

    print(f"[restore] Backup restaurado desde: {backup_path}")
    print(f"[restore] {summary}")
    return summary