from __future__ import annotations

from datetime import datetime
import json
import re
import sqlite3
from typing import Any

from src.services.models import MatchCandidate, StagingQuote


MIN_SCORE_DEFAULT = 20.0


def _get(value: Any, key: str, default: Any = None) -> Any:
    if value is None:
        return default

    if isinstance(value, dict):
        return value.get(key, default)

    if hasattr(value, key):
        return getattr(value, key)

    try:
        if key in value.keys():
            return value[key]
    except Exception:
        pass

    return default


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).upper().replace("\n", " ").strip().split())


def _load_json(value: Any) -> dict:
    if not value:
        return {}

    try:
        parsed = json.loads(value)
    except Exception:
        return {}

    return parsed if isinstance(parsed, dict) else {}


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _fetch_quote_record(conn: sqlite3.Connection, quote_id: int) -> sqlite3.Row | None:
    return conn.execute("""
        SELECT
            q.*,
            d.file_name
        FROM stg_supplier_quotes q
        LEFT JOIN stg_supplier_documents d
            ON d.id = q.supplier_document_id
        WHERE q.id = ?
    """, (quote_id,)).fetchone()


def _fetch_request_record(conn: sqlite3.Connection, request_id: int) -> sqlite3.Row | None:
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
        WHERE sr.id = ?
    """, (request_id,)).fetchone()


def _fetch_open_requests(conn: sqlite3.Connection) -> list[dict]:
    result_items = conn.execute("""
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

    return [dict(item) for item in result_items]


def _extract_tokens_from_quote(quote: Any) -> set[str]:
    text = _normalize_text(" ".join(
        str(part)
        for part in [
            _get(quote, "coating_raw"),
            _get(quote, "extracted_grade"),
            _get(quote, "raw_snippet"),
            _get(quote, "raw_text_snippet"),
        ]
        if part
    ))

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
            tokens.add(match.replace(" ", "").replace("/", "-"))

    return tokens


def _token_matches_request(token: str, request_grade: str | None) -> bool:
    grade = _normalize_text(request_grade).replace("/", "-")

    if token in grade:
        return True

    if "-" in token:
        first = token.split("-")[0]
        return bool(first and first in grade)

    return False


def _quote_thickness_range(quote: Any) -> tuple[float | None, float | None, float | None]:
    raw_payload = _load_json(_get(quote, "raw_row_json"))

    min_keys = ["thickness_min_mm", "thickness_min", "espessura_min_mm"]
    max_keys = ["thickness_max_mm", "thickness_max", "espessura_max_mm"]

    min_value = None
    max_value = None

    for key in min_keys:
        if raw_payload.get(key) is not None:
            min_value = float(raw_payload[key])
            break

    for key in max_keys:
        if raw_payload.get(key) is not None:
            max_value = float(raw_payload[key])
            break

    mid_value = _get(quote, "thickness_mm", _get(quote, "extracted_thickness_mm"))

    if mid_value is not None:
        try:
            mid_value = float(mid_value)
        except Exception:
            mid_value = None

    if min_value is not None and max_value is not None:
        return min_value, max_value, mid_value

    if mid_value is not None:
        return mid_value, mid_value, mid_value

    return None, None, None


def _score_grade(quote: Any, request: Any) -> tuple[float, dict]:
    tokens = _extract_tokens_from_quote(quote)
    request_grade = _get(request, "grade")

    if not tokens:
        return 0.0, {
            "reason": "sin tokens técnicos en quote",
            "tokens": [],
            "matched_tokens": [],
        }

    matched = [
        token
        for token in sorted(tokens)
        if _token_matches_request(token, request_grade)
    ]

    if len(matched) >= 2:
        return 40.0, {
            "reason": "varios tokens compatibles",
            "tokens": sorted(tokens),
            "matched_tokens": matched,
        }

    if len(matched) == 1:
        return 32.0, {
            "reason": "token compatible",
            "tokens": sorted(tokens),
            "matched_tokens": matched,
        }

    return 0.0, {
        "reason": "sin compatibilidad de coating/grade",
        "tokens": sorted(tokens),
        "matched_tokens": [],
    }


def _score_thickness(quote: Any, request: Any) -> tuple[float, dict]:
    q_min, q_max, q_mid = _quote_thickness_range(quote)
    request_thickness = _get(request, "thickness_mm")

    if request_thickness is None:
        return 0.0, {"reason": "request sin espesor"}

    request_thickness = float(request_thickness)

    if q_min is not None and q_max is not None and q_min != q_max:
        if q_min <= request_thickness <= q_max:
            return 40.0, {
                "reason": "espesor dentro del rango",
                "quote_min": q_min,
                "quote_max": q_max,
                "request_thickness": request_thickness,
            }

        diff = min(abs(request_thickness - q_min), abs(request_thickness - q_max))

        if diff <= 0.05:
            score = 30.0
        elif diff <= 0.15:
            score = 20.0
        elif diff <= 0.30:
            score = 10.0
        else:
            score = 0.0

        return score, {
            "reason": "espesor fuera de rango",
            "diff": round(diff, 3),
            "quote_min": q_min,
            "quote_max": q_max,
            "request_thickness": request_thickness,
        }

    if q_mid is None:
        return 8.0, {"reason": "quote sin espesor; penalización leve"}

    diff = abs(float(q_mid) - request_thickness)

    if diff <= 0.03:
        score = 40.0
    elif diff <= 0.08:
        score = 32.0
    elif diff <= 0.15:
        score = 24.0
    elif diff <= 0.30:
        score = 10.0
    else:
        score = 0.0

    return score, {
        "reason": "comparación por espesor representativo",
        "diff": round(diff, 3),
        "quote_thickness": q_mid,
        "request_thickness": request_thickness,
    }


def _score_width(quote: Any, request: Any) -> tuple[float, dict]:
    quote_width = _get(quote, "width_mm", _get(quote, "extracted_width_mm"))
    request_width = _get(request, "width_mm")

    if request_width is None:
        return 0.0, {"reason": "request sin ancho"}

    if quote_width is None:
        return 10.0, {"reason": "quote sin ancho; no penalización fuerte"}

    diff = abs(float(quote_width) - float(request_width))

    if diff <= 25:
        score = 20.0
    elif diff <= 75:
        score = 15.0
    elif diff <= 150:
        score = 10.0
    else:
        score = 0.0

    return score, {
        "reason": "comparación de ancho",
        "diff": round(diff, 3),
        "quote_width": quote_width,
        "request_width": request_width,
    }


def list_approved_unmatched(conn: sqlite3.Connection) -> list[StagingQuote]:
    result_items = conn.execute("""
        SELECT
            q.id,
            q.supplier_code,
            q.extracted_grade,
            q.coating_raw,
            q.extracted_thickness_mm,
            q.extracted_width_mm,
            q.extracted_price_per_ton,
            q.review_status,
            q.needs_manual_review,
            q.matched_sourcing_request_id,
            d.file_name,
            q.raw_text_snippet
        FROM stg_supplier_quotes q
        LEFT JOIN stg_supplier_documents d
            ON d.id = q.supplier_document_id
        WHERE q.review_status = 'approved'
          AND q.matched_sourcing_request_id IS NULL
        ORDER BY q.supplier_code, q.extracted_grade, q.extracted_thickness_mm, q.id
    """).fetchall()

    return [StagingQuote.from_row(item) for item in result_items]


def score_match(quote: Any, request: Any) -> tuple[float, dict]:
    grade_score, grade_detail = _score_grade(quote, request)
    thickness_score, thickness_detail = _score_thickness(quote, request)
    width_score, width_detail = _score_width(quote, request)

    breakdown = {
        "grade_score": grade_score,
        "thickness_score": thickness_score,
        "width_score": width_score,
        "grade": grade_detail,
        "thickness": thickness_detail,
        "width": width_detail,
        "blocked": False,
    }

    if grade_score <= 0:
        breakdown["blocked"] = True
        breakdown["block_reason"] = "sin compatibilidad de coating/grade"
        return 0.0, breakdown

    return grade_score + thickness_score + width_score, breakdown


def find_candidates(
    conn: sqlite3.Connection,
    quote_id: int,
    top_n: int = 5,
    min_score: float = MIN_SCORE_DEFAULT,
) -> list[MatchCandidate]:
    quote_record = _fetch_quote_record(conn, quote_id)

    if quote_record is None:
        return []

    request_items = _fetch_open_requests(conn)
    candidates: list[MatchCandidate] = []

    for request_item in request_items:
        score, breakdown = score_match(dict(quote_record), request_item)

        if score < min_score:
            continue

        candidates.append(MatchCandidate(
            score=score,
            breakdown=breakdown,
            request_id=int(request_item["id"]),
            our_ref=request_item.get("our_ref"),
            client_name=request_item.get("client_name"),
            product=request_item.get("product"),
            grade=request_item.get("grade"),
            thickness_mm=request_item.get("thickness_mm"),
            width_mm=request_item.get("width_mm"),
            tons=request_item.get("requested_tons"),
            status=request_item.get("status"),
        ))

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[:top_n]


def assign_match(conn: sqlite3.Connection, quote_id: int, request_id: int) -> None:
    try:
        conn.execute("""
            UPDATE stg_supplier_quotes
            SET matched_sourcing_request_id = ?
            WHERE id = ?
        """, (int(request_id), int(quote_id)))
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _existing_core_quote_id(conn: sqlite3.Connection, quote_id: int) -> int | None:
    columns = _table_columns(conn, "sourcing_quotes")

    if "stg_supplier_quote_id" in columns:
        item = conn.execute("""
            SELECT id
            FROM sourcing_quotes
            WHERE stg_supplier_quote_id = ?
            LIMIT 1
        """, (quote_id,)).fetchone()
        return int(item["id"]) if item else None

    if "notes" in columns:
        item = conn.execute("""
            SELECT id
            FROM sourcing_quotes
            WHERE notes LIKE ?
            LIMIT 1
        """, (f"%STG_SUPPLIER_QUOTE_ID={quote_id}%",)).fetchone()
        return int(item["id"]) if item else None

    return None


def promote_to_core(conn: sqlite3.Connection, quote_id: int) -> int:
    quote = _fetch_quote_record(conn, quote_id)

    if quote is None:
        raise ValueError(f"No existe stg_supplier_quote id={quote_id}")

    if quote["review_status"] != "approved":
        raise ValueError("La quote staging debe estar approved antes de promoverse.")

    request_id = quote["matched_sourcing_request_id"]
    if request_id is None:
        raise ValueError("La quote staging debe tener matched_sourcing_request_id antes de promoverse.")

    existing_id = _existing_core_quote_id(conn, quote_id)
    if existing_id is not None:
        return existing_id

    request = _fetch_request_record(conn, int(request_id))
    if request is None:
        raise ValueError(f"No existe sourcing_request id={request_id}")

    price = quote["extracted_price_per_ton"]
    if price is None:
        raise ValueError("La quote staging no tiene extracted_price_per_ton.")

    price = float(price)
    quoted_tons = float(request["requested_tons"]) if request["requested_tons"] is not None else None
    total_estimated_cost = price * quoted_tons if quoted_tons is not None else None

    columns = _table_columns(conn, "sourcing_quotes")
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    payload = {
        "sourcing_request_id": int(request_id),
        "supplier_code": quote["supplier_code"],
        "supplier_name": quote["supplier_name"],
        "quoted_price_per_ton": price,
        "base_price_per_ton": price,
        "total_price_per_ton": price,
        "transport_cost_per_ton": 0.0,
        "surcharges_per_ton": 0.0,
        "quoted_tons": quoted_tons,
        "total_estimated_cost": total_estimated_cost,
        "currency": quote["currency"] or "EUR",
        "lead_time_days": quote["lead_time_days"],
        "transport_type": quote["incoterm"],
        "quality_confirmed": "YES",
        "source_type": "pdf",
        "needs_manual_review": quote["needs_manual_review"],
        "stg_supplier_quote_id": int(quote_id),
        "created_at": now,
        "notes": (
            f"PROMOTED_FROM_STAGING | STG_SUPPLIER_QUOTE_ID={quote_id} | "
            f"{quote['notes'] or ''}"
        ).strip(),
    }

    insert_payload = {
        key: value
        for key, value in payload.items()
        if key in columns
    }

    if "sourcing_request_id" not in insert_payload:
        raise RuntimeError("sourcing_quotes no tiene columna sourcing_request_id.")

    if "total_price_per_ton" not in insert_payload:
        raise RuntimeError("sourcing_quotes no tiene columna total_price_per_ton.")

    column_names = list(insert_payload.keys())
    placeholders = ", ".join("?" for _ in column_names)
    sql = f"""
        INSERT INTO sourcing_quotes (
            {", ".join(column_names)}
        )
        VALUES ({placeholders})
    """

    try:
        cursor = conn.execute(sql, [insert_payload[name] for name in column_names])
        conn.commit()
        return int(cursor.lastrowid)
    except Exception:
        conn.rollback()
        raise