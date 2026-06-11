from __future__ import annotations

from src.services.db_status_service import (
    db_status_snapshot,
    run_system_check,
)

import streamlit as st
from src.services.dashboard_service import dashboard_snapshot

from src.services.matching_service import (
    assign_match,
    find_candidates,
    list_approved_unmatched,
    promote_to_core,
)
from src.services.shortlist_service import (
    get_request_quotes,
    list_shortlist,
    rebuild_shortlist,
    register_decision,
)
from src.services.staging_service import (
    get_distinct_coatings,
    get_distinct_suppliers,
    list_staging_quotes,
    set_needs_manual_review,
    set_review_status,
    staging_summary,
)
from src.services.reporting_service import (
    generate_monthly_report,
    generate_savings_report,
    generate_sourcing_report,
    list_export_files,
)
from src.utils.db import connect, get_db_path


def clear_cache() -> None:
    st.cache_data.clear()

@st.cache_data(ttl=30)
def load_dashboard_snapshot() -> dict:
    with connect() as conn:
        return dashboard_snapshot(conn)

@st.cache_data(ttl=30)
def get_database_path_text() -> str:
    return str(get_db_path())


@st.cache_data(ttl=30)
def load_staging_summary() -> list[dict]:
    with connect() as conn:
        return staging_summary(conn)


@st.cache_data(ttl=30)
def load_supplier_options() -> list[str]:
    with connect() as conn:
        return get_distinct_suppliers(conn)


@st.cache_data(ttl=30)
def load_coating_options() -> list[str]:
    with connect() as conn:
        return get_distinct_coatings(conn)


@st.cache_data(ttl=30)
def load_staging_quotes(
    supplier_code: str | None = None,
    review_status: str | None = None,
    coating: str | None = None,
    thickness_min: float | None = None,
    thickness_max: float | None = None,
    max_price: float | None = None,
) -> list[dict]:
    with connect() as conn:
        rows = list_staging_quotes(
            conn,
            supplier_code=supplier_code,
            review_status=review_status,
            coating=coating,
            thickness_min=thickness_min,
            thickness_max=thickness_max,
            max_price=max_price,
        )
        return [row.to_dict() for row in rows]


def update_staging_review_status(quote_ids: list[int], status: str) -> int:
    with connect() as conn:
        updated = set_review_status(conn, quote_ids, status)

    clear_cache()
    return updated


def update_staging_manual_review_flag(
    quote_ids: list[int],
    needs_manual_review: int,
) -> int:
    with connect() as conn:
        updated = set_needs_manual_review(
            conn,
            quote_ids,
            needs_manual_review,
        )

    clear_cache()
    return updated

@st.cache_data(ttl=30)
def load_approved_unmatched_quotes() -> list[dict]:
    with connect() as conn:
        rows = list_approved_unmatched(conn)
        return [row.to_dict() for row in rows]


@st.cache_data(ttl=30)
def load_match_candidates(
    quote_id: int,
    top_n: int = 5,
    min_score: float = 20.0,
) -> list[dict]:
    with connect() as conn:
        rows = find_candidates(
            conn,
            quote_id=quote_id,
            top_n=top_n,
            min_score=min_score,
        )
        return [row.to_dict() for row in rows]


def assign_match_action(quote_id: int, request_id: int) -> None:
    with connect() as conn:
        assign_match(conn, quote_id=quote_id, request_id=request_id)

    clear_cache()


def promote_quote_to_core_action(quote_id: int) -> int:
    with connect() as conn:
        core_quote_id = promote_to_core(conn, quote_id=quote_id)

    clear_cache()
    return core_quote_id


def assign_and_promote_action(quote_id: int, request_id: int) -> int:
    with connect() as conn:
        assign_match(conn, quote_id=quote_id, request_id=request_id)
        core_quote_id = promote_to_core(conn, quote_id=quote_id)

    clear_cache()
    return core_quote_id


@st.cache_data(ttl=30)
def load_shortlist_summary(only_with_alternatives: bool = False) -> list[dict]:
    with connect() as conn:
        rows = list_shortlist(
            conn,
            only_with_alternatives=only_with_alternatives,
        )
        return [row.to_dict() for row in rows]


@st.cache_data(ttl=30)
def load_request_core_quotes(request_id: int) -> list[dict]:
    with connect() as conn:
        rows = get_request_quotes(conn, request_id)
        return [row.to_dict() for row in rows]


def rebuild_shortlist_action() -> int:
    with connect() as conn:
        total = rebuild_shortlist(conn)

    clear_cache()
    return total


def register_decision_action(
    request_id: int,
    selected_quote_id: int,
    reason: str,
    decided_by: str,
) -> int:
    with connect() as conn:
        decision_id = register_decision(
            conn,
            request_id=request_id,
            selected_quote_id=selected_quote_id,
            reason=reason,
            decided_by=decided_by,
        )

    clear_cache()
    return decision_id


@st.cache_data(ttl=30)
def load_export_files() -> list[dict]:
    return list_export_files()


def generate_sourcing_report_action() -> dict:
    result = generate_sourcing_report()
    clear_cache()
    return result


def generate_savings_report_action() -> dict:
    result = generate_savings_report()
    clear_cache()
    return result


def generate_monthly_report_action(month: str) -> dict:
    result = generate_monthly_report(month)
    clear_cache()
    return result

@st.cache_data(ttl=30)
def load_db_status_snapshot() -> dict:
    with connect() as conn:
        return db_status_snapshot(conn)


def run_system_check_action(check_name: str) -> dict:
    result = run_system_check(check_name)
    clear_cache()
    return result

@st.cache_data(ttl=30)
def load_monthly_matrix_records(
    only_with_alternatives: bool = False,
    only_pdf_best: bool = False,
    status: str | None = None,
    search: str | None = None,
) -> list[dict]:
    from src.services.matrix_service import list_monthly_matrix

    with connect() as conn:
        return list_monthly_matrix(
            conn,
            only_with_alternatives=only_with_alternatives,
            only_pdf_best=only_pdf_best,
            status=status,
            search=search,
        )


@st.cache_data(ttl=30)
def load_monthly_matrix_summary(
    only_with_alternatives: bool = False,
    only_pdf_best: bool = False,
    status: str | None = None,
    search: str | None = None,
) -> dict:
    from src.services.matrix_service import list_monthly_matrix, matrix_summary

    with connect() as conn:
        records = list_monthly_matrix(
            conn,
            only_with_alternatives=only_with_alternatives,
            only_pdf_best=only_pdf_best,
            status=status,
            search=search,
        )

    return matrix_summary(records)


@st.cache_data(ttl=30)
def load_monthly_matrix_supplier_codes() -> list[str]:
    from src.services.matrix_service import list_matrix_supplier_codes

    with connect() as conn:
        return list_matrix_supplier_codes(conn)


@st.cache_data(ttl=30)
def load_matrix_request_quotes(request_id: int) -> list:
    from src.services.shortlist_service import get_request_quotes

    with connect() as conn:
        return get_request_quotes(conn, request_id)


def register_matrix_decision(
    request_id: int,
    selected_quote_id: int,
    reason: str,
    decided_by: str,
) -> int:
    from src.services.shortlist_service import register_decision

    with connect() as conn:
        decision_id = register_decision(
            conn,
            request_id=request_id,
            selected_quote_id=selected_quote_id,
            reason=reason,
            decided_by=decided_by,
        )

    clear_cache()
    return decision_id


def rebuild_monthly_matrix() -> int:
    from src.services.shortlist_service import rebuild_shortlist

    with connect() as conn:
        result = rebuild_shortlist(conn)

    clear_cache()
    return result

@st.cache_data(ttl=30)
def load_supplier_documents(limit: int = 100) -> list:
    from src.services.supplier_document_service import list_supplier_documents

    with connect() as conn:
        return list_supplier_documents(conn, limit=limit)


@st.cache_data(ttl=30)
def load_supplier_price_freshness() -> list:
    from src.services.supplier_document_service import supplier_price_freshness

    with connect() as conn:
        return supplier_price_freshness(conn)


def save_supplier_document_upload(
    file_bytes: bytes,
    filename: str,
    supplier_code: str,
    uploaded_by: str | None = None,
    notes: str | None = None,
) -> int:
    from src.services.supplier_document_service import save_uploaded_supplier_document

    with connect() as conn:
        document_id = save_uploaded_supplier_document(
            conn,
            file_bytes=file_bytes,
            filename=filename,
            supplier_code=supplier_code,
            uploaded_by=uploaded_by,
            notes=notes,
        )

    clear_cache()
    return document_id

