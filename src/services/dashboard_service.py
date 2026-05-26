from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXPORTS_DIR = BASE_DIR / "exports"


def _one(conn: sqlite3.Connection, query: str, params: tuple = ()) -> dict[str, Any]:
    item = conn.execute(query, params).fetchone()
    if item is None:
        return {}
    return {key: item[key] for key in item.keys()}


def _many(conn: sqlite3.Connection, query: str, params: tuple = ()) -> list[dict[str, Any]]:
    result_items = conn.execute(query, params).fetchall()
    return [{key: item[key] for key in item.keys()} for item in result_items]


def request_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    return _one(conn, """
        SELECT
            COUNT(*) AS requests_total,
            SUM(CASE WHEN COALESCE(status, '') = 'awarded' THEN 1 ELSE 0 END) AS requests_awarded,
            SUM(CASE WHEN COALESCE(status, '') NOT IN ('awarded', 'cancelled') THEN 1 ELSE 0 END) AS requests_pending,
            SUM(CASE WHEN COALESCE(status, '') = 'cancelled' THEN 1 ELSE 0 END) AS requests_cancelled
        FROM sourcing_requests
    """)


def staging_status_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    return _one(conn, """
        SELECT
            COUNT(*) AS staging_total,
            SUM(CASE WHEN COALESCE(review_status, 'pending') = 'pending' THEN 1 ELSE 0 END) AS staging_pending,
            SUM(CASE WHEN COALESCE(review_status, 'pending') = 'approved' THEN 1 ELSE 0 END) AS staging_approved,
            SUM(CASE WHEN COALESCE(review_status, 'pending') = 'rejected' THEN 1 ELSE 0 END) AS staging_rejected,
            SUM(CASE WHEN matched_sourcing_request_id IS NOT NULL THEN 1 ELSE 0 END) AS staging_matched,
            SUM(CASE WHEN matched_sourcing_request_id IS NULL THEN 1 ELSE 0 END) AS staging_unmatched
        FROM stg_supplier_quotes
    """)


def staging_by_supplier(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _many(conn, """
        SELECT
            supplier_code,
            COALESCE(review_status, 'pending') AS review_status,
            COUNT(*) AS n_quotes,
            SUM(CASE WHEN matched_sourcing_request_id IS NOT NULL THEN 1 ELSE 0 END) AS n_matched,
            COUNT(DISTINCT supplier_document_id) AS n_documents
        FROM stg_supplier_quotes
        GROUP BY supplier_code, COALESCE(review_status, 'pending')
        ORDER BY supplier_code, review_status
    """)


def shortlist_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    return _one(conn, """
        SELECT
            COUNT(*) AS shortlist_total,
            SUM(CASE WHEN second_option_code IS NOT NULL THEN 1 ELSE 0 END) AS shortlist_with_alternatives,
            SUM(CASE WHEN best_source = 'QUOTE' THEN 1 ELSE 0 END) AS best_source_quote,
            SUM(CASE WHEN savings_total_vs_am_spot IS NOT NULL THEN savings_total_vs_am_spot ELSE 0 END) AS estimated_savings_total
        FROM sourcing_request_shortlist
    """)


def latest_monthly_report() -> dict[str, Any]:
    if not EXPORTS_DIR.exists():
        return {
            "file_name": None,
            "file_path": None,
            "modified_at": None,
        }

    files = sorted(
        EXPORTS_DIR.glob("monthly_report_*.xlsx"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )

    if not files:
        return {
            "file_name": None,
            "file_path": None,
            "modified_at": None,
        }

    latest = files[0]
    modified_at = datetime.fromtimestamp(latest.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "file_name": latest.name,
        "file_path": str(latest),
        "modified_at": modified_at,
    }


def dashboard_snapshot(conn: sqlite3.Connection) -> dict[str, Any]:
    return {
        "requests": request_summary(conn),
        "staging": staging_status_summary(conn),
        "shortlist": shortlist_summary(conn),
        "staging_by_supplier": staging_by_supplier(conn),
        "latest_monthly_report": latest_monthly_report(),
    }