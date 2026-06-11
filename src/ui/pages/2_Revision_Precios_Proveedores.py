from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.ui.components.supplier_documents import render_supplier_documents_section
from src.ui.components.risk_indicators import add_staging_risk_columns

from src.ui.components.theme import inject_theme, page_header
from src.ui.components.db_session import (
    clear_cache,
    load_supplier_options,
    load_staging_quotes,
    update_staging_manual_review_flag,
    update_staging_review_status,
)

from src.ui.components.filters import (
    coating_text_filter,
    max_price_filter,
    review_status_selector,
    supplier_selector,
    thickness_range_filter,
)


st.set_page_config(page_title="Revisión de Precios", page_icon="📋", layout="wide")

inject_theme()

page_header(
    "Revisión de Precios de Proveedores",
    "Revisa los precios que llegan de proveedores antes de usarlos en la matriz.",
)


render_supplier_documents_section()

st.divider()
st.subheader("Precios detectados pendientes de revisión")
st.caption("Los precios extraídos de documentos existentes se revisan y validan aquí antes de usarse en la Matriz.")


suppliers = load_supplier_options()

with st.sidebar:
    st.header("Filtros")

    supplier_code = supplier_selector(
        suppliers,
        label="Proveedor",
        key="staging_supplier",
    )

    review_status = review_status_selector(
        label="Estado",
        key="staging_review_status",
    )

    coating = coating_text_filter(
        label="Coating / grade contiene",
        key="staging_coating",
    )

    thickness_min, thickness_max = thickness_range_filter(
        label="Espesor mm",
        min_value=0.0,
        max_value=5.0,
        default=(0.0, 5.0),
        key="staging_thickness",
    )

    max_price = max_price_filter(
        label="Precio máximo €/t",
        key="staging_max_price",
    )

    st.divider()

    if st.button("Limpiar caché", width="stretch"):
        clear_cache()
        st.rerun()


quotes = load_staging_quotes(
    supplier_code=supplier_code,
    review_status=review_status,
    coating=coating,
    thickness_min=thickness_min,
    thickness_max=thickness_max,
    max_price=max_price,
)

df = pd.DataFrame(quotes)
df = add_staging_risk_columns(df)


if df.empty:
    st.info("No hay precios de proveedor que cumplan los filtros actuales.")
    st.stop()

pending_count = int((df["review_status"] == "pending").sum())
approved_count = int((df["review_status"] == "approved").sum())
rejected_count = int((df["review_status"] == "rejected").sum())
matched_count = int(df["matched_request_id"].notna().sum())

manual_review_count = int((df["needs_manual_review"] == 1).sum())

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Filtradas", len(df))
col2.metric("Pendientes", pending_count)
col3.metric("Aprobadas", approved_count)
col4.metric("Rechazadas", rejected_count)
col5.metric("Con match", matched_count)
col6.metric("Revisión manual", manual_review_count)

st.divider()

display_df = df.copy()
display_df.insert(0, "seleccionar", False)

display_df["precio_eur_t"] = display_df["price_per_ton"].map(
    lambda value: "" if pd.isna(value) else f"{float(value):,.2f} €/t"
)

display_columns = [
    "seleccionar",
    "id",
    "supplier_code",
    "document",
    "coating_raw",
    "extracted_grade",
    "thickness_mm",
    "width_mm",
    "precio_eur_t",
    "review_status",
    "needs_manual_review",
    "matched_request_id",
]

display_df = display_df[display_columns]

st.subheader("Precios detectados")

edited_df = st.data_editor(
    display_df,
    width="stretch",
    hide_index=True,
    disabled=[
        "id",
        "supplier_code",
        "document",
        "coating_raw",
        "extracted_grade",
        "thickness_mm",
        "width_mm",
        "precio_eur_t",
        "review_status",
        "needs_manual_review",
        "matched_request_id",
    ],
    column_config={
        "seleccionar": st.column_config.CheckboxColumn(
            "Seleccionar",
            help="Marca filas para aprobar o rechazar.",
            default=False,
        ),
        "id": st.column_config.NumberColumn("ID", width="small"),
        "supplier_code": st.column_config.TextColumn("Proveedor"),
        "document": st.column_config.TextColumn("Documento"),
        "coating_raw": st.column_config.TextColumn("Coating raw"),
        "extracted_grade": st.column_config.TextColumn("Grade extraído"),
        "thickness_mm": st.column_config.NumberColumn("Espesor", format="%.3f"),
        "width_mm": st.column_config.NumberColumn("Ancho", format="%.3f"),
        "precio_eur_t": st.column_config.TextColumn("Precio €/t"),
        "review_status": st.column_config.TextColumn("Estado"),
        "needs_manual_review": st.column_config.NumberColumn("Manual review"),
        "matched_request_id": st.column_config.NumberColumn("Request match"),
    },
    key="staging_quotes_editor",
)

selected_ids = [
    int(row["id"])
    for _, row in edited_df.iterrows()
    if bool(row["seleccionar"])
]

st.caption(f"Filas seleccionadas: {len(selected_ids)}")

action_col1, action_col2, action_col3, action_col4 = st.columns([1, 1, 1.4, 1.4])

with action_col1:
    if st.button("Aprobar seleccionadas", disabled=not selected_ids, width="stretch"):
        updated = update_staging_review_status(selected_ids, "approved")
        st.success(f"Precios aprobados: {updated}")
        st.rerun()

with action_col2:
    if st.button("Rechazar seleccionadas", disabled=not selected_ids, width="stretch"):
        updated = update_staging_review_status(selected_ids, "rejected")
        st.success(f"Precios rechazados: {updated}")
        st.rerun()

with action_col3:
    if st.button("Validar para cálculo", disabled=not selected_ids, width="stretch"):
        updated = update_staging_manual_review_flag(selected_ids, 0)
        st.success(f"Precios marcados como válidos para cálculo: {updated}")
        st.rerun()

with action_col4:
    if st.button("Requiere revisión", disabled=not selected_ids, width="stretch"):
        updated = update_staging_manual_review_flag(selected_ids, 1)
        st.success(f"Precios marcados como requieren revisión: {updated}")
        st.rerun()


        
st.markdown("#### Acciones por lote sobre el filtro actual")

batch_col1, batch_col2, batch_col3, batch_col4 = st.columns(4)

with batch_col1:
    if st.button("Aprobar todo el filtro", disabled=len(df) == 0, width="stretch"):
        st.session_state["confirm_batch_action"] = "approved"

with batch_col2:
    if st.button("Rechazar todo el filtro", disabled=len(df) == 0, width="stretch"):
        st.session_state["confirm_batch_action"] = "rejected"

with batch_col3:
    if st.button("Validar filtro para cálculo", disabled=len(df) == 0, width="stretch"):
        st.session_state["confirm_batch_manual_review"] = 0

with batch_col4:
    if st.button("Filtro requiere revisión", disabled=len(df) == 0, width="stretch"):
        st.session_state["confirm_batch_manual_review"] = 1

batch_manual_review = st.session_state.get("confirm_batch_manual_review")

if batch_manual_review is not None:
    label = (
        "válidas para cálculo"
        if int(batch_manual_review) == 0
        else "requieren revisión manual"
    )

    st.warning(
        f"Vas a marcar {len(df)} quotes filtradas como '{label}'. "
        "Esta acción modifica la base de datos."
    )

    confirm_col1, confirm_col2 = st.columns([1, 1])

    with confirm_col1:
        if st.button("Confirmar cambio de revisión manual", type="primary", width="stretch"):
            ids = [int(value) for value in df["id"].tolist()]
            updated = update_staging_manual_review_flag(ids, int(batch_manual_review))
            st.session_state.pop("confirm_batch_manual_review", None)
            st.success(f"Precios actualizados: {updated}")
            st.rerun()

    with confirm_col2:
        if st.button("Cancelar cambio de revisión manual", width="stretch"):
            st.session_state.pop("confirm_batch_manual_review", None)
            st.rerun()

st.divider()

st.subheader("Ver origen del dato")

detail_ids = df["id"].astype(int).tolist()
selected_detail_id = st.selectbox(
    "Selecciona una quote para ver el origen del dato",
    detail_ids,
    format_func=lambda value: f"Quote #{value}",
)

detail_row = df[df["id"] == selected_detail_id].iloc[0].to_dict()

with st.expander("Ver raw snippet", expanded=True):
    st.write("Proveedor:", detail_row.get("supplier_code"))
    st.write("Documento:", detail_row.get("document"))
    st.write("Grade extraído:", detail_row.get("extracted_grade"))
    st.write("Coating raw:", detail_row.get("coating_raw"))
    st.code(detail_row.get("raw_snippet") or "(sin raw snippet)", language="text")