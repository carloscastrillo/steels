from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.ui.components.monthly_matrix import render_monthly_matrix_section
from src.ui.components.feedback import run_safe_action
from src.ui.components.risk_indicators import (
    add_core_quote_risk_columns,
    add_shortlist_risk_columns,
    render_quote_risk_alert,
)
from src.ui.components.db_session import (
    assign_and_promote_action,
    assign_match_action,
    clear_cache,
    load_approved_unmatched_quotes,
    load_match_candidates,
    load_request_core_quotes,
    load_shortlist_summary,
    promote_quote_to_core_action,
    rebuild_shortlist_action,
    register_decision_action,
)
from src.ui.components.filters import format_eur, format_eur_t
from src.ui.components.theme import inject_theme, page_header

st.set_page_config(page_title="Matriz", page_icon="📊", layout="wide")

inject_theme()

page_header(
    "Matriz — Ejercicio mensual",
    "Vista mensual de solicitudes y mejores opciones por proveedor. "
    "Datos calculados con los precios disponibles más recientes.",
)


render_monthly_matrix_section()

st.divider()
st.subheader("Vista operativa anterior")
st.caption("Se mantiene temporalmente como soporte mientras validamos la nueva matriz mensual.")

STATUS_LABELS = {
    "pending_review": "Pendiente de decisión",
    "awarded": "Adjudicado",
    "cancelled": "Cancelado",
    "open": "Abierto",
}

SOURCE_LABELS = {
    "BOSS": "Matriz",
    "QUOTE": "PDF proveedor",
}


def _status_label(value) -> str:
    return STATUS_LABELS.get(str(value), str(value) if value else "-")


def _source_label(value) -> str:
    return SOURCE_LABELS.get(str(value).upper(), str(value) if value else "-")


with st.sidebar:
    st.header("Filtros")

    only_with_alternatives = st.toggle(
        "Solo con alternativa real",
        value=False,
        help="Muestra únicamente solicitudes con segunda opción disponible.",
    )

    only_quote_source = st.toggle(
        "Solo mejor opción desde PDF",
        value=False,
        help="Solicitudes cuya mejor opción procede de un PDF de proveedor.",
    )

    st.divider()

    if st.button("Actualizar datos", width="stretch"):
        clear_cache()
        st.rerun()


rows = load_shortlist_summary(only_with_alternatives=only_with_alternatives)
df = pd.DataFrame(rows)
df = add_shortlist_risk_columns(df)

if df.empty:
    st.info("No hay solicitudes para mostrar en la matriz.")
    st.stop()

if only_quote_source:
    df = df[df["best_source"] == "QUOTE"]
    if df.empty:
        st.info("Ninguna solicitud tiene su mejor opción desde PDF de proveedor.")
        st.stop()

total_requests = len(df)
with_second = int(df["second_option_code"].notna().sum())
quote_best = int((df["best_source"] == "QUOTE").sum())
total_savings = df["savings_total_vs_am_spot"].fillna(0).sum()
total_tons = df["requested_tons"].fillna(0).sum()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Solicitudes", total_requests)
col2.metric("Toneladas", f"{total_tons:,.0f}".replace(",", "."))
col3.metric("Con alternativa", with_second)
col4.metric("Mejor opción desde PDF", quote_best)
col5.metric("Ahorro potencial", format_eur(total_savings))

st.divider()

rebuild_col1, rebuild_col2 = st.columns([1, 3])

with rebuild_col1:
    if st.button("Recalcular matriz", width="stretch"):
        st.session_state["confirm_rebuild_shortlist"] = True

with rebuild_col2:
    if st.session_state.get("confirm_rebuild_shortlist"):
        st.warning(
            "Se recalculará la matriz con las opciones de la matriz histórica "
            "y los precios de proveedor válidos para cálculo."
        )

        confirm_a, confirm_b = st.columns([1, 1])

        with confirm_a:
            if st.button("Confirmar recálculo", type="primary", width="stretch"):
                total = rebuild_shortlist_action()
                st.session_state.pop("confirm_rebuild_shortlist", None)
                st.success(f"Matriz recalculada: {total} solicitudes.")
                st.rerun()

        with confirm_b:
            if st.button("Cancelar", width="stretch"):
                st.session_state.pop("confirm_rebuild_shortlist", None)
                st.rerun()

st.subheader("Solicitudes del mes")

table_df = df.copy()

table_df["material"] = (
    table_df["product"].fillna("")
    + " | "
    + table_df["grade"].fillna("")
    + " | "
    + table_df["thickness_mm"].map(lambda value: "-" if pd.isna(value) else f"{float(value):.3f}")
    + " x "
    + table_df["width_mm"].map(lambda value: "-" if pd.isna(value) else f"{float(value):.0f}")
)

table_df["best_source_view"] = table_df["best_source"].map(_source_label)
table_df["status_view"] = table_df["status"].map(_status_label)
table_df["best_unit_cost_view"] = table_df["best_unit_cost"].map(format_eur_t)
table_df["second_unit_cost_view"] = table_df["second_unit_cost"].map(format_eur_t)
table_df["am_spot_unit_cost_view"] = table_df["am_spot_unit_cost"].map(format_eur_t)
table_df["delta_view"] = table_df["delta_best_vs_am_spot"].map(format_eur_t)
table_df["savings_view"] = table_df["savings_total_vs_am_spot"].map(format_eur)

display_columns = [
    "our_ref",
    "client_name",
    "material",
    "requested_tons",
    "best_option_code",
    "best_supplier_name",
    "best_source_view",
    "best_unit_cost_view",
    "second_option_code",
    "second_unit_cost_view",
    "am_spot_unit_cost_view",
    "delta_view",
    "savings_view",
    "status_view",
]

display_df = table_df[display_columns].rename(columns={
    "our_ref": "Ref",
    "client_name": "Cliente",
    "material": "Material",
    "requested_tons": "Toneladas",
    "best_option_code": "Mejor opción",
    "best_supplier_name": "Proveedor",
    "best_source_view": "Origen",
    "best_unit_cost_view": "Precio €/t",
    "second_option_code": "Segunda opción",
    "second_unit_cost_view": "Precio 2ª €/t",
    "am_spot_unit_cost_view": "AM Spot €/t",
    "delta_view": "Ahorro €/t",
    "savings_view": "Ahorro total",
    "status_view": "Estado",
})


def highlight_pdf_best(row):
    if row["Origen"] == "PDF proveedor":
        return ["background-color: #1E3A5F"] * len(row)
    return [""] * len(row)


st.dataframe(
    display_df.style.apply(highlight_pdf_best, axis=1),
    width="stretch",
    hide_index=True,
)

st.caption("Las filas resaltadas tienen su mejor opción en un PDF de proveedor actualizado.")

st.divider()

request_options = df["request_id"].astype(int).tolist()

selected_request_id = st.selectbox(
    "Selecciona una solicitud para ver el detalle",
    request_options,
    format_func=lambda request_id: (
        f"{df.loc[df['request_id'] == request_id, 'our_ref'].iloc[0]} | "
        f"{df.loc[df['request_id'] == request_id, 'client_name'].iloc[0]}"
    ),
)

selected = df[df["request_id"] == selected_request_id].iloc[0].to_dict()
core_quotes = load_request_core_quotes(int(selected_request_id))
quotes_df = pd.DataFrame(core_quotes)
quotes_df = add_core_quote_risk_columns(quotes_df)

st.subheader("Detalle de la solicitud")

detail_col1, detail_col2, detail_col3 = st.columns(3)

with detail_col1:
    st.markdown("#### Solicitud")
    st.write(f"Ref: {selected.get('our_ref')}")
    st.write(f"Cliente: {selected.get('client_name')}")
    st.write(f"Producto: {selected.get('product')}")
    st.write(f"Calidad: {selected.get('grade')}")
    st.write(f"Dimensiones: {selected.get('thickness_mm')} x {selected.get('width_mm')}")
    st.write(f"Toneladas: {selected.get('requested_tons')}")
    st.write(f"Estado: {_status_label(selected.get('status'))}")

with detail_col2:
    st.markdown("#### Comparativa")
    st.write(
        f"Mejor: {selected.get('best_option_code')} | "
        f"{format_eur_t(selected.get('best_unit_cost'))}"
    )
    st.write(f"Origen: {_source_label(selected.get('best_source'))}")
    st.write(
        f"Segunda: {selected.get('second_option_code') or '-'} | "
        f"{format_eur_t(selected.get('second_unit_cost'))}"
    )
    st.write(f"Tercera: {selected.get('third_option_code') or '-'}")
    st.write(f"AM Spot: {format_eur_t(selected.get('am_spot_unit_cost'))}")

with detail_col3:
    st.markdown("#### Ahorro")
    st.metric("Ahorro €/t vs AM Spot", format_eur_t(selected.get("delta_best_vs_am_spot")))
    st.metric("Ahorro total", format_eur(selected.get("savings_total_vs_am_spot")))

st.markdown("#### Precios de proveedor validados para esta solicitud")

if quotes_df.empty:
    st.info("Esta solicitud no tiene precios de proveedor validados todavía.")
else:
    quotes_display = quotes_df.copy()
    quotes_display["total_price_per_ton"] = quotes_display["total_price_per_ton"].map(format_eur_t)
    quotes_display["total_estimated_cost"] = quotes_display["total_estimated_cost"].map(format_eur)

    st.dataframe(quotes_display, width="stretch", hide_index=True)

st.divider()

st.subheader("Registrar decisión de compra")

if quotes_df.empty:
    st.warning(
        "No hay precios de proveedor validados para registrar una decisión "
        "sobre esta solicitud."
    )
else:
    quote_options = quotes_df["id"].astype(int).tolist()

    selected_quote_id = st.selectbox(
        "Precio seleccionado",
        quote_options,
        format_func=lambda quote_id: (
            f"{quotes_df.loc[quotes_df['id'] == quote_id, 'supplier_code'].iloc[0]} | "
            f"{format_eur_t(quotes_df.loc[quotes_df['id'] == quote_id, 'total_price_per_ton'].iloc[0])}"
        ),
    )

    reason = st.text_area("Motivo", value="best_price", height=90)
    decided_by = st.text_input("Decidido por", value="manual_user")

    selected_quote_row = quotes_df[quotes_df["id"] == selected_quote_id].iloc[0].to_dict()

    if int(selected_quote_row.get("needs_manual_review") or 0) == 1:
        st.warning(
            "El precio seleccionado requiere revisión. "
            "Revísalo en 'Revisión de Precios de Proveedores' antes de decidir."
        )

    already_awarded = selected.get("status") == "awarded"

    if already_awarded:
        st.info("Esta solicitud ya está adjudicada. No se registrará una nueva decisión.")

    if st.button(
        "Registrar decisión",
        type="primary",
        width="stretch",
        disabled=already_awarded,
    ):
        if not reason.strip():
            st.error("El motivo no puede estar vacío.")
        elif not decided_by.strip():
            st.error("El campo 'decidido por' no puede estar vacío.")
        else:
            run_safe_action(
                lambda: register_decision_action(
                    request_id=int(selected_request_id),
                    selected_quote_id=int(selected_quote_id),
                    reason=reason.strip(),
                    decided_by=decided_by.strip(),
                ),
                success_message="Decisión registrada correctamente.",
                error_message=(
                    "No se pudo registrar la decisión. "
                    "Revisa si la solicitud ya está adjudicada."
                ),
                rerun=True,
            )

st.divider()

# ------------------------------------------------------------------
# Asignación avanzada: conectar precios de proveedor aprobados con
# solicitudes (antiguo Matching). Flujo técnico, plegado por defecto.
# ------------------------------------------------------------------

with st.expander("Asignación avanzada de precio proveedor (técnico)", expanded=False):
    st.caption(
        "Conecta precios de proveedor aprobados con solicitudes de compra. "
        "Los precios deben estar aprobados en 'Revisión de Precios de Proveedores'."
    )

    unmatched_quotes = load_approved_unmatched_quotes()

    if not unmatched_quotes:
        st.success("No hay precios aprobados pendientes de asignar.")
    else:
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            top_n = st.slider(
                "Candidatos por precio", min_value=1, max_value=15, value=5, step=1,
                key="mx_top_n",
            )
        with m_col2:
            min_score = st.slider(
                "Compatibilidad mínima", min_value=0.0, max_value=100.0,
                value=20.0, step=5.0, key="mx_min_score",
            )

        mq_df = pd.DataFrame(unmatched_quotes)
        mq_options = mq_df["id"].astype(int).tolist()

        sel_quote_id = st.selectbox(
            "Precio de proveedor aprobado",
            mq_options,
            format_func=lambda quote_id: (
                f"#{quote_id} | "
                f"{mq_df.loc[mq_df['id'] == quote_id, 'supplier_code'].iloc[0]} | "
                f"{mq_df.loc[mq_df['id'] == quote_id, 'extracted_grade'].iloc[0]} | "
                f"{mq_df.loc[mq_df['id'] == quote_id, 'price_per_ton'].iloc[0]} €/t"
            ),
            key="mx_quote_select",
        )

        sel_quote = mq_df[mq_df["id"] == sel_quote_id].iloc[0].to_dict()
        render_quote_risk_alert(sel_quote)

        candidates = load_match_candidates(
            quote_id=int(sel_quote_id),
            top_n=int(top_n),
            min_score=float(min_score),
        )

        if not candidates:
            st.warning("No hay solicitudes compatibles por encima de la compatibilidad mínima.")
        else:
            cand_df = pd.DataFrame(candidates)

            cand_view = cand_df.copy()
            cand_view["grade_score"] = cand_view["breakdown"].map(
                lambda value: value.get("grade_score") if isinstance(value, dict) else None
            )
            cand_view["blocked"] = cand_view["breakdown"].map(
                lambda value: value.get("blocked") if isinstance(value, dict) else None
            )

            st.dataframe(
                cand_view[[
                    "score", "request_id", "our_ref", "client_name",
                    "product", "grade", "thickness_mm", "width_mm",
                    "tons", "status",
                ]],
                width="stretch",
                hide_index=True,
            )

            cand_options = cand_df["request_id"].astype(int).tolist()

            sel_req_id = st.selectbox(
                "Solicitud candidata",
                cand_options,
                format_func=lambda request_id: (
                    f"{cand_df.loc[cand_df['request_id'] == request_id, 'our_ref'].iloc[0]} | "
                    f"{cand_df.loc[cand_df['request_id'] == request_id, 'client_name'].iloc[0]} | "
                    f"compatibilidad {cand_df.loc[cand_df['request_id'] == request_id, 'score'].iloc[0]:.0f}"
                ),
                key="mx_request_select",
            )

            sel_cand = cand_df[cand_df["request_id"] == sel_req_id].iloc[0].to_dict()
            breakdown = sel_cand.get("breakdown") or {}

            b1, b2, b3 = st.columns(3)
            b1.metric("Compatibilidad calidad", breakdown.get("grade_score", 0))
            b2.metric("Compatibilidad espesor", breakdown.get("thickness_score", 0))
            b3.metric("Compatibilidad ancho", breakdown.get("width_score", 0))

            if breakdown.get("grade_score", 0) <= 0 or breakdown.get("blocked"):
                st.error("Candidato bloqueado por falta de compatibilidad de calidad.")
            else:
                confirm_key = f"mx_confirm_{sel_quote_id}_{sel_req_id}"

                ma_col1, ma_col2 = st.columns(2)

                with ma_col1:
                    if st.button("Asignar a la solicitud", width="stretch", key="mx_assign"):
                        st.session_state[confirm_key] = "assign"

                with ma_col2:
                    if st.button(
                        "Asignar y usar en la matriz",
                        type="primary",
                        width="stretch",
                        key="mx_assign_promote",
                    ):
                        st.session_state[confirm_key] = "assign_promote"

                pending_action = st.session_state.get(confirm_key)

                if pending_action:
                    if pending_action == "assign":
                        action_text = "asignar este precio a la solicitud seleccionada"
                    else:
                        action_text = (
                            "asignar este precio y hacerlo disponible en la matriz"
                        )

                    st.warning(
                        f"Confirmación: vas a {action_text}.\n\n"
                        f"Precio #{sel_quote_id} → Solicitud #{sel_req_id}"
                    )

                    cc1, cc2 = st.columns(2)

                    with cc1:
                        if st.button("Confirmar", type="primary", width="stretch", key="mx_confirm_btn"):
                            if pending_action == "assign":
                                assign_match_action(
                                    quote_id=int(sel_quote_id),
                                    request_id=int(sel_req_id),
                                )
                                st.success("Precio asignado correctamente.")
                            else:
                                core_id = assign_and_promote_action(
                                    quote_id=int(sel_quote_id),
                                    request_id=int(sel_req_id),
                                )
                                st.success(f"Precio asignado y disponible en la matriz (ref. {core_id}).")
                                rebuilt = rebuild_shortlist_action()
                                st.info(f"Matriz recalculada: {rebuilt} solicitudes.")

                            st.session_state.pop(confirm_key, None)
                            st.rerun()

                    with cc2:
                        if st.button("Cancelar", width="stretch", key="mx_cancel_btn"):
                            st.session_state.pop(confirm_key, None)
                            st.rerun()
