from __future__ import annotations

import streamlit as st


REVIEW_STATUS_OPTIONS = ["Todos", "pending", "approved", "rejected"]


def supplier_selector(
    suppliers: list[str],
    label: str = "Proveedor",
    key: str | None = None,
) -> str | None:
    selected = st.selectbox(
        label,
        ["Todos", *suppliers],
        key=key,
    )

    return None if selected == "Todos" else selected


def review_status_selector(
    label: str = "Estado revisión",
    key: str | None = None,
) -> str | None:
    selected = st.selectbox(
        label,
        REVIEW_STATUS_OPTIONS,
        key=key,
    )

    return None if selected == "Todos" else selected


def coating_text_filter(
    label: str = "Coating / grade contiene",
    key: str | None = None,
) -> str | None:
    value = st.text_input(label, key=key).strip()
    return value or None


def thickness_range_filter(
    label: str = "Rango de espesor",
    min_value: float = 0.0,
    max_value: float = 5.0,
    default: tuple[float, float] = (0.0, 5.0),
    key: str | None = None,
) -> tuple[float | None, float | None]:
    selected_min, selected_max = st.slider(
        label,
        min_value=min_value,
        max_value=max_value,
        value=default,
        step=0.01,
        key=key,
    )

    return selected_min, selected_max


def max_price_filter(
    label: str = "Precio máximo €/t",
    key: str | None = None,
) -> float | None:
    value = st.number_input(
        label,
        min_value=0.0,
        value=0.0,
        step=10.0,
        key=key,
    )

    return None if value <= 0 else float(value)


def format_eur_t(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):,.2f} €/t"


def format_eur(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):,.2f} €"