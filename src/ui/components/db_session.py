from __future__ import annotations

import streamlit as st

from src.services.shortlist_service import list_shortlist
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
def load_shortlist_summary(only_with_alternatives: bool = False) -> list[dict]:
    with connect() as conn:
        rows = list_shortlist(
            conn,
            only_with_alternatives=only_with_alternatives,
        )
        return [row.to_dict() for row in rows]