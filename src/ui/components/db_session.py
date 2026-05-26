from __future__ import annotations

import streamlit as st

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
    set_review_status,
    staging_summary,
)
from src.utils.db import connect, get_db_path


def clear_cache() -> None:
    st.cache_data.clear()


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