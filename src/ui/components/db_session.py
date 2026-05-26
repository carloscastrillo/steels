from __future__ import annotations

import streamlit as st

from src.services.shortlist_service import list_shortlist
from src.services.staging_service import (
    get_distinct_coatings,
    get_distinct_suppliers,
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
def load_shortlist_summary(only_with_alternatives: bool = False) -> list[dict]:
    with connect() as conn:
        rows = list_shortlist(
            conn,
            only_with_alternatives=only_with_alternatives,
        )
        return [row.to_dict() for row in rows]