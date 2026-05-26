from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st


BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.ui.components.db_session import (
    get_database_path_text,
    load_shortlist_summary,
    load_staging_summary,
)


st.set_page_config(
    page_title="Steel MVP",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.title("Steel MVP")
st.caption("Interfaz operativa local para sourcing, revisión de proveedores y reporting.")

st.sidebar.title("Steel MVP")
st.sidebar.info(
    "Usa las páginas del menú lateral para revisar staging, hacer matching, "
    "consultar shortlist y generar reporting."
)

st.subheader("Dashboard inicial")

summary = load_staging_summary()
shortlist_rows = load_shortlist_summary()

total_staging = sum(item["n_quotes"] for item in summary)
pending_staging = sum(
    item["n_quotes"]
    for item in summary
    if item["review_status"] == "pending"
)
approved_staging = sum(
    item["n_quotes"]
    for item in summary
    if item["review_status"] == "approved"
)
shortlist_total = len(shortlist_rows)
quote_best = sum(
    1
    for item in shortlist_rows
    if item.get("best_source") == "QUOTE"
)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Quotes staging", total_staging)
col2.metric("Pendientes", pending_staging)
col3.metric("Aprobadas", approved_staging)
col4.metric("Shortlists", shortlist_total)
col5.metric("Best source QUOTE", quote_best)

st.divider()

left, right = st.columns([2, 1])

with left:
    st.markdown("### Estado staging por proveedor")
    if summary:
        st.dataframe(summary, width="stretch", hide_index=True)
    else:
        st.info("No hay datos de staging todavía.")

with right:
    st.markdown("### Base de datos")
    st.code(get_database_path_text(), language="text")

st.divider()

st.markdown("### Flujo operativo previsto")
st.write(
    "1. Revisar quotes de proveedor en staging.\n"
    "2. Aprobar o rechazar quotes.\n"
    "3. Hacer matching quote → request.\n"
    "4. Promover quotes válidas al core.\n"
    "5. Recalcular shortlist y registrar decisiones."
)