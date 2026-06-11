from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.ui.components.db_session import (
    load_matrix_request_quotes,
    load_monthly_matrix_records,
    load_monthly_matrix_summary,
    rebuild_monthly_matrix,
    register_matrix_decision,
)
from src.ui.components.feedback import run_safe_action
from src.ui.components.filters import format_eur


CORE_COLUMNS = [
    "request_id",
    "ref",
    "cliente",
    "producto",
    "grado",
    "espesor_mm",
    "ancho_mm",
    "toneladas",
    "falta_comprar_t",
    "fecha",
    "AM Spot €/t",
    "AM PDF €/t",
    "GALMED €/t",
    "LEON €/t",
    "BAO DDP HL €/t",
    "BAO CFRFO €/t",
    "Base equiv. €/t",
    "mejor_proveedor",
    "mejor_eur_t",
    "am_spot_eur_t",
    "ahorro_eur_t",
    "ahorro_total",
    "origen_mejor",
    "estado",
]


def _format_number(value: Any, decimals: int = 2) -> str:
    if value is None or value == "":
        return "-"

    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    return f"{number:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_tons(value: Any) -> str:
    return f"{_format_number(value, 0)} t"


def _display_records(records: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)

    if df.empty:
        return df

    ordered_columns = [
        col
        for col in CORE_COLUMNS
        if col in df.columns
    ]

    price_columns = [
        col
        for col in df.columns
        if col.endswith("€/t") and col not in ordered_columns
    ]

    remaining_columns = [
        col
        for col in df.columns
        if col not in ordered_columns and col not in price_columns and not col.endswith("origen")
    ]

    df = df[ordered_columns + price_columns + remaining_columns]

    rename_map = {
        "request_id": "ID",
        "ref": "Ref",
        "cliente": "Cliente",
        "producto": "Producto",
        "grado": "Grado",
        "espesor_mm": "Espesor",
        "ancho_mm": "Ancho",
        "toneladas": "Toneladas",
        "falta_comprar_t": "Falta comprar",
        "fecha": "Fecha",
        "mejor_proveedor": "Mejor proveedor",
        "mejor_eur_t": "Mejor €/t",
        "am_spot_eur_t": "AM Spot ref.",
        "ahorro_eur_t": "Ahorro €/t",
        "ahorro_total": "Ahorro total",
        "origen_mejor": "Origen",
        "estado": "Estado",
    }

    return df.rename(columns=rename_map)


def _style_matrix(df: pd.DataFrame):
    def style_row(row):
        styles = [""] * len(row)

        origen = str(row.get("Origen", ""))
        estado = str(row.get("Estado", ""))
        ahorro = row.get("Ahorro total")

        for idx, col in enumerate(row.index):
            if col == "Origen" and "PDF" in origen:
                styles[idx] = "background-color: #1E3A5F; color: #E6F2FF; font-weight: 700;"
            elif col == "Estado" and "Adjudicado" in estado:
                styles[idx] = "background-color: #14532D; color: #DCFCE7; font-weight: 700;"
            elif col == "Estado" and "Pendiente" in estado:
                styles[idx] = "background-color: #78350F; color: #FEF3C7; font-weight: 700;"
            elif col == "Ahorro total":
                try:
                    if float(ahorro or 0) > 0:
                        styles[idx] = "color: #86EFAC; font-weight: 700;"
                except Exception:
                    pass
            elif col == "Mejor €/t":
                styles[idx] = "font-weight: 700;"
            elif col in {"AM Spot €/t", "AM PDF €/t", "GALMED €/t", "LEON €/t", "BAO DDP HL €/t", "BAO CFRFO €/t", "Base equiv. €/t"}:
                styles[idx] = "background-color: rgba(59, 130, 196, 0.10);"

        return styles

    return df.style.apply(style_row, axis=1)


def render_monthly_matrix_section() -> None:
    st.subheader("Matriz mensual de compra")
    st.caption(
        "Vista tipo matriz: solicitudes del mes, precios por proveedor, mejor opción, origen y ahorro estimado."
    )

    with st.container(border=True):
        left, mid1, mid2, right = st.columns([2.5, 1.4, 1.4, 1.4])

        with left:
            search = st.text_input(
                "Buscar",
                placeholder="Cliente, referencia, producto, grado...",
                key="matrix_search",
            )

        with mid1:
            only_with_alternatives = st.toggle(
                "Solo con alternativa",
                value=False,
                key="matrix_only_alt",
            )

        with mid2:
            only_pdf_best = st.toggle(
                "Solo mejor desde PDF",
                value=False,
                key="matrix_only_pdf",
            )

        with right:
            status_filter = st.selectbox(
                "Estado",
                options=[
                    "Todos",
                    "pending_review",
                    "awarded",
                    "cancelled",
                ],
                format_func=lambda value: {
                    "Todos": "Todos",
                    "pending_review": "Pendiente de decisión",
                    "awarded": "Adjudicado",
                    "cancelled": "Cancelado",
                }.get(value, value),
                key="matrix_status",
            )

    status_value = None if status_filter == "Todos" else status_filter

    records = load_monthly_matrix_records(
        only_with_alternatives=only_with_alternatives,
        only_pdf_best=only_pdf_best,
        status=status_value,
        search=search,
    )

    summary = load_monthly_matrix_summary(
        only_with_alternatives=only_with_alternatives,
        only_pdf_best=only_pdf_best,
        status=status_value,
        search=search,
    )

    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    kpi1.metric("Solicitudes", int(summary.get("requests") or 0))
    kpi2.metric("Toneladas", _format_tons(summary.get("total_tons")))
    kpi3.metric("Falta comprar", _format_tons(summary.get("missing_tons")))
    kpi4.metric("Con alternativa", int(summary.get("with_alternatives") or 0))
    kpi5.metric("PDF proveedor", int(summary.get("pdf_best") or 0))
    kpi6.metric("Ahorro estimado", format_eur(summary.get("total_savings")))

    st.divider()

    if not records:
        st.info("No hay solicitudes para los filtros actuales.")
        return

    display_df = _display_records(records)

    st.dataframe(
        _style_matrix(display_df),
        width="stretch",
        hide_index=True,
    )

    st.caption(
        "Las columnas por proveedor muestran el mejor precio disponible por solicitud. "
        "El origen indica si la mejor opción viene de la Matriz o de un PDF de proveedor."
    )

    st.divider()

    st.subheader("Detalle de solicitud")

    options = {
        f"{item.get('ref')} · {item.get('cliente')} · {item.get('producto')} · {item.get('toneladas')} t": item
        for item in records
    }

    selected_label = st.selectbox(
        "Selecciona una solicitud",
        options=list(options.keys()),
        key="matrix_selected_request",
    )

    selected = options[selected_label]
    request_id = int(selected["request_id"])

    detail_left, detail_right = st.columns([1.2, 1])

    with detail_left:
        with st.container(border=True):
            st.markdown("#### Solicitud")
            st.write(f"**Ref:** {selected.get('ref')}")
            st.write(f"**Cliente:** {selected.get('cliente')}")
            st.write(f"**Producto:** {selected.get('producto')}")
            st.write(f"**Grado:** {selected.get('grado')}")
            st.write(f"**Dimensiones:** {selected.get('espesor_mm')} mm × {selected.get('ancho_mm')} mm")
            st.write(f"**Toneladas:** {_format_tons(selected.get('toneladas'))}")
            st.write(f"**Estado:** {selected.get('estado')}")

    with detail_right:
        with st.container(border=True):
            st.markdown("#### Mejor opción")
            st.metric("Proveedor", selected.get("mejor_proveedor") or "-")
            st.metric("Precio", format_eur(selected.get("mejor_eur_t")))
            st.metric("AM Spot", format_eur(selected.get("am_spot_eur_t")))
            st.metric("Ahorro total", format_eur(selected.get("ahorro_total")))
            st.write(f"**Origen:** {selected.get('origen_mejor') or '-'}")

    quotes = load_matrix_request_quotes(request_id)

    if quotes:
        st.markdown("#### Precios de proveedor validados para esta solicitud")

        quote_rows = []

        for quote in quotes:
            quote_rows.append({
                "ID": quote.id,
                "Proveedor": quote.supplier_name,
                "Código": quote.supplier_code,
                "Precio €/t": quote.total_price_per_ton,
                "Total": quote.total_estimated_cost,
                "Toneladas": quote.quoted_tons,
                "Revisión": "Requiere revisión" if quote.needs_manual_review else "Válido para cálculo",
                "Origen": quote.source_type,
            })

        quotes_df = pd.DataFrame(quote_rows)

        st.dataframe(
            quotes_df,
            width="stretch",
            hide_index=True,
        )

        already_awarded = selected.get("estado_raw") == "awarded"

        if already_awarded:
            st.info("Esta solicitud ya está adjudicada. No se registrará una nueva decisión.")
        else:
            st.markdown("#### Registrar decisión")

            valid_quotes = [
                quote
                for quote in quotes
                if not quote.needs_manual_review
            ]

            if not valid_quotes:
                st.warning("No hay precios válidos para cálculo en esta solicitud.")
            else:
                selected_quote = st.selectbox(
                    "Precio seleccionado",
                    options=valid_quotes,
                    format_func=lambda quote: f"{quote.supplier_name} · {format_eur(quote.total_price_per_ton)} · quote #{quote.id}",
                    key=f"matrix_decision_quote_{request_id}",
                )

                reason = st.text_area(
                    "Motivo",
                    value="best_price",
                    key=f"matrix_decision_reason_{request_id}",
                )

                decided_by = st.text_input(
                    "Decidido por",
                    value="",
                    key=f"matrix_decision_by_{request_id}",
                )

                if st.button(
                    "Registrar decisión",
                    type="primary",
                    key=f"matrix_register_decision_{request_id}",
                    width="stretch",
                ):
                    if not reason.strip():
                        st.error("El motivo no puede estar vacío.")
                    elif not decided_by.strip():
                        st.error("El campo 'decidido por' no puede estar vacío.")
                    else:
                        run_safe_action(
                            lambda: register_matrix_decision(
                                request_id=request_id,
                                selected_quote_id=int(selected_quote.id),
                                reason=reason.strip(),
                                decided_by=decided_by.strip(),
                            ),
                            success_message="Decisión registrada correctamente.",
                            error_message="No se pudo registrar la decisión.",
                            rerun=True,
                        )
    else:
        st.info("Esta solicitud no tiene precios PDF/core asociados. La comparativa se basa en opciones de la Matriz.")

    st.divider()

    with st.expander("Acciones de matriz", expanded=False):
        st.warning("Recalcular la matriz reconstruye la shortlist con las opciones disponibles actuales.")

        if st.button("Recalcular matriz", key="matrix_rebuild", width="stretch"):
            run_safe_action(
                rebuild_monthly_matrix,
                success_message="Matriz recalculada correctamente.",
                error_message="No se pudo recalcular la matriz.",
                rerun=True,
            )
