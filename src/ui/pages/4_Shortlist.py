from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

from src.ui.components.feedback import run_safe_action, show_user_error
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.ui.components.db_session import (
    clear_cache,
    load_request_core_quotes,
    load_shortlist_summary,
    rebuild_shortlist_action,
    register_decision_action,
)
from src.ui.components.filters import format_eur, format_eur_t


st.set_page_config(page_title="Shortlist", page_icon="🏁", layout="wide")

st.title("Shortlist y decisión")
st.caption("Consulta de shortlist BOSS + QUOTE y registro de decisiones de compra.")

with st.sidebar:
    st.header("Filtros")

    only_with_alternatives = st.toggle(
        "Solo requests con alternativa real",
        value=False,
        help="Muestra únicamente requests con segunda opción disponible.",
    )

    st.divider()

    if st.button("Limpiar caché", width="stretch"):
        clear_cache()
        st.rerun()


rows = load_shortlist_summary(only_with_alternatives=only_with_alternatives)
df = pd.DataFrame(rows)

if df.empty:
    st.info("No hay shortlists para mostrar.")
    st.stop()


total_requests = len(df)
with_second = int(df["second_option_code"].notna().sum())
quote_best = int((df["best_source"] == "QUOTE").sum())
total_savings = df["savings_total_vs_am_spot"].fillna(0).sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Requests mostradas", total_requests)
col2.metric("Con segunda opción", with_second)
col3.metric("Best source QUOTE", quote_best)
col4.metric("Ahorro total", format_eur(total_savings))

st.divider()

rebuild_col1, rebuild_col2 = st.columns([1, 3])

with rebuild_col1:
    if st.button("Recalcular shortlist", width="stretch"):
        st.session_state["confirm_rebuild_shortlist"] = True

with rebuild_col2:
    if st.session_state.get("confirm_rebuild_shortlist"):
        st.warning("Se regenerará la shortlist con las opciones BOSS y las quotes core válidas.")

        confirm_a, confirm_b = st.columns([1, 1])

        with confirm_a:
            if st.button("Confirmar recálculo", type="primary", width="stretch"):
                total = rebuild_shortlist_action()
                st.session_state.pop("confirm_rebuild_shortlist", None)
                st.success(f"Shortlists regeneradas: {total}")
                st.rerun()

        with confirm_b:
            if st.button("Cancelar", width="stretch"):
                st.session_state.pop("confirm_rebuild_shortlist", None)
                st.rerun()

st.subheader("Resumen shortlist")

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

table_df["best_source_view"] = table_df["best_source"].fillna("-")
table_df.loc[table_df["best_source"] == "QUOTE", "best_source_view"] = "QUOTE - PDF"

table_df["best_unit_cost_view"] = table_df["best_unit_cost"].map(format_eur_t)
table_df["second_unit_cost_view"] = table_df["second_unit_cost"].map(format_eur_t)
table_df["am_spot_unit_cost_view"] = table_df["am_spot_unit_cost"].map(format_eur_t)
table_df["delta_view"] = table_df["delta_best_vs_am_spot"].map(format_eur_t)
table_df["savings_view"] = table_df["savings_total_vs_am_spot"].map(format_eur)

display_columns = [
    "request_id",
    "our_ref",
    "client_name",
    "material",
    "requested_tons",
    "status",
    "best_option_code",
    "best_supplier_name",
    "best_source_view",
    "best_unit_cost_view",
    "second_option_code",
    "second_unit_cost_view",
    "am_spot_unit_cost_view",
    "delta_view",
    "savings_view",
]

display_df = table_df[display_columns].rename(columns={
    "request_id": "Request ID",
    "our_ref": "Ref",
    "client_name": "Cliente",
    "material": "Material",
    "requested_tons": "Toneladas",
    "status": "Estado",
    "best_option_code": "Mejor opción",
    "best_supplier_name": "Proveedor mejor",
    "best_source_view": "Origen mejor",
    "best_unit_cost_view": "Coste mejor",
    "second_option_code": "Segunda opción",
    "second_unit_cost_view": "Coste segunda",
    "am_spot_unit_cost_view": "AM Spot",
    "delta_view": "Delta vs AM Spot",
    "savings_view": "Ahorro total",
})

def highlight_quote_best(row):
    if row["Origen mejor"] == "QUOTE - PDF":
        return ["background-color: #fff3cd"] * len(row)
    return [""] * len(row)


st.dataframe(
    display_df.style.apply(highlight_quote_best, axis=1),
    width="stretch",
    hide_index=True,
)

st.divider()

request_options = df["request_id"].astype(int).tolist()

selected_request_id = st.selectbox(
    "Selecciona request para ver detalle",
    request_options,
    format_func=lambda request_id: (
        f"Req {request_id} | "
        f"{df.loc[df['request_id'] == request_id, 'our_ref'].iloc[0]} | "
        f"{df.loc[df['request_id'] == request_id, 'client_name'].iloc[0]}"
    ),
)

selected = df[df["request_id"] == selected_request_id].iloc[0].to_dict()
core_quotes = load_request_core_quotes(int(selected_request_id))
quotes_df = pd.DataFrame(core_quotes)

st.subheader("Detalle de request")

detail_col1, detail_col2, detail_col3 = st.columns(3)

with detail_col1:
    st.markdown("#### Request")
    st.write(f"Ref: {selected.get('our_ref')}")
    st.write(f"Cliente: {selected.get('client_name')}")
    st.write(f"Producto: {selected.get('product')}")
    st.write(f"Grade: {selected.get('grade')}")
    st.write(f"Dimensiones: {selected.get('thickness_mm')} x {selected.get('width_mm')}")
    st.write(f"Toneladas: {selected.get('requested_tons')}")
    st.write(f"Estado: {selected.get('status')}")

with detail_col2:
    st.markdown("#### Shortlist")
    st.write(f"Mejor: {selected.get('best_option_code')} | {format_eur_t(selected.get('best_unit_cost'))}")
    st.write(f"Origen: {selected.get('best_source') or '-'}")
    st.write(f"Segunda: {selected.get('second_option_code') or '-'} | {format_eur_t(selected.get('second_unit_cost'))}")
    st.write(f"Tercera: {selected.get('third_option_code') or '-'}")
    st.write(f"AM Spot: {format_eur_t(selected.get('am_spot_unit_cost'))}")

with detail_col3:
    st.markdown("#### Ahorro")
    st.metric("Delta vs AM Spot", format_eur_t(selected.get("delta_best_vs_am_spot")))
    st.metric("Ahorro total", format_eur(selected.get("savings_total_vs_am_spot")))

st.markdown("#### Quotes reales del core")

if quotes_df.empty:
    st.info("Esta request no tiene quotes core asociadas.")
else:
    quotes_display = quotes_df.copy()
    quotes_display["total_price_per_ton"] = quotes_display["total_price_per_ton"].map(format_eur_t)
    quotes_display["total_estimated_cost"] = quotes_display["total_estimated_cost"].map(format_eur)

    st.dataframe(
        quotes_display,
        width="stretch",
        hide_index=True,
    )

st.divider()

st.subheader("Registrar decisión")

if quotes_df.empty:
    st.warning("No hay quotes core disponibles para registrar decisión desde esta pantalla.")
else:
    quote_options = quotes_df["id"].astype(int).tolist()

    selected_quote_id = st.selectbox(
        "Quote seleccionada",
        quote_options,
        format_func=lambda quote_id: (
            f"Quote {quote_id} | "
            f"{quotes_df.loc[quotes_df['id'] == quote_id, 'supplier_code'].iloc[0]} | "
            f"{format_eur_t(quotes_df.loc[quotes_df['id'] == quote_id, 'total_price_per_ton'].iloc[0])} | "
            f"manual_review={quotes_df.loc[quotes_df['id'] == quote_id, 'needs_manual_review'].iloc[0]}"
        ),
    )

    reason = st.text_area(
        "Motivo",
        value="best_price",
        height=90,
    )

    decided_by = st.text_input(
        "Decidido por",
        value="manual_user",
    )

    selected_quote_row = quotes_df[quotes_df["id"] == selected_quote_id].iloc[0].to_dict()

    if int(selected_quote_row.get("needs_manual_review") or 0) == 1:
        st.warning("La quote seleccionada tiene needs_manual_review=1. Revísala antes de decidir.")

    already_awarded = selected.get("status") == "awarded"

    if already_awarded:
        st.info("Esta request ya está marcada como awarded. No se registrará una nueva decisión.")

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
                error_message="No se pudo registrar la decisión. Revisa si la request ya está adjudicada.",
                rerun=True,
            )