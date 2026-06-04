from __future__ import annotations

import sqlite3
from typing import Any, Sequence

from src.services.models import StagingQuote


VALID_REVIEW_STATUS = {"pending", "approved", "rejected"}


def _normalize_status(status: str | None) -> str | None:
    if status is None:
        return None

    normalized = status.strip().lower()

    aliases = {
        "a": "approved",
        "approve": "approved",
        "aprobado": "approved",
        "aprobada": "approved",
        "r": "rejected",
        "reject": "rejected",
        "rechazado": "rejected",
        "rechazada": "rejected",
        "p": "pending",
        "pendiente": "pending",
    }

    return aliases.get(normalized, normalized)


def list_staging_quotes(
    conn: sqlite3.Connection,
    supplier_code: str | None = None,
    review_status: str | None = None,
    coating: str | None = None,
    thickness_min: float | None = None,
    thickness_max: float | None = None,
    max_price: float | None = None,
    limit: int | None = None,
) -> list[StagingQuote]:
    where_parts = ["1 = 1"]
    params: list[Any] = []

    if supplier_code:
        where_parts.append("UPPER(q.supplier_code) = ?")
        params.append(supplier_code.strip().upper())

    normalized_status = _normalize_status(review_status)
    if normalized_status:
        where_parts.append("COALESCE(q.review_status, 'pending') = ?")
        params.append(normalized_status)

    if coating:
        where_parts.append("""
            (
                UPPER(COALESCE(q.extracted_grade, '')) LIKE ?
                OR UPPER(COALESCE(q.coating_raw, '')) LIKE ?
            )
        """)
        pattern = f"%{coating.strip().upper()}%"
        params.extend([pattern, pattern])

    if thickness_min is not None:
        where_parts.append("q.extracted_thickness_mm IS NOT NULL")
        where_parts.append("q.extracted_thickness_mm >= ?")
        params.append(float(thickness_min))

    if thickness_max is not None:
        where_parts.append("q.extracted_thickness_mm IS NOT NULL")
        where_parts.append("q.extracted_thickness_mm <= ?")
        params.append(float(thickness_max))

    if max_price is not None:
        where_parts.append("q.extracted_price_per_ton IS NOT NULL")
        where_parts.append("q.extracted_price_per_ton <= ?")
        params.append(float(max_price))

    limit_sql = ""
    if limit is not None:
        limit_sql = "LIMIT ?"
        params.append(int(limit))

    query = f"""
        SELECT
            q.id,
            q.supplier_code,
            q.extracted_grade,
            q.coating_raw,
            q.extracted_thickness_mm,
            q.extracted_width_mm,
            q.extracted_price_per_ton,
            COALESCE(q.review_status, 'pending') AS review_status,
            COALESCE(q.needs_manual_review, 0) AS needs_manual_review,
            q.matched_sourcing_request_id,
            d.file_name,
            q.raw_text_snippet
        FROM stg_supplier_quotes q
        LEFT JOIN stg_supplier_documents d
            ON d.id = q.supplier_document_id
        WHERE {" AND ".join(where_parts)}
        ORDER BY q.supplier_code, q.id
        {limit_sql}
    """

    result_rows = conn.execute(query, params).fetchall()
    return [StagingQuote.from_row(item) for item in result_rows]


def set_review_status(
    conn: sqlite3.Connection,
    quote_ids: Sequence[int],
    status: str,
) -> int:
    normalized_status = _normalize_status(status)

    if normalized_status not in VALID_REVIEW_STATUS:
        raise ValueError(
            f"review_status inválido: {status}. "
            f"Valores permitidos: {sorted(VALID_REVIEW_STATUS)}"
        )

    clean_ids = sorted({int(quote_id) for quote_id in quote_ids})

    if not clean_ids:
        return 0

    placeholders = ",".join("?" for _ in clean_ids)

    try:
        cursor = conn.execute(
            f"""
            UPDATE stg_supplier_quotes
            SET review_status = ?
            WHERE id IN ({placeholders})
            """,
            [normalized_status, *clean_ids],
        )
        conn.commit()
        return cursor.rowcount
    except Exception:
        conn.rollback()
        raise


def staging_summary(conn: sqlite3.Connection) -> list[dict]:
    result_rows = conn.execute("""
        SELECT
            q.supplier_code,
            COALESCE(q.review_status, 'pending') AS review_status,
            COUNT(*) AS n_quotes,
            SUM(CASE WHEN COALESCE(q.needs_manual_review, 0) = 1 THEN 1 ELSE 0 END) AS n_manual_review,
            SUM(CASE WHEN q.matched_sourcing_request_id IS NOT NULL THEN 1 ELSE 0 END) AS n_matched,
            COUNT(DISTINCT q.supplier_document_id) AS n_documents
        FROM stg_supplier_quotes q
        GROUP BY q.supplier_code, COALESCE(q.review_status, 'pending')
        ORDER BY q.supplier_code, review_status
    """).fetchall()

    return [
        {
            "supplier_code": item["supplier_code"],
            "review_status": item["review_status"],
            "n_quotes": item["n_quotes"],
            "n_manual_review": item["n_manual_review"],
            "n_matched": item["n_matched"],
            "n_documents": item["n_documents"],
        }
        for item in result_rows
    ]


def get_distinct_suppliers(conn: sqlite3.Connection) -> list[str]:
    result_rows = conn.execute("""
        SELECT DISTINCT supplier_code
        FROM stg_supplier_quotes
        WHERE supplier_code IS NOT NULL
          AND TRIM(supplier_code) <> ''
        ORDER BY supplier_code
    """).fetchall()

    return [item["supplier_code"] for item in result_rows]


def get_distinct_coatings(conn: sqlite3.Connection) -> list[str]:
    result_rows = conn.execute("""
        SELECT DISTINCT
            COALESCE(NULLIF(TRIM(coating_raw), ''), NULLIF(TRIM(extracted_grade), '')) AS coating
        FROM stg_supplier_quotes
        WHERE COALESCE(NULLIF(TRIM(coating_raw), ''), NULLIF(TRIM(extracted_grade), '')) IS NOT NULL
        ORDER BY coating
    """).fetchall()

    return [item["coating"] for item in result_rows if item["coating"]]


def count_pending_by_supplier(conn: sqlite3.Connection, supplier_code: str) -> int:
    result = conn.execute("""
        SELECT COUNT(*) AS n
        FROM stg_supplier_quotes
        WHERE UPPER(supplier_code) = ?
          AND COALESCE(review_status, 'pending') = 'pending'
    """, (supplier_code.strip().upper(),)).fetchone()

    return int(result["n"] if result else 0)


def pending_documents_by_supplier(conn: sqlite3.Connection, supplier_code: str) -> list[dict]:
    result_rows = conn.execute("""
        SELECT
            COALESCE(d.file_name, '(sin documento)') AS file_name,
            COUNT(q.id) AS n_pending
        FROM stg_supplier_quotes q
        LEFT JOIN stg_supplier_documents d
            ON d.id = q.supplier_document_id
        WHERE UPPER(q.supplier_code) = ?
          AND COALESCE(q.review_status, 'pending') = 'pending'
        GROUP BY COALESCE(d.file_name, '(sin documento)')
        ORDER BY file_name
    """, (supplier_code.strip().upper(),)).fetchall()

    return [
        {
            "file_name": item["file_name"],
            "n_pending": item["n_pending"],
        }
        for item in result_rows
    ]

def set_needs_manual_review(
    conn: sqlite3.Connection,
    quote_ids: Sequence[int],
    needs_manual_review: int,
) -> int:
    if needs_manual_review not in {0, 1}:
        raise ValueError("needs_manual_review debe ser 0 o 1.")

    clean_ids = sorted({int(quote_id) for quote_id in quote_ids})

    if not clean_ids:
        return 0

    placeholders = ",".join("?" for _ in clean_ids)

    try:
        cursor = conn.execute(
            f"""
            UPDATE stg_supplier_quotes
            SET needs_manual_review = ?
            WHERE id IN ({placeholders})
            """,
            [int(needs_manual_review), *clean_ids],
        )
        conn.commit()
        return cursor.rowcount
    except Exception:
        conn.rollback()
        raise