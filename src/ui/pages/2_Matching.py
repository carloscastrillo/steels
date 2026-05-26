from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.ui.components.db_session import (
    assign_and_promote_action,
    assign_match_action,
    clear_cache,
    load_approved_unmatched_quotes,
    load_match_candidates,
    promote_quote_to_core_action,
    rebuild_shortlist_action,
)


st.set_page_config(page_title="Matching", page_icon="🔗", layout="wide")

st.title("Matching quote → request")
st.caption("Asignación semiautomática de quotes aprobadas a sourcing requests.")

with st.sidebar:
    st.header("Parámetros")

    top_n = st.slider(
        "Candidatos por quote",
        min_value=1,
        max_value=15,
        value=5,
        step=1,
    )

    min_score = st.slider(
        "Score mínimo",
        min_value=0.0,
        max_value=100.0,
        value=20.0,
        step=5.0,
    )

    st.divider()

    if st.button("Limpiar caché", width="stretch"):
        clear_cache()
        st.rerun()


quotes = load_approved_unmatched_quotes()

col1, col2, col3 = st.columns(3)
col1.metric("Quotes approved sin match", len(quotes))
col2.metric("Top candidatos", top_n)
col3.metric("Score mínimo", int(min_score))

st.divider()

if not quotes:
    st.success("No hay quotes aprobadas pendientes de matching.")
    st.info(
        "Para usar esta pantalla, primero aprueba quotes en la página "
        "'Revisión staging'."
    )
    st.stop()


quotes_df = pd.DataFrame(quotes)

quote_options = quotes_df["id"].astype(int).tolist()

selected_quote_id = st.selectbox(
    "Selecciona quote staging aprobada",
    quote_options,
    format_func=lambda quote_id: (
        f"Quote #{quote_id} | "
        f"{quotes_df.loc[quotes_df['id'] == quote_id, 'supplier_code'].iloc[0]} | "
        f"{quotes_df.loc[quotes_df['id'] == quote_id, 'extracted_grade'].iloc[0]} | "
        f"{quotes_df.loc[quotes_df['id'] == quote_id, 'price_per_ton'].iloc[0]} €/t"
    ),
)

selected_quote = quotes_df[quotes_df["id"] == selected_quote_id].iloc[0].to_dict()

st.subheader("Quote seleccionada")

q_col1, q_col2, q_col3, q_col4 = st.columns(4)

q_col1.metric("Proveedor", selected_quote.get("supplier_code") or "-")
q_col2.metric("Precio €/t", selected_quote.get("price_per_ton") or "-")
q_col3.metric("Espesor", selected_quote.get("thickness_mm") or "-")
q_col4.metric("Manual review", selected_quote.get("needs_manual_review") or 0)

with st.expander("Detalle de quote staging", expanded=True):
    st.write("ID:", selected_quote.get("id"))
    st.write("Documento:", selected_quote.get("document"))
    st.write("Grade extraído:", selected_quote.get("extracted_grade"))
    st.write("Coating raw:", selected_quote.get("coating_raw"))
    st.write("Ancho:", selected_quote.get("width_mm"))
    st.write("Review status:", selected_quote.get("review_status"))
    st.code(selected_quote.get("raw_snippet") or "(sin raw snippet)", language="text")


candidates = load_match_candidates(
    quote_id=int(selected_quote_id),
    top_n=int(top_n),
    min_score=float(min_score),
)

st.subheader("Candidatos sugeridos")

if not candidates:
    st.warning("No hay candidatos compatibles por encima del score mínimo.")
    st.stop()

candidates_df = pd.DataFrame(candidates)

display_df = candidates_df.copy()
display_df["grade_score"] = display_df["breakdown"].map(lambda value: value.get("grade_score") if isinstance(value, dict) else None)
display_df["thickness_score"] = display_df["breakdown"].map(lambda value: value.get("thickness_score") if isinstance(value, dict) else None)
display_df["width_score"] = display_df["breakdown"].map(lambda value: value.get("width_score") if isinstance(value, dict) else None)
display_df["blocked"] = display_df["breakdown"].map(lambda value: value.get("blocked") if isinstance(value, dict) else None)

display_columns = [
    "score",
    "request_id",
    "our_ref",
    "client_name",
    "product",
    "grade",
    "thickness_mm",
    "width_mm",
    "tons",
    "status",
    "grade_score",
    "thickness_score",
    "width_score",
    "blocked",
]

st.dataframe(
    display_df[display_columns],
    width="stretch",
    hide_index=True,
)

bad_candidates = display_df[
    (display_df["grade_score"].fillna(0) <= 0)
    | (display_df["blocked"] == True)
]

if not bad_candidates.empty:
    st.error(
        "Hay candidatos bloqueados o sin compatibilidad de grade. "
        "Esto no debería ocurrir por el hotfix del matching."
    )

candidate_options = candidates_df["request_id"].astype(int).tolist()

selected_request_id = st.selectbox(
    "Selecciona request candidata",
    candidate_options,
    format_func=lambda request_id: (
        f"Req #{request_id} | "
        f"{candidates_df.loc[candidates_df['request_id'] == request_id, 'our_ref'].iloc[0]} | "
        f"{candidates_df.loc[candidates_df['request_id'] == request_id, 'client_name'].iloc[0]} | "
        f"score={candidates_df.loc[candidates_df['request_id'] == request_id, 'score'].iloc[0]}"
    ),
)

selected_candidate = candidates_df[candidates_df["request_id"] == selected_request_id].iloc[0].to_dict()

st.markdown("#### Desglose del candidato seleccionado")

breakdown = selected_candidate.get("breakdown") or {}

b1, b2, b3 = st.columns(3)
b1.metric("Grade score", breakdown.get("grade_score", 0))
b2.metric("Thickness score", breakdown.get("thickness_score", 0))
b3.metric("Width score", breakdown.get("width_score", 0))

with st.expander("Ver explicación completa del score", expanded=False):
    st.json(breakdown)

st.divider()

st.subheader("Acciones")

if breakdown.get("grade_score", 0) <= 0 or breakdown.get("blocked"):
    st.error("Este candidato está bloqueado por falta de compatibilidad de grade.")
    st.stop()

confirm_key = f"confirm_match_{selected_quote_id}_{selected_request_id}"

a_col1, a_col2, a_col3 = st.columns(3)

with a_col1:
    if st.button("Asignar match", width="stretch"):
        st.session_state[confirm_key] = "assign"

with a_col2:
    if st.button("Asignar y promover al core", type="primary", width="stretch"):
        st.session_state[confirm_key] = "assign_promote"

with a_col3:
    if st.button("Promover quote ya matcheada", width="stretch"):
        st.session_state[confirm_key] = "promote_only"


pending_action = st.session_state.get(confirm_key)

if pending_action:
    if pending_action == "assign":
        action_text = "asignar esta quote a la request seleccionada"
    elif pending_action == "assign_promote":
        action_text = "asignar esta quote y crear la sourcing_quote core"
    else:
        action_text = "promover esta quote a sourcing_quotes"

    st.warning(
        f"Confirmación requerida: vas a {action_text}.\n\n"
        f"Quote #{selected_quote_id} → Request #{selected_request_id}"
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button("Confirmar", type="primary", width="stretch"):
            if pending_action == "assign":
                assign_match_action(
                    quote_id=int(selected_quote_id),
                    request_id=int(selected_request_id),
                )
                st.success("Match asignado correctamente.")

            elif pending_action == "assign_promote":
                core_id = assign_and_promote_action(
                    quote_id=int(selected_quote_id),
                    request_id=int(selected_request_id),
                )
                st.success(f"Match asignado y sourcing_quote creada/encontrada. ID: {core_id}")

                rebuilt = rebuild_shortlist_action()
                st.info(f"Shortlist recalculada. Filas: {rebuilt}")

            else:
                core_id = promote_quote_to_core_action(
                    quote_id=int(selected_quote_id),
                )
                st.success(f"Sourcing_quote creada/encontrada. ID: {core_id}")

                rebuilt = rebuild_shortlist_action()
                st.info(f"Shortlist recalculada. Filas: {rebuilt}")

            st.session_state.pop(confirm_key, None)
            st.rerun()

    with c2:
        if st.button("Cancelar", width="stretch"):
            st.session_state.pop(confirm_key, None)
            st.rerun()