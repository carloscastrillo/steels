from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def review_status_label(value: Any) -> str:
    status = _as_text(value).lower()

    if status == "approved":
        return "🟢 Aprobado"
    if status == "rejected":
        return "🔴 Rechazado"
    if status == "pending":
        return "🟡 Pendiente de decisión"

    return f"⚪ {value}" if value else "⚪ Sin estado"


def manual_review_label(value: Any) -> str:
    return "🔴 Requiere revisión" if _as_int(value, 1) == 1 else "🟢 Válido para cálculo"


def match_label(value: Any) -> str:
    if value is None or str(value).strip() in {"", "nan", "None"}:
        return "🟡 Sin asignar"
    return f"🟢 Asignado #{value}"


def source_label(value: Any) -> str:
    source = _as_text(value).upper()

    if source == "QUOTE":
        return "🟣 PDF proveedor"
    if source == "BOSS":
        return "🔵 Matriz"
    if not source:
        return "⚪ Sin origen"

    return f"⚪ {source}"


def request_status_label(value: Any) -> str:
    status = _as_text(value).lower()

    if status == "awarded":
        return "🟢 Adjudicado"
    if status == "cancelled":
        return "🔴 Cancelado"
    if status in {"pending_review", "pending"}:
        return "🟡 Pendiente de decisión"

    return f"⚪ {value}" if value else "⚪ Sin estado"


def add_staging_risk_columns(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()

    if "review_status" in output.columns:
        output["Estado revisión"] = output["review_status"].apply(review_status_label)

    if "needs_manual_review" in output.columns:
        output["Riesgo cálculo"] = output["needs_manual_review"].apply(manual_review_label)

    if "matched_sourcing_request_id" in output.columns:
        output["Estado match"] = output["matched_sourcing_request_id"].apply(match_label)
    elif "matched_request_id" in output.columns:
        output["Estado match"] = output["matched_request_id"].apply(match_label)

    visual_cols = [
        "Estado revisión",
        "Riesgo cálculo",
        "Estado match",
    ]

    front_cols = [
        col
        for col in ["Seleccionar", "id", "ID", *visual_cols]
        if col in output.columns
    ]

    remaining_cols = [
        col
        for col in output.columns
        if col not in front_cols
    ]

    return output[front_cols + remaining_cols]


def add_shortlist_risk_columns(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()

    if "best_source" in output.columns:
        output["Origen visual"] = output["best_source"].apply(source_label)

    if "status" in output.columns:
        output["Estado request"] = output["status"].apply(request_status_label)

    return output


def add_core_quote_risk_columns(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()

    if "needs_manual_review" in output.columns:
        output["Riesgo cálculo"] = output["needs_manual_review"].apply(manual_review_label)

    if "source_type" in output.columns:
        output["Origen quote"] = output["source_type"].apply(lambda value: "🟣 PDF" if _as_text(value).lower() == "pdf" else _as_text(value))

    return output


def render_staging_quote_risk_alert(
    review_status: Any,
    needs_manual_review: Any,
    matched_request_id: Any = None,
) -> None:
    if _as_text(review_status).lower() == "pending":
        st.warning("Este precio todavía está pendiente de aprobación.")

    if _as_int(needs_manual_review, 1) == 1:
        st.error("Este precio requiere revisión. Aunque se apruebe, no entra en la matriz ni en el cálculo de ahorro hasta marcarlo como válido para cálculo.")

    if matched_request_id is None or str(matched_request_id).strip() in {"", "nan", "None"}:
        st.info("Este precio todavía no está asignado a ninguna solicitud.")

def get_field(item: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(item, dict) and name in item:
            return item.get(name)

        if hasattr(item, name):
            return getattr(item, name)

    return default


def render_quote_risk_alert(quote: Any) -> None:
    render_staging_quote_risk_alert(
        review_status=get_field(quote, "review_status", default=None),
        needs_manual_review=get_field(quote, "needs_manual_review", default=1),
        matched_request_id=get_field(
            quote,
            "matched_request_id",
            "matched_sourcing_request_id",
            default=None,
        ),
    )

